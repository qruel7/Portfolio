"""Tests de l'Agent 2 et de la lecture des référentiels. AUCUN appel API, référentiels INVENTÉS."""

import json
import re

import openpyxl
import pytest

from src import agent2, appel_llm
from src.referentiels import charger_referentiel, ligne_en_texte

LIGNES_IA = [
    {"id": "S01-001", "ref": "12.4", "dom": "conservation", "obl": "Conserver les registres cinq ans.",
     "ctrl": "Archivage quotidien, contrôle mensuel de complétude.", "test": "Échantillon de 25 jours."},
    {"id": "S01-002", "ref": "12.5", "dom": "accès", "obl": "Mettre les registres à disposition.",
     "ctrl": "Procédure d'accès.", "test": "Demande fictive."},
    {"id": "S02-001", "ref": "13.1", "dom": "formation", "obl": "Former le personnel.",
     "ctrl": "Plan annuel.", "test": "Feuilles de présence."},
]


def _xlsx(tmp_path, titre=True, avec_id=False):
    wb = openpyxl.Workbook()
    ws = wb.active
    if titre:
        ws.append(["Référentiel fictif - recommandations", None, None])
    entete = (["CTRL_ID"] if avec_id else []) + ["Classification", "Constat", "Criticité"]
    ws.append(entete)
    lignes = [["Conservation", "Pas de responsable du contrôle de complétude.", "Majeure"],
              ["Conservation", "Durée de conservation non définie.", None],
              ["Données", "Aucune règle de portabilité des données.", "Mineure"]]
    for k, l in enumerate(lignes):
        ws.append(([f"C_{k}"] if avec_id else []) + l)
    ws.append([None, None, None])  # ligne vide résiduelle
    chemin = tmp_path / "ref.xlsx"
    wb.save(chemin)
    return chemin


def test_lecture_generique_titre_fusionne_et_cellule_vide(tmp_path):
    r = charger_referentiel(_xlsx(tmp_path))
    assert r["colonnes"] == ["Classification", "Constat", "Criticité"]
    assert [l["id_ref"] for l in r["lignes"]] == ["L3", "L4", "L5"]  # numéros de ligne Excel
    assert r["lignes"][1]["champs_vides"] == ["Criticité"]  # signalée, pas imputée
    assert "(vide)" in ligne_en_texte(r["lignes"][1])


def test_lecture_avec_colonne_identifiant(tmp_path):
    r = charger_referentiel(_xlsx(tmp_path, titre=False, avec_id=True))
    assert r["colonne_id"] == "CTRL_ID" and [l["id_ref"] for l in r["lignes"]] == ["C_0", "C_1", "C_2"]
    # les blocs ignorent la colonne d'identifiant et regroupent par la colonne suivante
    assert [len(b) for b in agent2._blocs(r["lignes"], 4, r["colonne_id"])] == [2, 1]


def test_couverture_decidee_par_le_code():
    v = lambda *n: {"hors_perimetre": False, "elements": [{"niveau": x} for x in n]}
    assert agent2.couverture_ligne(v("equivalent", "equivalent")) == ("totale", 1.0)
    assert agent2.couverture_ligne(v("absent", "principe")) == ("partielle", 0.25)
    assert agent2.couverture_ligne(v("absent", "absent")) == ("absente", 0.0)
    assert agent2.couverture_ligne({"hors_perimetre": True, "elements": []}) == ("hors_perimetre", None)


def test_ids_inventes_retires_et_element_retrograde():
    v = {"hors_perimetre": False, "elements": [
        {"element": "a", "niveau": "equivalent", "lignes": ["S01-001", "ZZZ-999"], "justification": ""},
        {"element": "b", "niveau": "principe", "lignes": ["ZZZ-998"], "justification": ""}]}
    v, inventes = agent2.nettoyer_verdict(v, {"S01-001"})
    assert inventes == ["ZZZ-999", "ZZZ-998"]
    assert v["elements"][0]["lignes"] == ["S01-001"] and v["elements"][1]["niveau"] == "absent"


class FauxClient:
    def __init__(self):
        self.requetes, self.messages = [], self

    def _repondre(self, msg):
        if "TÂCHE : APPARIEMENT" in msg:
            ids = re.findall(r'id_ref="([^"]+)"', msg)
            verdicts = []
            for i in ids:
                if "portabilité" in msg.split(f'id_ref="{i}"')[1].split("</ligne_reference>")[0]:
                    verdicts.append({"id_ref": i, "hors_perimetre": True, "justification": "autre texte", "elements": []})
                else:
                    verdicts.append({"id_ref": i, "hors_perimetre": False, "justification": "ok", "elements": [
                        {"element": "contrôle", "niveau": "equivalent", "lignes": ["S01-001"], "justification": "x"},
                        {"element": "preuve", "niveau": "principe", "lignes": ["INVENTE-1"], "justification": "y"}]})
            return json.dumps({"verdicts": verdicts})
        ids = [l.strip() for l in msg.split("seules :")[1].splitlines() if l.strip()]
        return json.dumps({"verdicts": [{"id": i, "p": "pertinente", "raison": "r"} for i in ids]})

    def stream(self, **requete):
        self.requetes.append(requete)
        texte = self._repondre(requete["messages"][0]["content"])

        class _U:
            input_tokens, output_tokens = 50, 300
            cache_creation_input_tokens = 1_000 if len(self.requetes) == 1 else 0
            cache_read_input_tokens = 0 if len(self.requetes) == 1 else 1_000

        class _M:
            id, stop_reason, usage = "msg", "end_turn", _U()

            def model_dump(s):
                usage = {k: getattr(_U, k) for k in ("input_tokens", "output_tokens",
                                                     "cache_creation_input_tokens", "cache_read_input_tokens")}
                return {"id": "msg", "stop_reason": "end_turn", "usage": usage,
                        "content": [{"type": "text", "text": texte}]}

        class _F:
            def __enter__(s):
                return s

            def __exit__(s, *a):
                return False

            def get_final_message(s):
                return _M()

        return _F()


def test_executer_bout_en_bout(monkeypatch, tmp_path):
    client = FauxClient()
    monkeypatch.setattr(appel_llm, "_client", lambda: client)
    ref = charger_referentiel(_xlsx(tmp_path))
    res = agent2.executer(lignes_ia=LIGNES_IA, referentiel=ref, nom_document="Règlement fictif",
                          id_source="run-test", dossier_resultats=tmp_path / "res",
                          journal=tmp_path / "j.jsonl", dossier_cache=tmp_path / "c")
    m = res["metriques"]
    # L5 (portabilité) est hors périmètre ; L3 et L4 : un élément equivalent + un rétrogradé (id inventé)
    assert m["nb_hors_perimetre"] == 1 and m["nb_evaluees"] == 2
    assert m["comptes"] == {"totale": 0, "partielle": 2, "absente": 0}
    assert m["couverture_stricte"] == 0 and m["couverture_large"] == 1.0
    assert m["qualite_moyenne"] == pytest.approx(0.5)  # (2 + 0) / 2 éléments / 2
    assert all(e["ids_inventes"] == ["INVENTE-1"] for e in res["evaluations"] if e["couverture"] == "partielle")
    # S01-001 est mobilisée ; les deux autres lignes IA passent au jugement de pertinence
    assert sorted(p["id"] for p in res["pertinences"]) == ["S01-002", "S02-001"]
    # préfixe identique pour toutes les requêtes (cache) ; les lignes de référence ne sont QUE dans les messages
    assert all(r["system"] == client.requetes[0]["system"] for r in client.requetes)
    assert "Pas de responsable" not in json.dumps(client.requetes[0]["system"], ensure_ascii=False)
    enreg = [json.loads(l) for l in open(res["fichier"], encoding="utf-8")]
    assert enreg[0]["type"] == "entete" and enreg[-1]["type"] == "synthese"


def test_prompts_agent2_sans_corpus():
    for f in agent2.DOSSIER_PROMPTS.glob("agent2_*.txt"):
        c = f.read_text(encoding="utf-8").lower()
        for interdit in ("ifrs", "sapin", "corruption", "ias 39"):
            assert interdit not in c, f.name


def test_alias_id_accepte_et_reanalyse(monkeypatch, tmp_path):
    ref = charger_referentiel(_xlsx(tmp_path))
    brut = json.dumps({"verdicts": [{"id": "L3", "hors_perimetre": False, "justification": "j",
                                     "elements": [{"element": "e", "niveau": "equivalent", "lignes": ["S01-001"]}]}]})
    evals, rejets = agent2.evaluer_bloc(brut, ref["lignes"][:1], {"S01-001"})
    assert rejets == [] and evals[0]["couverture"] == "totale"
    # ré-analyse d'un run enregistré : aucun appel, mêmes règles
    run = tmp_path / "run.jsonl"
    run.write_text("\n".join(json.dumps(e) for e in [
        {"type": "entete"}, {"type": "appariement", "ids_ref": ["L3"], "reponse_brute": brut},
        {"type": "pertinence", "ids": ["S01-001", "S01-002"],
         "reponse_brute": json.dumps({"verdicts": [{"id": "S01-001", "p": "faible"}, {"id": "S01-002", "p": "pertinente"}]})},
    ]), encoding="utf-8")
    res = agent2.reanalyser(run, LIGNES_IA, ref)
    assert res["metriques"]["couverture_stricte"] == 1.0
    assert [p["id"] for p in res["pertinences"]] == ["S01-002"]  # S01-001 est mobilisée : plus « supplémentaire »
