"""Tests du dédoublonnage. AUCUN appel API : faux client."""

import json

from src import appel_llm, dedoublonnage as dd
from tests.test_agent1 import FauxClient


def _l(i, obl, cit, d, f, par, statut="valide", ref=None, **kw):
    return {"id": i, "ref": ref or par, "cit": cit, "obl": obl, "dom": "x", "typ": "mesure", "crit": "majeure",
            "_verif": {"statut": statut, "debut": d, "fin": f, "paragraphe": par}, **kw}


LIGNES = [
    _l("S01-001", "Keep a register of incidents for five years.", "shall keep a register", 0, 40, "1.1"),
    _l("S01-002", "Keep a register of incidents for five years.", "shall keep a register", 0, 40, "1.1"),   # exact
    _l("S02-001", "Keep the incident register for five years.", "register shall be kept", 500, 540, "2.4"),  # proche
    _l("S02-002", "Review the register every quarter.", "review it quarterly", 600, 640, "2.5"),            # isolée
    _l("R1-001", "Keep a register of incidents during five years.", "keep a register of incidents", 10, 50,
       "1.1", _rattrapage=True),                                                                             # chevauche
]


def test_exacts_candidats_et_grappes():
    assert dd.doublons_exacts(LIGNES) == [["S01-001", "S01-002"]]
    paires = dd.candidats(LIGNES)
    assert not any("S02-002" in (p["a"], p["b"]) for p in paires)
    assert any(p["a"] == "S01-001" and p["b"] == "R1-001" and "citations_chevauchantes" in p["motifs"] for p in paires)
    gr = dd.grappes(LIGNES, paires)
    assert len(gr) == 1 and set(gr[0]) == {"S01-001", "S01-002", "S02-001", "R1-001"}


def test_representant_deterministe():
    # citation valide d'abord, puis extraction plutôt que rattrapage, puis référence la plus longue
    groupe = [LIGNES[4], LIGNES[2], {**LIGNES[0], "_verif": {**LIGNES[0]["_verif"], "statut": "introuvable"}}]
    assert dd.representant(groupe)["id"] == "S02-001"


def test_lire_verdicts_cliques_et_rejet_de_l_invente():
    attendues = {"G001": ["A", "B", "C"], "G002": ["D", "E"]}
    paires = [{"a": "A", "b": "B", "doublon": True, "difference": "aucune"},
              {"a": "B", "b": "C", "doublon": True, "difference": "aucune"},
              {"a": "A", "b": "C", "doublon": False, "difference": "autre cas"},   # pas de chaînage A–B–C
              {"a": "A", "b": "Z", "doublon": True, "difference": "aucune"}]      # Z inventé
    brut = json.dumps({"grappes": [{"grappe": "G001", "paires": paires}, {"grappe": "G999", "paires": []}]})
    v, anomalies = dd.lire_verdicts(brut, attendues)
    assert v["G001"]["groupes"] == [["A", "B"]]
    raisons = {a["raison"] for a in anomalies}
    assert {"paire hors grappe ignorée", "grappe inconnue", "grappe sans verdict (conservée telle quelle)"} <= raisons


def test_veto_meme_tache():
    a = _l("S07-014", "Assume the benchmark is not altered when assessing probability.", "x", 0, 10, "6.8.4", _tache="S07")
    b = _l("S07-015", "Assume the benchmark is not altered when assessing reclassification.", "y", 20, 30, "6.8.5",
           _tache="S07")
    c = _l("S20-001", "Assume the benchmark is not altered when assessing probability.", "z", 900, 910, "B6.8.4",
           _tache="S20")
    ids = {(p["a"], p["b"]) for p in dd.candidats([a, b, c])}
    assert ("S07-014", "S07-015") not in ids and ("S07-014", "S20-001") in ids


def test_executer_bout_en_bout(monkeypatch, tmp_path):
    vrai = lambda a, b: {"a": a, "b": b, "difference": "aucune", "doublon": True}
    reponse = json.dumps({"grappes": [{"grappe": "G001", "paires": [
        vrai("S01-001", "S02-001"), vrai("S01-001", "R1-001"), vrai("S02-001", "R1-001")]}]})
    client = FauxClient(reponse)
    monkeypatch.setattr(appel_llm, "_client", lambda: client)
    res = dd.executer(LIGNES, journal=tmp_path / "j.jsonl", dossier_cache=tmp_path / "c")
    ids = [l["id"] for l in res["lignes"]]
    assert ids == ["S01-001", "S02-002"] and res["stats"]["doublons_exacts"] == 1
    conservee = res["lignes"][0]
    assert {d["id"] for d in conservee["_doublons"]} == {"S01-002", "S02-001", "R1-001"}  # aucune trace perdue
    assert dd.table_de_correspondance(res["fusions"]) == {"S01-002": "S01-001", "S02-001": "S01-001",
                                                           "R1-001": "S01-001"}
    requete = client.requetes[0]
    assert requete["model"] == dd.config.MODELE_EXTRACTION  # v2 : Sonnet par défaut (mesure du 26/10)
    assert "TÂCHE" not in requete["messages"][0]["content"] and "<grappe id=\"G001\">" in requete["messages"][0]["content"]


def test_prompt_dedoublonnage_sans_corpus():
    for v in ("v1", "v2"):
        c = (dd.agent1.DOSSIER_PROMPTS / f"dedoublonnage_{v}.txt").read_text(encoding="utf-8").lower()
        for interdit in ("ifrs", "sapin", "corruption", "deloitte"):
            assert interdit not in c
