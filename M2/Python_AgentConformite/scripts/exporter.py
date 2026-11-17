"""Exporte un référentiel pivot (consolidé ou dédoublonné) au format d'un référentiel de référence.
GRATUIT, sans LLM. Seule la ligne d'en-tête du fichier de format est lue.

    python scripts/exporter.py resultats/section-xxxx_consolide_dedoublonne.json \\
        --format data/referentiels/referentiel_IFRS9.xlsx
→ resultats/section-xxxx_consolide_dedoublonne_export_<format>.xlsx
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.export import exporter  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("entree", type=Path)
    p.add_argument("--format", required=True, type=Path, help="fichier Excel dont on reprend les colonnes")
    p.add_argument("--feuille", default=0)
    a = p.parse_args()
    lignes = json.loads(a.entree.read_text(encoding="utf-8"))["lignes"]
    feuille = int(a.feuille) if str(a.feuille).isdigit() else a.feuille
    sortie = a.entree.with_name(f"{a.entree.stem}_export_{a.format.stem}.xlsx")
    r = exporter(lignes, a.format, sortie, feuille)
    print(f"{r['nb_lignes']} lignes au format de {r['format']} (échelle de criticité : {r['langue_echelle']})")
    for c, role in r["roles"].items():
        print(f"  {c!r:28} ← {role or '(non reconnu, vide)'}")
    for c in r["colonnes_ajoutees"]:
        print(f"  {c!r:28} ← colonne de traçabilité ajoutée")
    if r["anomalies"]:
        print(f"Anomalies : {len(r['anomalies'])} (ex. {r['anomalies'][0]})")
    print(f"Écrit : {r['fichier']}")


if __name__ == "__main__":
    main()
