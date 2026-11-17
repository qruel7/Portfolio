"""Métriques du projet (section 4.4 des instructions). AUCUN appel API.

- Justesse : rappel, précision, F1 sur des ensembles d'identifiants appariés.
- Reproductibilité : Jaccard moyen sur les paires de répétitions.
- Essoufflement : rappel par section r(c) d'un run contre une référence, puis
  régression de r(c) sur la position c ; une pente négative significative mesure
  l'essoufflement.

La pseudo-référence R* (décision à faire valider) est l'union des lignes du mode
section par section (rattrapage compris) dont la citation est valide. Une ligne de
R* est « retrouvée » par un autre run selon une règle DÉTERMINISTE fondée sur la
position des citations dans le texte source :
- stricte : une citation valide du run chevauche la citation de la ligne de R* ;
- large   : une citation valide du run tombe dans le même paragraphe numéroté.
"""

import math
from bisect import bisect_right
from itertools import combinations

# ----------------------------------------------------------------------------- justesse


def rappel_precision_f1(n_commun_ref: int, n_ref: int, n_commun_ia: int, n_ia: int) -> dict:
    """r = |A∩R|/|R| et p = |A∩R|/|A|.

    |A∩R| peut se compter côté référence (lignes de R couvertes) ou côté IA (lignes
    de A qui couvrent quelque chose) : les deux comptes diffèrent dès qu'une ligne
    couvre plusieurs lignes de l'autre ensemble, on les passe donc séparément.
    """
    r = n_commun_ref / n_ref if n_ref else None
    p = n_commun_ia / n_ia if n_ia else None
    f1 = 2 * p * r / (p + r) if p is not None and r is not None and (p + r) else (0.0 if p is not None and r is not None else None)
    return {"rappel": r, "precision": p, "f1": f1}


# ----------------------------------------------------------------------- reproductibilité


def jaccard(a: set, b: set) -> float:
    u = a | b
    return len(a & b) / len(u) if u else 1.0


def jaccard_moyen(ensembles: list[set]) -> dict:
    """J̄ = (k(k−1)/2)⁻¹ Σ_{i<j} |Aᵢ∩Aⱼ| / |Aᵢ∪Aⱼ|."""
    paires = [jaccard(a, b) for a, b in combinations(ensembles, 2)]
    return {"k": len(ensembles), "nb_paires": len(paires),
            "jaccard_moyen": sum(paires) / len(paires) if paires else None, "paires": paires}


# ------------------------------------------------------------------------- régression


def _betacf(a: float, b: float, x: float) -> float:
    """Fraction continue de la bêta incomplète (Numerical Recipes, betacf)."""
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-300 else 1e-300
        dl = d * c
        h *= dl
        if abs(dl - 1) < 1e-14:
            break
    return h


def _beta_incomplete(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1 - math.exp(lbt) * _betacf(b, a, 1 - x) / b


def _p_bilaterale_t(t: float, ddl: int) -> float:
    """P(|T| > |t|) pour une loi de Student à ddl degrés de liberté, sans scipy."""
    if math.isinf(t):
        return 0.0
    return _beta_incomplete(ddl / 2, 0.5, ddl / (ddl + t * t))


def _quantile_t(p: float, ddl: int) -> float:
    """Quantile d'ordre p (> 0,5) de Student, par dichotomie sur la fonction de répartition."""
    bas, haut = 0.0, 1000.0
    for _ in range(200):
        milieu = (bas + haut) / 2
        if 1 - _p_bilaterale_t(milieu, ddl) / 2 < p:
            bas = milieu
        else:
            haut = milieu
    return (bas + haut) / 2


def regression(x: list[float], y: list[float]) -> dict:
    """MCO de y sur x : pente, écart-type, t, p-valeur bilatérale, IC à 95 %, R²."""
    n = len(x)
    if n < 3:
        return {"n": n, "pente": None}
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    if sxx == 0:
        return {"n": n, "pente": None}
    pente = sxy / sxx
    constante = my - pente * mx
    residus = [b - (constante + pente * a) for a, b in zip(x, y)]
    scr = sum(e * e for e in residus)
    sct = sum((b - my) ** 2 for b in y)
    ddl = n - 2
    sigma2 = scr / ddl
    se = math.sqrt(sigma2 / sxx)
    t = pente / se if se > 0 else float("inf")
    p = _p_bilaterale_t(t, ddl) if se > 0 else 0.0
    q = _quantile_t(0.975, ddl)
    return {"n": n, "constante": constante, "pente": pente, "ecart_type": se, "t": t, "p_valeur": p,
            "ic95": (pente - q * se, pente + q * se), "r2": 1 - scr / sct if sct else None}


# ------------------------------------------------------------------------ essoufflement


def _valides(lignes: list[dict]) -> list[dict]:
    return [l for l in lignes if (l.get("_verif") or {}).get("statut") == "valide"]


def retrouvees(reference: list[dict], run: list[dict]) -> list[dict]:
    """Pour chaque ligne valide de la référence : retrouvée (stricte / large) par le run ?"""
    cits = sorted(((l["_verif"]["debut"], l["_verif"]["fin"]) for l in _valides(run)))
    debuts = [d for d, _ in cits]
    paragraphes = {l["_verif"]["paragraphe"] for l in _valides(run) if l["_verif"].get("paragraphe")}
    fin_max = []  # fin maximale des intervalles jusqu'à k : test de chevauchement en O(log n)
    m = -1
    for _, f in cits:
        m = max(m, f)
        fin_max.append(m)
    sortie = []
    for l in _valides(reference):
        d, f = l["_verif"]["debut"], l["_verif"]["fin"]
        k = bisect_right(debuts, f - 1) - 1  # intervalles qui commencent avant la fin de la citation
        stricte = k >= 0 and fin_max[k] > d
        sortie.append({"id": l["id"], "debut": d, "paragraphe": l["_verif"].get("paragraphe"),
                       "stricte": stricte, "large": stricte or l["_verif"].get("paragraphe") in paragraphes})
    return sortie


def rappel_par_section(detail: list[dict], sections: list) -> list[dict]:
    """r(c) = |A∩R_c| / |R_c| pour chaque section c (numérotée à partir de 1)."""
    lignes = []
    for c, s in enumerate(sections, start=1):
        dans = [x for x in detail if s.debut <= x["debut"] < s.fin]
        n = len(dans)
        lignes.append({"c": c, "section": s.id, "n_ref": n,
                       "n_stricte": sum(x["stricte"] for x in dans), "n_large": sum(x["large"] for x in dans),
                       "r_stricte": sum(x["stricte"] for x in dans) / n if n else None,
                       "r_large": sum(x["large"] for x in dans) / n if n else None})
    return lignes


def essoufflement(reference: list[dict], run: list[dict], sections: list, longueur_texte: int) -> dict:
    """Rappel du run contre la référence, par section et par position.

    Deux régressions pour chaque règle d'appariement :
    - « sections » : r(c) sur c, une observation par section non vide (formule de l'enseignant) ;
    - « lignes »   : indicatrice retrouvée (0/1) sur la position relative de la citation
      dans le texte (0 = début, 1 = fin). Modèle de probabilité linéaire, beaucoup plus
      d'observations, donc plus de puissance ; la pente se lit en points de rappel
      entre le début et la fin du texte.
    """
    detail = retrouvees(reference, run)
    par_section = rappel_par_section(detail, sections)
    res = {"n_reference": len(detail), "n_run_valides": len(_valides(run)), "n_run": len(run),
           "par_section": par_section, "regressions": {}, "detail": detail}
    for regle in ("stricte", "large"):
        pts = [(x["c"], x[f"r_{regle}"]) for x in par_section if x["n_ref"]]
        res[f"rappel_{regle}"] = sum(x[regle] for x in detail) / len(detail) if detail else None
        res["regressions"][f"sections_{regle}"] = regression([a for a, _ in pts], [b for _, b in pts])
        res["regressions"][f"lignes_{regle}"] = regression([x["debut"] / longueur_texte for x in detail],
                                                           [float(x[regle]) for x in detail])
    return res


def densite_par_section(run: list[dict], sections: list) -> list[dict]:
    """Lignes valides par millier de tokens de section, et taux de citations invalides, selon la position."""
    sortie = []
    for c, s in enumerate(sections, start=1):
        ici = [l for l in run if (l.get("_verif") or {}).get("debut") is not None
               and s.debut <= l["_verif"]["debut"] < s.fin]
        valides = sum(l["_verif"]["statut"] == "valide" for l in ici)
        sortie.append({"c": c, "section": s.id, "lignes_valides": valides,
                       "densite_par_mille_tokens": 1000 * valides / s.tokens_estimes if s.tokens_estimes else None})
    return sortie


# ---------------------------------------------------------------- précision des références


def precision_references(lignes: list[dict]) -> dict:
    """Compare `ref` au paragraphe où la citation a été TROUVÉE (vérification déterministe).

    exacte      : la référence désigne exactement ce paragraphe (« 5.5.17(a) » ↔ 5.5.17) ;
    trop_large  : elle désigne un niveau supérieur (« Article 17 » pour une citation du 17 II) ;
    intervalle  : la référence est un intervalle de paragraphes ;
    autre       : autre écart. Seules les lignes à citation valide sont comptées.
    """
    import re

    from src.couverture import base_ref

    comptes = {"exacte": 0, "trop_large": 0, "intervalle": 0, "autre": 0}
    for l in lignes:
        v = l.get("_verif") or {}
        par = v.get("paragraphe")
        if v.get("statut") != "valide" or not par:
            continue
        ref = l.get("ref") or ""
        b = base_ref(ref)
        if re.search(r"\d\s*[–-]\s*[A-Z]{0,3}\d", ref) and not ref.lower().startswith(("art", "l.")):
            comptes["intervalle"] += 1
        elif b == par:
            comptes["exacte"] += 1
        elif par.startswith(b + " ") or par.startswith(b + "."):
            comptes["trop_large"] += 1
        else:
            comptes["autre"] += 1
    n = sum(comptes.values())
    return {"n": n, **comptes, "taux_exacte": comptes["exacte"] / n if n else None}


def hors_zone(lignes: list[dict], sections: list[dict]) -> dict:
    """Lignes dont la citation tombe HORS de la section qui les a produites (discipline de zone).

    `sections` : liste de {id, debut, fin} (en-tête d'un run). Les lignes de rattrapage et
    celles sans position sont ignorées. Contrôle déterministe, sans LLM.
    """
    bornes = {s["id"]: (s["debut"], s["fin"]) for s in sections if isinstance(s, dict)}
    n, dehors, exemples = 0, 0, []
    for l in lignes:
        pos, t = (l.get("_verif") or {}).get("debut"), l.get("_tache")
        if pos is None or t not in bornes or l.get("_rattrapage"):
            continue
        n += 1
        d, f = bornes[t]
        if not d <= pos < f:
            dehors += 1
            exemples.append(l.get("id"))
    return {"n": n, "hors_zone": dehors, "taux": dehors / n if n else None, "exemples": exemples[:10]}
