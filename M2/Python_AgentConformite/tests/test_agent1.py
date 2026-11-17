"""Tests de l'Agent 1, du module d'appel et des citations.

AUCUN appel API : le client Anthropic est remplacé par un faux qui renvoie une
réponse fabriquée, avec un objet `usage` réaliste.
"""

import json
import re
from pathlib import Path

import pytest

from src import agent1, appel_llm, couts
from src.couts import BudgetDepasse
from src.decoupage import decouper
from src.schema import Enrichissement, analyser_sortie, fusionner
from src.verif_citations import IndexTexte, normaliser, ref_coherente, verifier_ligne, verifier_referentiel

# --- Un texte réglementaire INVENTÉ ----------------------------------------------------
TEXTE = "\n".join(
    [f"1.{p} The operator shall keep a register of incidents number {p} for at least five years and make it\n"
     f"available to the inspector on request, together with the related evidence." for p in range(1, 6)]
    + [f"2.{p} The operator shall review the register every quarter and document the review {p}\n"
       f"in minutes approved by the management body." for p in range(1, 6)]
) + "\n"


# --- Faux client ------------------------------------------------------------------------
class _Usage:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Message:
    def __init__(self, texte, usage):
        self.id, self.stop_reason, self.usage, self._texte = "msg_test", "end_turn", usage, texte

    def model_dump(self):
        return {"id": self.id, "stop_reason": self.stop_reason, "usage": vars(self.usage),
                "content": [{"type": "text", "text": self._texte}]}


class FauxClient:
    """Répond comme le modèle : extraction ou enrichissement selon la tâche du message."""

    def __init__(self, texte_reponse):
        self.requetes, self.texte_reponse = [], texte_reponse
        self.messages = self

    def _repondre(self, requete):
        message = requete["messages"][-1]["content"]
        if "TÂCHE : ENRICHISSEMENT" in message:
            ids = re.findall(r'"id": "([^"]+)"', message)
            return json.dumps({"lignes": [{"id": i, "ctrl": f"Contrôle {i}.", "test": f"Test {i}."} for i in ids]})
        # extraction : on reprend le préfixe d'identifiant demandé (« Numérote les lignes S02-001 »)
        prefixe = re.search(r"Numérote les lignes (\S+)-001", message)
        return self.texte_reponse.replace("S01-001", f"{prefixe.group(1)}-001" if prefixe else "S01-001")

    def stream(self, **requete):
        self.requetes.append(requete)
        rang = len(self.requetes)
        usage = _Usage(input_tokens=50, output_tokens=400,
                       cache_creation_input_tokens=3_000 if rang == 1 else 0,
                       cache_read_input_tokens=0 if rang == 1 else 3_000)
        message = _Message(self._repondre(requete), usage)

        class _Flux:
            def __enter__(s):
                return s

            def __exit__(s, *a):
                return False

            def get_final_message(s):
                return message

        return _Flux()


REPONSE = json.dumps({"lignes": [{
    "id": "S01-001", "ref": "1.2",
    "cit": "The operator shall keep a register of incidents number 2 for at least five years",
    "dom": "record keeping", "obl": "Keep the incident register for five years.",
    "typ": "documentation", "crit": "majeure"}]})


@pytest.fixture
def faux(monkeypatch, tmp_path):
    client = FauxClient(REPONSE)
    monkeypatch.setattr(appel_llm, "_client", lambda: client)
    return client, tmp_path / "couts.jsonl", tmp_path / "cache"


def _appel(journal, cache, **kw):
    base = dict(modele="claude-sonnet-5-5", systeme=[{"type": "text", "text": "consignes"}],
                messages=[{"role": "user", "content": "s1"}], etiquette="debug",
                version_prompt="v1", max_tokens=1_000, journal=journal, dossier_cache=cache)
    return appel_llm.appeler(**{**base, **kw})


# --- Module d'appel -----------------------------------------------------------------------
def test_appel_journalise_puis_relu_du_disque(faux):
    client, journal, cache = faux
    r1 = _appel(journal, cache)
    r2 = _appel(journal, cache)
    assert (r1["_vient_du_cache"], r2["_vient_du_cache"]) == (False, True)
    assert len(client.requetes) == 1  # le second appel n'a rien coûté
    lignes = couts.lire_journal(journal)
    assert len(lignes) == 1 and lignes[0]["etiquette"] == "debug"
    # 50 × 2 + 3 000 × 2,50 + 400 × 10 = 100 + 7 500 + 4 000 = 11 600 → 0,0116 $
    assert lignes[0]["cout_usd"] == pytest.approx(0.0116)


def test_aucun_parametre_d_echantillonnage_et_effort_en_extra_body(faux):
    client, journal, cache = faux
    _appel(journal, cache, effort="medium")
    req = client.requetes[0]
    assert not {"temperature", "top_p", "top_k"} & set(req)
    assert req["extra_body"] == {"output_config": {"effort": "medium"}}


def test_effort_ignore_pour_haiku(faux):
    client, journal, cache = faux
    _appel(journal, cache, modele="claude-haiku-4-5-20251001", effort="high")
    assert "extra_body" not in client.requetes[0]


def test_budget_refuse_avant_tout_appel(faux):
    client, journal, cache = faux
    couts.journaliser("claude-sonnet-5-5", {"output_tokens": 30_000_000}, "debug", chemin=journal)  # 300 $
    with pytest.raises(BudgetDepasse):
        _appel(journal, cache)
    assert client.requetes == []  # rien n'a été envoyé


def test_fable_refuse(faux):
    _, journal, cache = faux
    with pytest.raises(ValueError, match="interdit"):
        _appel(journal, cache, modele="claude-fable-5")


def test_erreurs_reessayables():
    anthropic = pytest.importorskip("anthropic")

    def erreur(code):
        # construite sans passer par la couche HTTP du SDK (httpx ou httpx2 selon la version)
        e = anthropic.APIStatusError.__new__(anthropic.APIStatusError)
        e.status_code = code
        return e

    assert appel_llm._erreur_reessayable(erreur(429))
    assert appel_llm._erreur_reessayable(erreur(529))
    for code in (400, 401, 403, 404):
        assert not appel_llm._erreur_reessayable(erreur(code))
    assert not appel_llm._erreur_reessayable(ValueError("pas une erreur d'API"))


# --- Prompt et structure de la requête -----------------------------------------------------
def test_prompts_ne_nomment_aucun_corpus():
    for f in Path(agent1.DOSSIER_PROMPTS).glob("*.txt"):
        contenu = f.read_text(encoding="utf-8").lower()
        for interdit in ("ifrs", "sapin", "ias 39", "corruption", "expected credit loss"):
            assert interdit not in contenu, f"{f.name} mentionne « {interdit} »"


def test_cache_sur_le_document_seulement():
    systeme = agent1.construire_systeme(TEXTE, "Règlement fictif", "anglais")
    assert "cache_control" not in systeme[0]
    assert systeme[-1]["cache_control"] == {"type": "ephemeral"}
    assert systeme[-1]["text"].startswith("<document>") and systeme[-1]["text"].rstrip().endswith("</document>")
    assert "{nom_document}" not in systeme[0]["text"] and "{langue}" not in systeme[0]["text"]
    assert "{{" not in systeme[0]["text"]  # les accolades doublées des exemples sont bien rendues
    assert "Règlement fictif" in systeme[0]["text"]


def test_executer_extraction_puis_enrichissement(faux, tmp_path):
    client, journal, cache = faux
    sections = decouper(TEXTE, min_tokens=50, max_tokens=200)
    res = agent1.executer(texte=TEXTE, sections=sections, mode="section", nom_document="Fictif",
                          sha_texte="abc12345", langue="anglais", taille_lot=1,
                          dossier_resultats=tmp_path / "res", journal=journal, dossier_cache=cache)
    nb_extr = len(sections)
    # chaque section renvoie la même ligne fictive « S01-001 » : autant de lignes que de sections
    assert len(client.requetes) == nb_extr + res["nb_lignes"]
    # le préfixe est STRICTEMENT identique entre extraction et enrichissement : une seule écriture de cache
    assert all(r["system"] == client.requetes[0]["system"] for r in client.requetes)
    assert "TÂCHE : ENRICHISSEMENT" in client.requetes[-1]["messages"][0]["content"]
    assert client.requetes[0]["extra_body"] == {"output_config": {"effort": "medium"}}  # effort par défaut v2
    enreg = [json.loads(l) for l in Path(res["fichier"]).read_text(encoding="utf-8").splitlines()]
    assert enreg[0]["type"] == "entete" and enreg[0]["version_prompt"] == agent1.VERSION_PROMPT
    assert [e["type"] for e in enreg][-1] == "synthese"
    finale = res["lignes"][0]
    assert finale["_verif"]["statut"] == "valide" and finale["ctrl"] == "Contrôle S01-001."


def test_executer_sans_enrichissement(faux, tmp_path):
    client, journal, cache = faux
    sections = decouper(TEXTE, min_tokens=50, max_tokens=200)
    agent1.executer(texte=TEXTE, sections=sections, mode="unique", nom_document="Fictif",
                    sha_texte="abc12345", langue="anglais", enrichir=False,
                    dossier_resultats=tmp_path / "res", journal=journal, dossier_cache=cache)
    assert len(client.requetes) == 1


def test_fusion_signale_les_lignes_non_enrichies():
    extr = [{"id": "a", "obl": "x"}, {"id": "b", "obl": "y"}]
    finales, manquants = fusionner(extr, [{"id": "a", "ctrl": "c", "test": "t"}])
    assert manquants == ["b"] and finales[0]["ctrl"] == "c" and finales[1]["ctrl"] == ""


def test_analyser_enrichissement():
    texte = json.dumps({"lignes": [{"id": "a", "ctrl": "c", "test": "t"}, {"id": "b", "ctrl": "c"}]})
    valides, rejets = analyser_sortie(texte, Enrichissement)
    assert [v["id"] for v in valides] == ["a"] and len(rejets) == 1


# --- Analyse de la sortie -------------------------------------------------------------------
def test_analyser_sortie_tolere_bloc_de_code_et_isole_les_lignes_invalides():
    mauvaise = {**json.loads(REPONSE)["lignes"][0], "crit": "critical"}  # valeur traduite : refusée
    texte = "```json\n" + json.dumps({"lignes": [json.loads(REPONSE)["lignes"][0], mauvaise]}) + "\n```"
    valides, rejets = analyser_sortie(texte)
    assert len(valides) == 1 and len(rejets) == 1


def test_analyser_sortie_tronquee_recupere_les_objets_complets():
    ligne = json.loads(REPONSE)["lignes"][0]
    complets = ",\n".join(json.dumps({**ligne, "id": f"S01-00{k}"}) for k in (1, 2))
    tronque = '{"lignes": [\n' + complets + ',\n{"id": "S01-003", "ref": "1.4", "cit": "The oper'
    valides, rejets = analyser_sortie(tronque)
    assert [v["id"] for v in valides] == ["S01-001", "S01-002"]
    assert "2 objets" in rejets[0]["raison"]


def test_analyser_sortie_rien_de_recuperable():
    valides, rejets = analyser_sortie('{"lignes": [{"id": "S01-001", ')
    assert valides == [] and "0 objets" in rejets[0]["raison"]


# --- Citations -------------------------------------------------------------------------------
def test_normalisation_guillemets_tirets_coupures():
    a, _ = normaliser("L’entité « non-\nfinancière »  —  ok")
    b, _ = normaliser("l'entité \"non-financière\" - OK")
    assert a == b
    # un tiret de ponctuation n'est PAS recollé au mot suivant
    assert normaliser("risque - élevé")[0] == "risque - élevé"


def test_mots_coupes_en_fin_de_ligne():
    ix = IndexTexte("The holder would analyse the conver-\ntible bond and its credit-\nadjusted rate in full.\n")
    for cit in ("analyse the convertible bond and its credit-adjusted rate",
                "analyse the conver- tible bond and its credit- adjusted rate",
                "analyse the conver-tible bond and its credit-adjusted rate"):
        assert ix.trouver(cit) is not None, cit


def test_citation_retrouvee_a_travers_un_saut_de_ligne_et_avec_ellipse():
    ix = IndexTexte(TEXTE)
    ligne = {"ref": "1.3", "cit": "keep a register of incidents number 3 … available to the inspector on request"}
    assert verifier_ligne(ix, ligne)["statut"] == "valide"


def test_reference_incoherente_et_citation_inventee():
    ix = IndexTexte(TEXTE)
    vraie = "The operator shall review the register every quarter and document the review 4"
    assert verifier_ligne(ix, {"ref": "1.4", "cit": vraie})["statut"] == "ref_incoherente"
    assert verifier_ligne(ix, {"ref": "2.4", "cit": vraie})["statut"] == "valide"
    inventee = "The operator shall notify the regulator within 24 hours of any incident"
    assert verifier_ligne(ix, {"ref": "2.4", "cit": inventee})["statut"] == "introuvable"


def test_formule_repetee_dans_plusieurs_paragraphes():
    texte = ("3.1 The entity shall assume that the benchmark is not altered by the reform for this purpose.\n"
             "3.2 The entity shall assume that the benchmark is not altered by the reform for this purpose.\n"
             "3.3 Other text.\n3.4 Other text.\n3.5 Other text.\n")
    ix = IndexTexte(texte)
    cit = "The entity shall assume that the benchmark is not altered by the reform"
    assert verifier_ligne(ix, {"ref": "3.2", "cit": cit})["statut"] == "valide"
    assert verifier_ligne(ix, {"ref": "3.2", "cit": cit})["nb_occurrences"] == 2
    assert verifier_ligne(ix, {"ref": "3.4", "cit": cit})["statut"] == "ref_incoherente"


def test_intervalles_et_articles():
    assert ref_coherente("B5.5.30–B5.5.40", ["B5.5.37"])
    assert not ref_coherente("B5.5.30–B5.5.36", ["B5.5.37"])
    assert ref_coherente("art. 17 II 3°", ["Article 17"])
    assert ref_coherente("Appendix A", ["Appendix A"])
    assert not ref_coherente("Appendix B", ["Appendix A"])


def test_taux_hallucination():
    lignes = [{"id": "a", "ref": "2.4", "cit": "The operator shall review the register every quarter and document the review 4"},
              {"id": "b", "ref": "2.4", "cit": "The operator shall notify the regulator within 24 hours of any incident"}]
    r = verifier_referentiel(TEXTE, lignes)
    assert r["taux_hallucination"] == 0.5


def test_prompts_v4_complets_et_sans_corpus():
    for v in ("v4a", "v4"):
        for nom in ("systeme", "section", "unique", "enrichissement", "rattrapage"):
            c = (agent1.DOSSIER_PROMPTS / f"agent1_{nom}_{v}.txt").read_text(encoding="utf-8").lower()
            for interdit in ("ifrs", "sapin", "corruption", "deloitte", "ias 39"):
                assert interdit not in c, (v, nom, interdit)
        systeme = agent1.charger_prompt("agent1_systeme", v)
        assert "Destinataire" in systeme and "subdivision LA PLUS FINE" in systeme
        assert ("Parcours la grille" in systeme) == (v == "v4")  # la grille de contrôle n'est que dans la v4
        systeme.format(nom_document="X", langue="français")  # les accolades du prompt restent valides


def test_v4b_systeme_identique_v4a_et_grille_dans_le_message():
    """v4b : l'extraction voit exactement le système v4a ; seule la consigne d'enrichissement change."""
    assert agent1.charger_prompt("agent1_systeme", "v4b") == agent1.charger_prompt("agent1_systeme", "v4a")
    assert "Parcours la grille" in agent1.consigne_enrichissement([{"id": "S01-001", "ref": "1", "obl": "x"}], "v4b")
    assert "Parcours la grille" not in agent1.consigne_enrichissement([{"id": "S01-001", "ref": "1", "obl": "x"}], "v4a")
    for nom in ("systeme", "section", "unique", "enrichissement", "rattrapage"):
        c = (agent1.DOSSIER_PROMPTS / f"agent1_{nom}_v4b.txt").read_text(encoding="utf-8").lower()
        assert not any(m in c for m in ("ifrs", "sapin", "corruption", "deloitte"))
