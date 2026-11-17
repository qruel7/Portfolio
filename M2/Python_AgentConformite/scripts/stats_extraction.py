"""Statistiques d'extraction sur des répétitions, par version de prompt. GRATUIT, aucun appel.

    python scripts/stats_extraction.py "resultats/section-ce42aa5e-*-s-complet-r*.jsonl"

Sans référentiel ni juge : tout est déterministe. Pour chaque version (et configuration) :
nombre de lignes (moyenne ± écart-type), lignes par section, part de lignes hors de leur zone,
précision des références, et reproductibilité J̄ sur les paragraphes couverts.
"""

import argparse
import glob
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import metriques  # noqa: E402


def lire(chemin: Path) -> tuple[dict, list[dict]]:
    enreg = [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]
    return enreg[0], [l for e in enreg if e["type"] == "extraction" for l in e["lignes"]]


def moy(v):
    v = [x for x in v if x is not None]
    if not v:
        return "—"
    return f"{st.fmean(v):.1f}" + (f" ± {st.stdev(v):.1f}" if len(v) > 1 else "")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("runs", nargs="+")
    p.add_argument("--sortie", type=Path, default=Path("resultats/stats_extraction.json"))
    a = p.parse_args()
    fichiers = sorted({f for m in a.runs for f in (glob.glob(m) or [m]) if f.endswith(".jsonl")})
    groupes = {}
    for f in fichiers:
        e, lignes = lire(Path(f))
        if e.get("mode") not in ("section", "unique"):
            continue
        cle = f"{e.get('version_prompt')}:{e.get('mode')}"
        hz = metriques.hors_zone(lignes, e.get("sections", []))
        refs = metriques.precision_references(lignes)
        par_section = {}
        for l in lignes:
            par_section[l.get("_tache")] = par_section.get(l.get("_tache"), 0) + 1
        paragraphes = {(l.get("_verif") or {}).get("paragraphe") for l in lignes
                       if (l.get("_verif") or {}).get("statut") == "valide"} - {None}
        groupes.setdefault(cle, []).append({"fichier": Path(f).name, "lignes": len(lignes), "hors_zone": hz,
                                            "refs": refs, "par_section": par_section, "paragraphes": paragraphes})
    sortie = {}
    for cle, runs in sorted(groupes.items()):
        sections = sorted({s for r in runs for s in r["par_section"]}, key=str)
        j = metriques.jaccard_moyen([r["paragraphes"] for r in runs])
        g = {"k": len(runs), "fichiers": [r["fichier"] for r in runs],
             "lignes": [r["lignes"] for r in runs],
             "taux_hors_zone": [r["hors_zone"]["taux"] for r in runs],
             "exemples_hors_zone": [r["hors_zone"]["exemples"] for r in runs],
             "refs_exactes": [r["refs"]["taux_exacte"] for r in runs],
             "refs_trop_larges": [r["refs"]["trop_large"] for r in runs],
             "jaccard_paragraphes": j["jaccard_moyen"],
             "par_section": {s: [r["par_section"].get(s, 0) for r in runs] for s in sections}}
        sortie[cle] = g
        pct = lambda v: [None if x is None else 100 * x for x in v]
        print(f"\n=== {cle} : k = {len(runs)}")
        print(f"  lignes                 : {moy(g['lignes'])}   {g['lignes']}")
        print(f"  hors zone (%)          : {moy(pct(g['taux_hors_zone']))}")
        print(f"  références exactes (%) : {moy(pct(g['refs_exactes']))}   trop larges : {g['refs_trop_larges']}")
        jtxt = "—" if j["jaccard_moyen"] is None else f"{j['jaccard_moyen']:.3f}"
        print(f"  J̄ paragraphes couverts : {jtxt}")
        print("  lignes par section     : " + "  ".join(f"{s}={'/'.join(map(str, v))}" for s, v in g["par_section"].items()))
    a.sortie.parent.mkdir(parents=True, exist_ok=True)
    a.sortie.write_text(json.dumps(sortie, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
    print(f"\nÉcrit : {a.sortie}")


if __name__ == "__main__":
    main()
