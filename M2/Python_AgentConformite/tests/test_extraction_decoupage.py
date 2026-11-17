"""Tests du nettoyage et du découpage : textes INVENTÉS, aucun appel API.

Le dernier test tourne sur le vrai PDF IFRS 9 s'il est présent dans data/corpus/
(il est ignoré sinon, par exemple sur une machine qui n'a pas le corpus).
"""

from pathlib import Path

import pytest

from src import decoupage as dc
from src import extraction as ex

# --- Nettoyage -------------------------------------------------------------------


def _pages(n):
    """n pages factices avec en-tête fixe, pied de page qui alterne pair/impair."""
    pages = []
    for i in range(n):
        pied = f"P{100 + i} © Éditeur" if i % 2 else f"© Éditeur P{100 + i}"
        mots = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliett"]
        remplissage = "\n".join(f"Ligne {mots[i]} {mots[j]} du texte." for j in range(4))
        corps = f"{remplissage}\nArticle {i + 1}\nCorps de l'article {i + 1}.\n{remplissage}"
        pages.append(f"Texte réglementaire\n\n\n{corps}\n\n{pied}")
    return pages


def test_en_tetes_et_pieds_alternes_retires():
    texte, rapport = ex.nettoyer(_pages(10))
    assert "Texte réglementaire" not in texte
    assert "Éditeur" not in texte  # les deux variantes du pied de page
    # « Article N » revient sur chaque page avec la même forme, mais au milieu
    # de la page : ce n'est pas un en-tête, il doit rester
    assert texte.count("Article ") == 10
    assert texte.count("Corps de l'article") == 10
    assert rapport["nb_lignes_retirees"] == 20


def test_pas_de_nettoyage_statistique_sous_quatre_pages():
    texte, _ = ex.nettoyer(["Titre\nA", "Titre\nB"])
    assert texte.count("Titre") == 2


# --- Découpage : structure « loi française » inventée -------------------------------

LOI = "\n".join(
    ["Loi n° 0000 relative à une matière imaginaire"]
    + [
        f"Article {n}\nI. – L'entité met en place un dispositif {n}.{k}."
        f"\nII. – Ce dispositif est évalué selon les modalités prévues à l'article {n + 1}.\n"
        + "Texte de remplissage pour donner du volume au contenu de l'article. " * 40
        for n in range(1, 13)
        for k in [1]
    ]
)


def test_loi_en_articles_couverture_complete_et_ordre():
    sections = dc.decouper(LOI, min_tokens=800, max_tokens=2_500)
    assert sections[0].debut == 0 and sections[-1].fin == len(LOI)
    assert all(a.fin == b.debut for a, b in zip(sections, sections[1:]))
    cles = [c for s in sections for c in s.cles]
    # les articles apparaissent dans l'ordre, chacun une fois comme clé de tête
    articles = [c for c in cles if c.startswith("Article") and c.count(" ") == 1]
    assert articles == [f"Article {n}" for n in range(1, 13)]


def test_renvoi_en_debut_de_ligne_ignore():
    # « Article 9 » en début de ligne au milieu de l'article 2 est un renvoi, pas un titre
    texte = (
        "Article 1\nDispositions.\n"
        "Article 2\nL'obligation est précisée à l'\n"
        "Article 9 qui suit.\n"
        "Article 3\nSuite.\n"
        "Article 4\nSuite.\n"
        "Article 5\nFin.\n"
    )
    blocs, _ = dc._blocs(texte)
    assert [b["cle"] for b in blocs] == ["Article 1", "Article 2", "Article 3", "Article 4", "Article 5"]


def test_article_de_code_en_debut_de_ligne_n_est_pas_un_romain():
    texte = ("Article 1\nI. – Les dirigeants sont tenus de prendre des mesures.\n"
             "II. – Ces mesures comprennent un code de conduite.\n"
             "L. 225-57 du code de commerce, applicables aux sociétés concernées.\n"
             "Article 2\nSuite.\nArticle 3\nSuite.\nArticle 4\nSuite.\nArticle 5\nFin.\n")
    blocs, _ = dc._blocs(texte)
    cles = [b["cle"] for b in blocs]
    assert "Article 1 I" in cles and "Article 1 II" in cles
    assert not any(c.endswith(" L") for c in cles)


def test_paragraphes_numerotes_et_renvois():
    lignes = []
    for ch in (1, 2, 3):
        lignes.append(f"{ch}.1 Intitulé du chapitre {ch}")
        for p in range(1, 6):
            lignes.append(f"{ch}.1.{p} The entity shall apply requirement {ch}.{p}.")
        lignes.append("3.1.4 and 9.9.9 are referred to here as a cross-reference.")
    blocs, _ = dc._blocs("\n".join(lignes))
    # le texte commence par une unité : pas de bloc « (début) » ; le renvoi
    # « 3.1.4 and 9.9.9… » placé dans les chapitres 1 et 2 est écarté
    assert [b["cle"] for b in blocs] == ["1.1", "2.1", "3.1"]


def test_repli_fenetres_fixes_sans_structure():
    texte = ("Un texte sans aucune numérotation exploitable.\n" * 2_000)
    sections = dc.decouper(texte, max_tokens=5_000)
    assert len(sections) > 1
    assert all(s.cles == ["(fenêtre)"] for s in sections)
    assert all(s.tokens_estimes <= 5_000 for s in sections)
    assert sections[-1].fin == len(texte)


def test_section_de_position():
    sections = dc.decouper(LOI, min_tokens=800, max_tokens=2_500)
    pos = LOI.index("dispositif 7.1")
    s = dc.section_de_position(sections, pos)
    assert s.debut <= pos < s.fin


# --- Intégration sur le vrai document (si disponible localement) --------------------

PDF_IFRS9 = Path(__file__).resolve().parent.parent / "data/corpus/ifrs-9-financial-instruments.pdf"


@pytest.mark.skipif(not PDF_IFRS9.exists(), reason="corpus IFRS 9 absent de cette machine")
def test_ifrs9_reel():
    doc = ex.charger_document(PDF_IFRS9)
    texte = doc["texte"]
    assert "IFRS Foundation" not in texte  # pieds de page retirés
    sections = dc.decouper(texte)
    assert sections[0].debut == 0 and sections[-1].fin == len(texte)
    assert all(a.fin == b.debut for a, b in zip(sections, sections[1:]))
    assert all(s.tokens_estimes <= 12_000 for s in sections)
    assert 10 <= len(sections) <= 40


def test_romain_legifrance_sans_espace_apres_le_tiret():
    # style Légifrance : « II.-Les personnes… », sans espace ; « L.-225 » n'est pas un romain
    texte = ("Article 1\nI.-Les dirigeants sont tenus de prendre des mesures.\n"
             "II.-Les personnes mentionnées au I mettent en œuvre un code de conduite.\n"
             "Article 2\nSuite.\nArticle 3\nSuite.\nArticle 4\nSuite.\nArticle 5\nFin.\n")
    cles = [b["cle"] for b in dc._blocs(texte)[0]]
    assert "Article 1 I" in cles and "Article 1 II" in cles
