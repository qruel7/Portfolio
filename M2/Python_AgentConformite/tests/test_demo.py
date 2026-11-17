"""Tests du mode démonstration (src/demo.py). AUCUN appel API, données inventées."""

from src import demo

SECTIONS = [{"id": f"S{i:02d}", "tokens_estimes": 1000, "tokens_exacts": 1100} for i in range(1, 5)]


def _groupe(rappels, lignes=10):
    m = sum(rappels) / len(rappels)
    return {"k": len(rappels), "rappel_large": {"moyenne": m, "ecart_type": 0.0 if len(rappels) > 1 else None},
            "rappel_stricte": {"moyenne": m / 2}, "nb_lignes": {"moyenne": lignes}, "_rappels_large": rappels}


def test_courbe_longueur_tokens_cumules_et_exclusion():
    rep = {"unique:S01": _groupe([0.0]), "unique:S01-S02": _groupe([1.0, 0.9]), "unique:S01-S03": _groupe([0.7]),
           "unique:complet": _groupe([0.5, 0.5]), "unique:S03-S04": _groupe([0.9]), "section:complet": _groupe([0.95]),
           "_comparaisons": {}}
    pts = demo.courbe_longueur(rep, SECTIONS)
    assert [p["k"] for p in pts] == [1, 2, 3, 4]  # S03-S04 et le mode section sont écartés
    assert pts[1]["tokens"] == 2200 and pts[3]["tokens"] == 4400  # tokens exacts cumulés
    assert pts[0]["exclu"] and not pts[1]["exclu"]


def test_regression_longueur_sur_les_repetitions():
    rep = {"unique:S01-S02": _groupe([1.0, 0.9]), "unique:S01-S03": _groupe([0.7, 0.8]), "unique:complet": _groupe([0.5, 0.6])}
    reg = demo.regression_longueur(demo.courbe_longueur(rep, SECTIONS))
    assert reg["n"] == 6 and reg["pente"] < 0
    assert abs(reg["pente_par_10k_tokens"] - 10 * reg["pente"]) < 1e-12


def test_controles_couverture_denominateur_fixe():
    ref = [{"id_ref": "L1", "couverture": "totale", "score": 1.0}, {"id_ref": "L2", "couverture": "partielle", "score": 0.5},
           {"id_ref": "L3", "couverture": "hors_perimetre", "score": None}]
    ctl = [{"id_ref": "L1", "couverture": "hors_perimetre", "score": None},  # le juge l'exclut ici : comptée non couverte
           {"id_ref": "L2", "couverture": "partielle", "score": 0.5}, {"id_ref": "L3", "couverture": "absente", "score": 0.0}]
    lignes = demo.controles_couverture([{"nom": "complet", "nb_lignes_ia": 10, "evaluations": ref},
                                        {"nom": "echantillon", "nb_lignes_ia": 2, "evaluations": ctl}], {"L3"})
    assert [l["denominateur"] for l in lignes] == [2, 2]
    assert lignes[0]["couverture_large"] == 1.0 and lignes[0]["couverture_stricte"] == 0.5 and lignes[0]["qualite"] == 0.75
    assert lignes[1]["couverture_large"] == 0.5 and lignes[1]["qualite"] == 0.25 and lignes[1]["hors_perimetre_juge"] == "L1"
