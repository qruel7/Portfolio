"""Tests de la couverture des paragraphes et de la passe de rattrapage. AUCUN appel API."""

import pytest

from src import agent1, appel_llm
from src.couverture import compter_prescriptif, paragraphes_omis
from src.decoupage import decouper
from tests.test_agent1 import REPONSE, TEXTE, FauxClient


def test_renvois_et_negations_ne_comptent_pas_comme_prescriptifs():
    assert compter_prescriptif("The entity shall keep records.") == 1
    assert compter_prescriptif("Paragraph 5.5.9 requires an assessment.") == 0
    assert compter_prescriptif("Paragraphs 4.1.2 and 4.1.2A require that…") == 0
    assert compter_prescriptif("An entity is not required to restate.") == 0


def test_paragraphes_omis_et_titres_ignores():
    texte = ("2.1 Intitulé du chapitre\n"
             "2.1.1 The operator shall keep a register of incidents for five years.\n"
             "2.1.2 The operator shall review the register every quarter.\n"
             "2.1.3 For example, a register may be kept on paper.\n"
             "2.1.4 Other text.\n2.1.5 Other text.\n")
    sections = decouper(texte, min_tokens=10, max_tokens=10_000)
    lignes = {sections[0].id: [{"ref": "2.1.1"}]}
    omis = {o["paragraphe"]: o for o in paragraphes_omis(texte, sections, lignes)}
    assert "2.1" not in omis  # titre, parent de 2.1.1
    assert omis["2.1.2"]["prescriptif"] == 1  # oubli probable
    assert omis["2.1.3"]["prescriptif"] == 0 and omis["2.1.3"]["facultatif"] == 1


@pytest.fixture
def faux(monkeypatch, tmp_path):
    client = FauxClient(REPONSE)
    monkeypatch.setattr(appel_llm, "_client", lambda: client)
    return client, tmp_path


def test_rattrapage_meme_prefixe_et_consigne_ciblee(faux):
    client, tmp = faux
    sections = decouper(TEXTE, min_tokens=50, max_tokens=200)
    omis = [{"paragraphe": "1.2", "debut": TEXTE.index("1.2 "), "fin": TEXTE.index("1.3 ")}]
    consigne = agent1.consigne_rattrapage(TEXTE, omis, "R1")
    res = agent1.executer(texte=TEXTE, sections=sections, mode="rattrapage", nom_document="Fictif",
                          sha_texte="abc12345", langue="anglais", taches=[("R1", consigne)],
                          meta_run={"rattrapage_de": "section-abc"}, dossier_resultats=tmp / "res",
                          journal=tmp / "j.jsonl", dossier_cache=tmp / "c")
    # préfixe identique à celui d'un run normal : le cache serveur du document est réutilisable
    assert client.requetes[0]["system"] == agent1.construire_systeme(TEXTE, "Fictif", "anglais")
    assert "1.2" in client.requetes[0]["messages"][0]["content"]
    assert "TÂCHE : EXTRACTION" in client.requetes[0]["messages"][0]["content"]
    assert res["nb_lignes"] == 1 and res["lignes"][0]["id"] == "R1-001"
    assert res["id_run"].startswith("rattrapage-")


def test_rattrapage_exige_des_taches():
    with pytest.raises(ValueError):
        agent1.executer(texte=TEXTE, sections=[], mode="rattrapage", nom_document="x", sha_texte="y")


def test_references_d_article_et_subdivisions():
    from src.couverture import base_ref
    assert base_ref("art. 17, II, 3°") == base_ref("Article 17 II") == "Article 17 II"
    assert base_ref("article 8") == "Article 8" and base_ref("5.5.17(a)") == "5.5.17"
    assert compter_prescriptif("Les personnes mentionnées au I mettent en œuvre les mesures.") == 1
    texte = ("Article 1\nI.-Les dirigeants sont tenus de prendre des mesures.\n"
             "II.-Les personnes mentionnées au I mettent en œuvre un code de conduite.\n"
             "III.-L'entité veille à la formation des cadres.\n")
    sections = decouper(texte, min_tokens=10, max_tokens=10_000)
    omis = {o["paragraphe"] for o in paragraphes_omis(texte, sections, {sections[0].id: [{"ref": "art. 1, II, 1°"}]})}
    assert omis == {"Article 1 I", "Article 1 III"}  # « Article 1 » est un titre, II est couvert


def test_paragraphe_de_la_citation_compte_comme_couvert():
    texte = ("Article 1\nI.-Les dirigeants sont tenus de prendre des mesures.\n"
             "II.-Les personnes mentionnées au I mettent en œuvre un code de conduite.\n")
    sections = decouper(texte, min_tokens=10, max_tokens=10_000)
    # référence trop large (« Article 1 ») mais citation trouvée dans le II
    lignes = {sections[0].id: [{"ref": "Article 1", "_verif": {"statut": "valide", "paragraphe": "Article 1 II"}}]}
    assert {o["paragraphe"] for o in paragraphes_omis(texte, sections, lignes)} == {"Article 1 I"}
