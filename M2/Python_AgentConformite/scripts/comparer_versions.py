"""Compare des versions de l'Agent 1 sur un même texte (v3, v4a, v4…). GRATUIT, aucun appel.

    python scripts/comparer_versions.py \\
        --version v3  resultats/section-xxxx_consolide_dedoublonne.json resultats/agent2-aaaa.jsonl \\
        --version v4a resultats/section-yyyy_consolide_dedoublonne.json resultats/agent2-bbbb.jsonl

Pour chaque version : nombre de lignes, citations valides et hallucination factuelle, précision
des références (contrôle déterministe), lignes jugées peu ou non pertinentes par l'Agent 2,
couverture stricte et large, qualité, et coût réel (journal, par identifiant de run).
Le run d'Agent 2 est facultatif (mettre « - »).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import couts, metriques, tableau  # noqa: E402


def cout_runs(ids: set[str]) -> float:
    return sum(l["cout_usd"] for l in couts.lire_journal() if (l.get("meta") or {}).get("id_run") in ids)


def ligne_version(nom: str, chemin_ia: Path, chemin_a2: Path | None) -> dict:
    meta, lignes = tableau.lignes_referentiel(chemin_ia)
    statuts = tableau.statuts_citations(lignes)
    n = len(lignes)
    refs = metriques.precision_references(lignes)
    ids = {x for x in (meta.get("run"), meta.get("rattrapage"), meta.get("id_run")) if x}
    r = {"version": nom, "lignes": n,
         "citations_valides": statuts.get("valide", 0) / n if n else None,
         "hallucination": (statuts.get("introuvable", 0) + statuts.get("ref_incoherente", 0)) / n if n else None,
         "refs_exactes": refs["taux_exacte"], "refs_trop_larges": refs["trop_large"],
         "cout_agent1": cout_runs(ids)}
    if chemin_a2:
        ev = tableau.evaluation_agent2(chemin_a2) or {}
        m = ev.get("metriques") or {}
        pert = m.get("pertinence_supplementaires") or {}
        r |= {"couverture_stricte": m.get("couverture_stricte"), "couverture_large": m.get("couverture_large"),
              "qualite": m.get("qualite_moyenne"), "supp_pertinentes": pert.get("pertinente"),
              "supp_faibles": pert.get("faible"), "supp_non_pertinentes": pert.get("non_pertinente"),
              "cout_agent2": cout_runs({(ev.get("entete") or {}).get("id_run")})}
    return r


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--version", nargs=3, action="append", metavar=("NOM", "REFERENTIEL_IA", "RUN_AGENT2"),
                   required=True)
    p.add_argument("--sortie", type=Path, default=Path("resultats/comparaison_versions.json"))
    a = p.parse_args()
    lignes = [ligne_version(n, Path(ia), None if a2 == "-" else Path(a2)) for n, ia, a2 in a.version]
    cles = [k for k in lignes[0] if k != "version"]
    fmt = lambda v: "—" if v is None else (f"{100 * v:.1f} %" if isinstance(v, float) and v <= 1 and v >= 0
                                           and not isinstance(v, bool) else str(v))
    print(f"{'':24}" + "".join(f"{l['version']:>14}" for l in lignes))
    for k in cles:
        vals = []
        for l in lignes:
            v = l.get(k)
            vals.append(f"{v:.2f} $" if k.startswith("cout") and v is not None else fmt(v))
        print(f"{k:24}" + "".join(f"{x:>14}" for x in vals))
    a.sortie.write_text(json.dumps(lignes, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nÉcrit : {a.sortie}")


if __name__ == "__main__":
    main()
