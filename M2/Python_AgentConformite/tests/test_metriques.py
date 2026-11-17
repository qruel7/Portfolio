"""Tests des métriques (section 4.4). AUCUN appel API."""

import pytest

from src import metriques
from src.decoupage import Section


def _l(i, d, f, par, statut="valide"):
    return {"id": i, "_verif": {"statut": statut, "debut": d, "fin": f, "paragraphe": par}}


def test_rappel_precision_f1():
    m = metriques.rappel_precision_f1(n_commun_ref=8, n_ref=10, n_commun_ia=12, n_ia=20)
    assert m["rappel"] == 0.8 and m["precision"] == 0.6
    assert m["f1"] == pytest.approx(2 * 0.6 * 0.8 / 1.4)


def test_jaccard_moyen_sur_les_paires():
    j = metriques.jaccard_moyen([{1, 2, 3}, {1, 2}, {1, 2, 3}])
    # paires : 2/3, 1, 2/3 → moyenne 7/9
    assert j["nb_paires"] == 3 and j["jaccard_moyen"] == pytest.approx(7 / 9)


def test_regression_pente_exacte():
    r = metriques.regression([1, 2, 3, 4, 5], [1.0, 0.9, 0.8, 0.7, 0.6])
    assert r["pente"] == pytest.approx(-0.1) and r["r2"] == pytest.approx(1.0)


def test_retrouvees_stricte_et_large():
    ref = [_l("R1", 0, 50, "1.1"), _l("R2", 100, 150, "1.2"), _l("R3", 300, 350, "2.1"),
           _l("R4", 400, 450, "2.2", statut="introuvable")]  # R4 hors de R* (citation non valide)
    run = [_l("U1", 40, 80, "1.1"),        # chevauche R1
           _l("U2", 160, 190, "1.2"),      # même paragraphe que R2, sans chevauchement
           _l("U3", 310, 320, "2.1", statut="introuvable")]  # invalide : ignorée
    d = {x["id"]: x for x in metriques.retrouvees(ref, run)}
    assert set(d) == {"R1", "R2", "R3"}
    assert d["R1"]["stricte"] and d["R1"]["large"]
    assert not d["R2"]["stricte"] and d["R2"]["large"]
    assert not d["R3"]["stricte"] and not d["R3"]["large"]


def test_essoufflement_pente_negative_detectee():
    sections = [Section(id=f"S{k:02d}", titre="", debut=1000 * k, fin=1000 * (k + 1), tokens_estimes=250, cles=[])
                for k in range(10)]
    ref, run = [], []
    for k in range(10):
        for j in range(20):
            d = 1000 * k + 40 * j
            ref.append(_l(f"R{k}-{j}", d, d + 30, f"{k}.{j}"))
            if j < 20 - 2 * k:  # le run « s'essouffle » : 100 % au début, 10 % à la fin
                run.append(_l(f"U{k}-{j}", d, d + 30, f"{k}.{j}"))
    res = metriques.essoufflement(ref, run, sections, 10_000)
    assert res["par_section"][0]["r_stricte"] == 1.0 and res["par_section"][-1]["r_stricte"] == pytest.approx(0.1)
    for nom in ("sections_stricte", "lignes_stricte"):
        assert res["regressions"][nom]["pente"] < 0 and res["regressions"][nom]["p_valeur"] < 0.001


def test_precision_des_references():
    lignes = [
        {"ref": "5.5.17(a)", "_verif": {"statut": "valide", "paragraphe": "5.5.17"}},          # exacte
        {"ref": "Article 17", "_verif": {"statut": "valide", "paragraphe": "Article 17 II"}},   # trop large
        {"ref": "art. 17, II, 1°", "_verif": {"statut": "valide", "paragraphe": "Article 17 II"}},  # exacte
        {"ref": "B5.5.17–B5.5.20", "_verif": {"statut": "valide", "paragraphe": "B5.5.18"}},   # intervalle
        {"ref": "3.1", "_verif": {"statut": "introuvable", "paragraphe": None}},                # ignorée
    ]
    r = metriques.precision_references(lignes)
    assert (r["n"], r["exacte"], r["trop_large"], r["intervalle"]) == (4, 2, 1, 1)
