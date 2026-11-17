"""Relit un run de l'Agent 2, recalcule les métriques et écrit la gap analysis Excel. GRATUIT.

    python scripts/reanalyser_agent2.py resultats/agent2-xxxx.jsonl \\
        --ia resultats/section-xxxx_consolide.json --referentiel data/referentiels/referentiel_IFRS9.xlsx
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.lancer_agent2 import charger_ia  # noqa: E402
from src import agent2  # noqa: E402
from src.rapport_agent2 import ecrire_gap_analysis  # noqa: E402
from src.referentiels import charger_referentiel  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run", type=Path)
    p.add_argument("--ia", required=True, type=Path)
    p.add_argument("--referentiel", required=True, type=Path)
    p.add_argument("--feuille", default=0)
    a = p.parse_args()

    feuille = int(a.feuille) if str(a.feuille).isdigit() else a.feuille
    ref = charger_referentiel(a.referentiel, feuille)
    entete = json.loads(a.run.read_text(encoding="utf-8").splitlines()[0])
    if entete.get("sha256_referentiel") != ref["sha256"]:
        sys.exit("Ce n'est pas le référentiel utilisé par ce run (empreintes différentes).")
    lignes_ia, _ = charger_ia(a.ia)
    res = agent2.reanalyser(a.run, lignes_ia, ref)
    sortie = a.run.with_name(a.run.stem + "_reanalyse.json")
    sortie.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    xlsx = ecrire_gap_analysis(res, ref, lignes_ia, a.run.with_name(a.run.stem + "_gap_analysis.xlsx"))
    m = res["metriques"]
    pct = lambda x: "—" if x is None else f"{100 * x:.1f} %"
    for e in res["evaluations"]:
        print(f"  {e['id_ref']:6} {e['couverture']:15} score={'' if e['score'] is None else round(e['score'], 2)}")
    print(f"\nÉvaluées {m['nb_evaluees']} | hors périmètre {m['nb_hors_perimetre']} | non évaluées {m['nb_non_evaluees']}")
    print(f"Couverture stricte {pct(m['couverture_stricte'])} | large {pct(m['couverture_large'])} | "
          f"qualité moyenne {pct(m['qualite_moyenne'])}")
    print(f"Supplémentaires : {m['pertinence_supplementaires']}")
    print(f"Écrit : {sortie}\n        {xlsx}")


if __name__ == "__main__":
    main()
