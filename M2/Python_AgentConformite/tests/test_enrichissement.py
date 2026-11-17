"""Enrichissement seul sur extraction figée. AUCUN appel API."""

from src import appel_llm
from src.enrichissement import enrichir
from tests.test_agent1 import REPONSE, TEXTE, FauxClient

LIGNES = [{"id": "S01-001", "ref": "1.2", "cit": "x", "dom": "d", "obl": "Tenir un registre.", "typ": "mesure",
           "crit": "majeure", "ctrl": "ANCIEN", "test": "ANCIEN", "_tache": "S01"}]


def test_repetitions_distinctes_et_extraction_intacte(monkeypatch, tmp_path):
    client = FauxClient(REPONSE)
    monkeypatch.setattr(appel_llm, "_client", lambda: client)
    kw = dict(texte=TEXTE, nom_document="Règlement fictif", version="v4", journal=tmp_path / "j.jsonl",
              dossier_cache=tmp_path / "c")
    r1 = enrichir(LIGNES, repetition=1, **kw)
    r2 = enrichir(LIGNES, repetition=2, **kw)
    r1bis = enrichir(LIGNES, repetition=1, **kw)
    assert len(client.requetes) == 2  # r1 et r2 appellent l'API ; r1 relancé vient du cache disque
    l = r1["lignes"][0]
    assert l["ctrl"] == "Contrôle S01-001." and l["obl"] == "Tenir un registre." and l["_tache"] == "S01"
    assert r1bis["lignes"] == r1["lignes"] and not r1["non_enrichies"]
    assert "Parcours la grille" in client.requetes[0]["system"][0]["text"]  # consigne v4
