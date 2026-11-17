"""Agrégation de répétitions : essoufflement moyen et reproductibilité (Jaccard). GRATUIT.

    python scripts/repetitions.py resultats/unique-5b820c13-*.jsonl resultats/unique-18ed0200-*.jsonl ... \\
        --reference resultats/section-5b820c13-v3-20261022T181226_consolide.json \\
        --document data/corpus/ifrs-9-financial-instruments.pdf

Les runs sont regroupés par configuration (mode + sections traitées). Pour chacune :
- rappel global contre R* (strict et large) : moyenne, écart-type, min, max ;
- pente de chaque répétition, puis moyenne des pentes et test de Student de « pente = 0 »
  sur les k pentes : c'est la répétition, pas la ligne, qui est l'unité indépendante ;
- r(c) moyen par section (pour le graphique) ;
- reproductibilité : Jaccard moyen sur les paires, pour deux identités d'obligation
  déterministes : lignes de R* retrouvées (strict) et paragraphes couverts.
Comparaison « même contenu, position différente » : pour chaque configuration sur
mini-document, on recalcule le rappel des runs sur document complet restreint aux mêmes
lignes de R*, puis on compare les deux séries de rappels par un test de Welch (les
répétitions sont les observations indépendantes).
"""

import argparse
import glob
import json
import math
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.essoufflement import evaluer  # noqa: E402
from src import metriques  # noqa: E402
from src.extraction import charger_document  # noqa: E402


def resume(valeurs: list[float]) -> dict:
    v = [x for x in valeurs if x is not None]
    if not v:
        return {"k": 0}
    return {"k": len(v), "moyenne": st.fmean(v), "ecart_type": st.stdev(v) if len(v) > 1 else None,
            "min": min(v), "max": max(v)}


def test_moyenne_nulle(valeurs: list[float]) -> dict:
    """t de Student de H0 : moyenne = 0, sur k valeurs indépendantes (les pentes des répétitions)."""
    k = len(valeurs)
    if k < 2:
        return {"k": k, "moyenne": valeurs[0] if valeurs else None}
    m, s = st.fmean(valeurs), st.stdev(valeurs)
    if s == 0:
        return {"k": k, "moyenne": m, "t": math.inf, "p_valeur": 0.0}
    t = m / (s / math.sqrt(k))
    q = metriques._quantile_t(0.975, k - 1)
    return {"k": k, "moyenne": m, "t": t, "p_valeur": metriques._p_bilaterale_t(t, k - 1),
            "ic95": (m - q * s / math.sqrt(k), m + q * s / math.sqrt(k))}


def welch(a: list[float], b: list[float]) -> dict:
    if len(a) < 2 or len(b) < 2:
        return {}
    ma, mb, va, vb = st.fmean(a), st.fmean(b), st.variance(a), st.variance(b)
    se = math.sqrt(va / len(a) + vb / len(b))
    if se == 0:
        return {"difference": ma - mb, "p_valeur": 0.0 if ma != mb else 1.0}
    t = (ma - mb) / se
    ddl = (va / len(a) + vb / len(b)) ** 2 / ((va / len(a)) ** 2 / (len(a) - 1) + (vb / len(b)) ** 2 / (len(b) - 1))
    return {"difference": ma - mb, "t": t, "ddl": ddl, "p_valeur": metriques._p_bilaterale_t(t, max(1, round(ddl)))}


def pct(x):
    return "  —  " if x is None else f"{100 * x:5.1f}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("runs", nargs="+", help="fichiers de runs .jsonl (motifs glob acceptés)")
    p.add_argument("--reference", required=True, type=Path)
    p.add_argument("--document", required=True, type=Path)
    p.add_argument("--sortie", type=Path, default=Path("resultats/repetitions.json"))
    a = p.parse_args()

    fichiers = sorted({f for motif in a.runs for f in (glob.glob(motif) or [motif])
                       if f.endswith(".jsonl") and "_reanalyse" not in f})
    doc = charger_document(a.document)
    groupes: dict[str, list[dict]] = {}
    for f in fichiers:
        res = evaluer(Path(f), a.reference, doc, verbeux=False)
        cle = f"{res['config']['mode']}:{res['config']['sections']}"
        groupes.setdefault(cle, []).append(res)

    sortie = {}
    for cle, runs in groupes.items():
        g = {"k": len(runs), "runs": [r["run"] for r in runs]}
        for regle in ("stricte", "large"):
            g[f"rappel_{regle}"] = resume([r[f"rappel_{regle}"] for r in runs])
            g[f"pente_lignes_{regle}"] = test_moyenne_nulle(
                [r["regressions"][f"lignes_{regle}"]["pente"] for r in runs])
            g[f"pente_sections_{regle}"] = test_moyenne_nulle(
                [r["regressions"][f"sections_{regle}"]["pente"] for r in runs])
        g["r_c_moyen"] = [{"section": s["section"], "n_ref": s["n_ref"],
                           "r_large": resume([r["par_section"][j]["r_large"] for r in runs]),
                           "r_stricte": resume([r["par_section"][j]["r_stricte"] for r in runs])}
                          for j, s in enumerate(runs[0]["par_section"])]
        g["jaccard_lignes_R*"] = metriques.jaccard_moyen(
            [{x["id"] for x in r["detail"] if x["stricte"]} for r in runs])
        g["jaccard_paragraphes"] = metriques.jaccard_moyen([set(r["paragraphes_couverts"]) for r in runs])
        g["nb_lignes"] = resume([r["n_run"] for r in runs])
        g["sortie_tokens"] = resume([r["sortie_tokens"] for r in runs])
        g["reflexion_tokens"] = resume([r["reflexion_tokens"] for r in runs])
        g["_rappels_large"] = [r["rappel_large"] for r in runs]
        sortie[cle] = g

        print(f"\n=== {cle} : k = {len(runs)} répétition(s)")
        for regle in ("stricte", "large"):
            rr = g[f"rappel_{regle}"]
            et = "" if rr.get("ecart_type") is None else f" ± {100 * rr['ecart_type']:.1f}"
            print(f"  rappel {regle:7} : {pct(rr['moyenne'])} %{et}  [min {pct(rr['min'])} ; max {pct(rr['max'])}]")
        for regle in ("stricte", "large"):
            t = g[f"pente_lignes_{regle}"]
            if t.get("p_valeur") is None:
                print(f"  pente (lignes) {regle:7} : {t.get('moyenne', float('nan')):+.3f} (une seule répétition)")
            else:
                lo, hi = t.get("ic95", (float("nan"), float("nan")))
                print(f"  pente (lignes) {regle:7} : moyenne {t['moyenne']:+.3f}  IC95 [{lo:+.3f} ; {hi:+.3f}]  "
                      f"p = {t['p_valeur']:.3g} (k = {t['k']})")
        print(f"  Jaccard moyen : lignes de R* retrouvées {g['jaccard_lignes_R*']['jaccard_moyen'] or float('nan'):.3f} | "
              f"paragraphes couverts {g['jaccard_paragraphes']['jaccard_moyen'] or float('nan'):.3f}")
        print(f"  lignes par run : {g['nb_lignes']['moyenne']:.0f} [min {g['nb_lignes']['min']} ; max {g['nb_lignes']['max']}] | "
              f"réflexion : {g['reflexion_tokens']['moyenne']:.0f} tokens en moyenne "
              f"[min {g['reflexion_tokens']['min']} ; max {g['reflexion_tokens']['max']}]")
        print("  r(c) moyen (large) : " + " ".join(
            f"{x['section']}={pct(x['r_large'].get('moyenne')).strip()}" for x in g["r_c_moyen"]))

    complets = [r for cle, rs in groupes.items() if cle.endswith(":complet") for r in rs]
    if complets:
        print("\n=== Même contenu, position différente (document complet vs mini-document seul)")
        comparaisons = {}
        for cle, runs in groupes.items():
            if cle.endswith(":complet"):
                continue
            ids_ref = {x["id"] for x in runs[0]["detail"]}
            ligne = {}
            for regle in ("stricte", "large"):
                dans_complet = [sum(x[regle] for x in r["detail"] if x["id"] in ids_ref) / len(ids_ref) for r in complets]
                seul = [r[f"rappel_{regle}"] for r in runs]
                w = welch(seul, dans_complet)
                ligne[regle] = {"seul": resume(seul), "dans_le_complet": resume(dans_complet), "welch": w}
                pw = f"p = {w['p_valeur']:.3g}" if w.get("p_valeur") is not None else "test impossible (k < 2)"
                print(f"  {cle:22} {regle:7} : seul {pct(st.fmean(seul))} % vs dans le complet "
                      f"{pct(st.fmean(dans_complet))} %  (écart {100 * (st.fmean(seul) - st.fmean(dans_complet)):+.1f} pts, {pw})")
            comparaisons[cle] = ligne
        sortie["_comparaisons"] = comparaisons

    a.sortie.parent.mkdir(parents=True, exist_ok=True)
    a.sortie.write_text(json.dumps(sortie, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
    print(f"\nÉcrit : {a.sortie}")


if __name__ == "__main__":
    main()
