"""Pipeline LangGraph de bout en bout, sur un texte et un référentiel INVENTÉS. AUCUN appel API."""

import json

import openpyxl

from src import appel_llm, config, pipeline, rattrapage
from src.extraction import empreinte
from tests import test_agent1, test_agent2


class FauxClientMixte:
    """Agent 1 (extraction, enrichissement, rattrapage) et Agent 2 (appariement, pertinence)."""

    def __init__(self):
        self.a1 = test_agent1.FauxClient(test_agent1.REPONSE)
        self.a2 = test_agent2.FauxClient()
        self.requetes, self.messages = [], self

    def stream(self, **requete):
        self.requetes.append(requete)
        msg = requete["messages"][0]["content"]
        cible = self.a2 if ("TÂCHE : APPARIEMENT" in msg or "TÂCHE : PERTINENCE" in msg) else self.a1
        return cible.stream(**requete)


def _environnement(monkeypatch, tmp_path):
    doc = {"texte": test_agent1.TEXTE, "sha256_texte": empreinte(test_agent1.TEXTE), "rapport": {}}
    for module in (pipeline, rattrapage):
        monkeypatch.setattr(module, "charger_document", lambda *a, **k: doc)
    monkeypatch.setattr(config, "JOURNAL_COUTS", tmp_path / "couts.jsonl")
    monkeypatch.setattr(config, "DOSSIER_CACHE", tmp_path / "cache")
    monkeypatch.setattr(config, "DECOUPAGE_MIN_TOKENS", 10)
    monkeypatch.setattr(config, "DECOUPAGE_MAX_TOKENS", 120)
    client = FauxClientMixte()
    monkeypatch.setattr(appel_llm, "_client", lambda: client)
    return client


def test_chaine_complete(monkeypatch, tmp_path):
    client = _environnement(monkeypatch, tmp_path)
    ref = test_agent2._xlsx(tmp_path)
    etat = pipeline.executer({"document": "inutile.pdf", "nom": "Règlement fictif", "referentiel": str(ref),
                              "dossier_resultats": str(tmp_path / "res")})
    assert [e["etape"] for e in etat["journal_etapes"]] == list(pipeline.ETAPES)
    assert etat["nb_etapes"] == 5
    for cle in ("run_agent1", "consolide", "dedoublonne", "run_agent2", "gap_analysis", "export"):
        assert (tmp_path / "res" / __import__("pathlib").Path(etat[cle]).name).exists() or \
            __import__("pathlib").Path(etat[cle]).exists(), cle
    lignes_export = list(openpyxl.load_workbook(etat["export"]).active.iter_rows(values_only=True))
    assert lignes_export[0][:3] == ("Classification", "Constat", "Criticité")
    # l'état ne transporte que des chemins et des compteurs : jamais le texte ni le référentiel
    assert "register of incidents" not in json.dumps(etat, default=str)
    assert len(client.requetes) >= 3


def test_etapes_optionnelles_sans_referentiel(monkeypatch, tmp_path):
    _environnement(monkeypatch, tmp_path)
    etat = pipeline.executer({"document": "inutile.pdf", "nom": "Règlement fictif",
                              "etapes": ["agent1", "dedoublonnage", "agent2"],
                              "dossier_resultats": str(tmp_path / "res")})
    # agent2 demandé mais impossible sans référentiel : le routeur s'arrête après le dédoublonnage
    assert [e["etape"] for e in etat["journal_etapes"]] == ["agent1", "dedoublonnage"]
    assert etat["dedoublonne"].endswith("_consolide_dedoublonne.json")


def test_estimation_et_garde_fou(monkeypatch, tmp_path):
    _environnement(monkeypatch, tmp_path)
    est = pipeline.estimer({"document": "x.pdf", "nom": "n", "etapes": ["agent1", "rattrapage"]})
    assert set(est["detail"]) == {"agent1", "rattrapage"} and est["total"] > 0
    try:
        pipeline._pas({"nb_etapes": pipeline.MAX_ETAPES}, "x")
        assert False, "le garde-fou aurait dû lever"
    except RuntimeError:
        pass


def test_version_des_prompts_transmise(monkeypatch, tmp_path):
    client = _environnement(monkeypatch, tmp_path)
    etat = pipeline.executer({"document": "inutile.pdf", "nom": "Règlement fictif", "version": "v4a",
                              "etapes": ["agent1"], "dossier_resultats": str(tmp_path / "res")})
    entete = json.loads(open(etat["run_agent1"], encoding="utf-8").readline())
    assert entete["version_prompt"] == "v4a"
    assert "Destinataire" in client.requetes[0]["system"][0]["text"]
