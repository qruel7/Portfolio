"""Chaîne complète orchestrée par LangGraph : Agent 1 → rattrapage → dédoublonnage → Agent 2 → export.

1) Chiffrer (gratuit) :
    python scripts/lancer_pipeline.py data/corpus/ifrs-9-financial-instruments.pdf --nom "IFRS 9 Financial Instruments" \\
        --referentiel data/referentiels/referentiel_IFRS9.xlsx --simulation
2) Lancer (payant) : même commande avec --confirmer à la place de --simulation.
   Sans --confirmer, le script refuse de lancer : une chaîne complète coûte plusieurs dollars.

--etapes agent1,rattrapage,dedoublonnage,agent2,export (toutes par défaut).
Sans --referentiel, la chaîne s'arrête après le dédoublonnage.
En cas de panne, relancer la même commande : les appels déjà payés sont relus sur disque.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import couts, pipeline, traces  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("document")
    p.add_argument("--nom", required=True)
    p.add_argument("--referentiel", default=None)
    p.add_argument("--feuille", default=0)
    p.add_argument("--etapes", default=",".join(pipeline.ETAPES))
    p.add_argument("--effort", choices=["low", "medium", "high"], default="medium")
    p.add_argument("--version", default=None, help="version des prompts de l'Agent 1 (v3 par défaut)")
    p.add_argument("--simulation", action="store_true")
    p.add_argument("--confirmer", action="store_true", help="autorise les appels payants")
    a = p.parse_args()

    etapes = [e.strip() for e in a.etapes.split(",") if e.strip()]
    inconnues = set(etapes) - set(pipeline.ETAPES)
    if inconnues:
        sys.exit(f"Étapes inconnues : {sorted(inconnues)} (possibles : {', '.join(pipeline.ETAPES)})")
    etat = {"document": a.document, "nom": a.nom, "referentiel": a.referentiel,
            "feuille": int(a.feuille) if str(a.feuille).isdigit() else a.feuille, "etapes": etapes, "effort": a.effort,
            "version": a.version}
    if a.version:
        from src import agent1

        manquants = [n for n in ("systeme", "section", "enrichissement", "rattrapage")
                     if not (agent1.DOSSIER_PROMPTS / f"agent1_{n}_{a.version}.txt").exists()]
        if manquants:
            sys.exit(f"Prompts absents pour la version {a.version} : {manquants}")
    est = pipeline.estimer(etat)
    realisables = [e for e in etapes if e not in ("agent2", "export") or a.referentiel]
    print(f"Version des prompts de l'Agent 1 : {a.version or 'défaut'}")
    print(f"Étapes : {' → '.join(realisables)}" + ("" if a.referentiel else "  (pas de référentiel : ni Agent 2 ni export)"))
    print(f"Document : {est['sections']} sections, préfixe ≈ {est['prefixe_estime']:,} tokens, "
          f"≈ {est['lignes_estimees']} lignes attendues".replace(",", " "))
    for e, c in est["detail"].items():
        print(f"  {e:14} ≤ {c:.2f} $")
    print(f"  TOTAL prudent  ≈ {est['total']:.2f} $   (déjà dépensé ce mois : {couts.depense():.2f} $)")
    if a.simulation:
        print("Simulation : rien n'a été appelé. Détail étape par étape : scripts/*.py --simulation.")
        return
    if not a.confirmer:
        sys.exit("Ajouter --confirmer pour lancer la chaîne (appels payants).")

    fin = pipeline.executer(etat)
    print("\nFichiers produits :")
    for cle in ("run_agent1", "consolide", "dedoublonne", "run_agent2", "gap_analysis", "export"):
        if fin.get(cle):
            print(f"  {cle:13} {fin[cle]}")
    journal = Path(fin.get("run_agent1", "resultats/x")).with_name(
        f"pipeline-{Path(fin.get('run_agent1', 'x')).stem}.json")
    journal.write_text(json.dumps({k: v for k, v in fin.items()}, ensure_ascii=False, indent=1, default=str),
                       encoding="utf-8")
    print(f"  journal       {journal}")
    print(json.dumps(couts.bilan(), indent=1, ensure_ascii=False))
    traces.vider()


if __name__ == "__main__":
    main()
