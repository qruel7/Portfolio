"""Paragraphes du texte qui n'ont reçu AUCUNE ligne lors d'un run. GRATUIT (aucun appel).

Diagnostic de l'exhaustivité de l'extraction, sans référentiel : pour chaque
section traitée, liste les paragraphes numérotés sans ligne, avec le nombre de
tournures prescriptives qu'ils contiennent. Un paragraphe omis qui contient
« shall » ou « doit » est un oubli probable ; sans tournure prescriptive, c'est
souvent un passage descriptif (ou une option, un critère : voir le prompt v3).

    python scripts/couverture_paragraphes.py resultats/section-xxxx.jsonl data/corpus/ifrs-9-financial-instruments.pdf --mini
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import agent1  # noqa: E402
from src.couverture import paragraphes_omis  # noqa: E402
from src.decoupage import decouper  # noqa: E402
from src.extraction import charger_document, empreinte  # noqa: E402

def main():
    p = argparse.ArgumentParser()
    p.add_argument("resultats")
    p.add_argument("document")
    p.add_argument("--mini", action="store_true")
    a = p.parse_args()

    enreg = [json.loads(l) for l in Path(a.resultats).read_text(encoding="utf-8").splitlines() if l.strip()]
    entete = enreg[0]
    texte = charger_document(Path(a.document))["texte"]
    dec = entete.get("params_decoupage") or {"min_tokens": 4_000, "max_tokens": 12_000}
    sections = decouper(texte, **dec)
    if a.mini:
        texte, sections = agent1.mini_document(texte, sections, entete["taches"])
    if empreinte(texte) != entete["sha256_texte"]:
        sys.exit("Le texte reconstruit ne correspond pas à celui du run (empreintes différentes).")

    lignes_par_tache = {}
    for e in enreg[1:]:
        if e["type"] in ("extraction", "tache"):
            lignes_par_tache.setdefault(e["tache"], []).extend(e["lignes"])
    omis = paragraphes_omis(texte, sections, lignes_par_tache)

    total, alertes = 0, 0
    for s in sections:
        if s.id not in lignes_par_tache:
            continue
        o = [x for x in omis if x["section"] == s.id]
        n = next((x["nb_paragraphes_section"] for x in o), None)
        if n is None:  # aucun omis : on recompte pour l'affichage
            n = len({l["ref"] for l in lignes_par_tache[s.id]})
        total += n
        alertes += sum(1 for x in o if x["prescriptif"])
        print(f"{s.id}: {n - len(o)}/{n} paragraphes avec au moins une ligne")
        for x in o:
            debut = re.sub(r"\s+", " ", texte[x["debut"]:x["debut"] + 90])
            alerte = "  <-- OUBLI PROBABLE" if x["prescriptif"] else ""
            print(f"   omis {x['paragraphe']:10} prescriptif={x['prescriptif']} facultatif={x['facultatif']} | {debut}{alerte}")
    print(f"\nParagraphes omis contenant une tournure prescriptive : {alertes} (sur environ {total})")


if __name__ == "__main__":
    main()
