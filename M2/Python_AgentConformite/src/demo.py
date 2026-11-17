"""Mode démonstration : préparation des résultats figés que l'application relit sans clé API.

Depuis la révocation des clés (31/10), l'application déployée ne fait AUCUN appel : elle relit
des runs déjà effectués. Ce module contient les calculs (purs, testés) qui transforment les
mesures brutes en tableaux prêts à afficher :

- courbe_longueur : rappel du passage unique selon la longueur du document
  (préfixes S01…Sk, expérience du 31/10) ;
- regression_longueur : pente du rappel en fonction de la longueur, sur toutes les répétitions ;
- controles_couverture : couverture de l'Agent 2 sur des référentiels de contrôle (placebo,
  sous-échantillons), recalculée sur un dénominateur FIXE pour neutraliser l'instabilité du
  classement « hors périmètre » du juge.

scripts/preparer_demo.py appelle ces fonctions et copie les fichiers utiles dans demo/.
"""

import re

from src import metriques


def _fin_plage(cle: str, nb_sections: int) -> int | None:
    """« unique:S01-S08 » → 8 ; « unique:S01 » → 1 ; « unique:complet » → nb_sections."""
    if cle.endswith(":complet"):
        return nb_sections
    m = re.search(r":S(\d+)(?:-S(\d+))?$", cle)
    if not m:
        return None
    return int(m.group(2) or m.group(1))


def courbe_longueur(repetitions: dict, sections: list[dict]) -> list[dict]:
    """Un point par préfixe S01…Sk : longueur en tokens et rappel moyen (± écart-type).

    `repetitions` : sortie de scripts/repetitions.py sur les runs en passage unique.
    `sections`    : sections du document complet (decouper.py), avec tokens_exacts si
                    disponibles, sinon tokens_estimes. Seules les plages qui commencent à S01
                    sont retenues. Le préfixe d'une seule section est signalé « exclu » : son
                    rappel nul (22 lignes produites, 0 retrouvée) contredit tous les autres
                    préfixes et relève d'un défaut de mesure sur un mini-document d'une section.
    """
    tokens = [s.get("tokens_exacts") or s.get("tokens_estimes") or 0 for s in sections]
    points = []
    for cle, g in repetitions.items():
        if cle.startswith("_") or not cle.startswith("unique:"):
            continue
        if not (cle.endswith(":complet") or re.search(r":S0*1(?:-|$)", cle)):
            continue
        k = _fin_plage(cle, len(sections))
        if not k or k > len(sections):
            continue
        rl, rs = g.get("rappel_large") or {}, g.get("rappel_stricte") or {}
        points.append({"configuration": cle, "k": k, "tokens": sum(tokens[:k]),
                       "repetitions": g.get("k"), "rappel_large": rl.get("moyenne"),
                       "ecart_type": rl.get("ecart_type"), "rappel_stricte": rs.get("moyenne"),
                       "lignes": (g.get("nb_lignes") or {}).get("moyenne"),
                       "reflexion_tokens": (g.get("reflexion_tokens") or {}).get("moyenne"),
                       "rappels_individuels": g.get("_rappels_large") or [],
                       "exclu": k == 1})
    return sorted(points, key=lambda p: p["k"])


def regression_longueur(points: list[dict]) -> dict:
    """MCO du rappel large de CHAQUE répétition sur la longueur (en milliers de tokens)."""
    x, y = [], []
    for p in points:
        if p["exclu"]:
            continue
        for r in p["rappels_individuels"]:
            x.append(p["tokens"] / 1000)
            y.append(r)
    res = metriques.regression(x, y)
    if res.get("pente") is not None:
        res["pente_par_10k_tokens"] = 10 * res["pente"]
    return res


def controles_couverture(runs: list[dict], exclues_fixes: set[str]) -> list[dict]:
    """Couverture sur un dénominateur FIXE : toutes les lignes de référence sauf `exclues_fixes`.

    `runs` : [{"nom", "nb_lignes_ia", "evaluations"}] où evaluations vient de l'Agent 2.
    Une ligne que le juge classe « hors périmètre » dans un run, mais qui n'est pas dans
    `exclues_fixes`, compte comme NON couverte (et score 0) : le dénominateur ne bouge pas.
    """
    sortie = []
    for r in runs:
        evals = [e for e in r["evaluations"] if e["id_ref"] not in exclues_fixes]
        n = len(evals)
        couvertes = sum(e["couverture"] in ("totale", "partielle") for e in evals)
        totales = sum(e["couverture"] == "totale" for e in evals)
        score = sum((e.get("score") or 0.0) for e in evals if e["couverture"] != "hors_perimetre")
        hp = sorted(e["id_ref"] for e in r["evaluations"] if e["couverture"] == "hors_perimetre")
        sortie.append({"controle": r["nom"], "lignes_ia": r["nb_lignes_ia"], "denominateur": n,
                       "couvertes": couvertes, "couverture_large": couvertes / n if n else None,
                       "couverture_stricte": totales / n if n else None,
                       "qualite": score / n if n else None, "hors_perimetre_juge": ", ".join(hp)})
    return sortie
