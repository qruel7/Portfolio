"""Passe de rattrapage après un run : la RÈGLE décide quels paragraphes revoir, le LLM extrait.

1. Relit un run (fichier de resultats/), reconstruit le texte et vérifie son empreinte.
2. Repère, sans LLM, les paragraphes à tournure prescriptive restés sans ligne (src/couverture.py).
3. Relance une extraction ciblée sur ces seuls paragraphes, section par section, avec
   EXACTEMENT le même préfixe (consignes + document), puis enrichit les lignes trouvées.
4. Écrit le run de rattrapage (resultats/rattrapage-…jsonl) et un référentiel consolidé
   <run>_consolide.json : lignes du run + lignes de rattrapage (marquées "_rattrapage": true).
Le run d'origine n'est jamais modifié : on peut mesurer le rappel AVANT et APRÈS rattrapage.

    python scripts/rattraper.py resultats/section-xxxx.jsonl data/corpus/ifrs-9-financial-instruments.pdf --simulation
    python scripts/rattraper.py resultats/section-xxxx.jsonl data/corpus/ifrs-9-financial-instruments.pdf
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import couts, rattrapage, traces  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("resultats", help="fichier du run d'origine (pas un _reanalyse)")
    p.add_argument("document")
    p.add_argument("--mini", action="store_true", help="le run portait sur un mini-document")
    p.add_argument("--seuil", type=int, default=1, help="nb minimal de tournures prescriptives")
    p.add_argument("--simulation", action="store_true")
    a = p.parse_args()

    try:
        prep = rattrapage.preparer(Path(a.resultats), Path(a.document), seuil=a.seuil, mini=a.mini)
    except rattrapage.RattrapageImpossible as e:
        sys.exit(str(e))
    omis = prep["omis"]
    par_section = {}
    for o in omis:
        par_section.setdefault(o["section"], []).append(o)
    print(f"Source : {prep['source'].name}")
    print(f"{len(omis)} paragraphe(s) à revoir dans {len(par_section)} section(s) :")
    for sid, os_ in par_section.items():
        print(f"  {sid}: {', '.join(o['paragraphe'] for o in os_)}")

    if a.simulation:
        e = rattrapage.estimer(prep)
        prefixe = f"{e['prefixe']:,}".replace(",", " ")
        print(f"\nSimulation : {e['appels']} appels, préfixe ≈ {prefixe} tokens")
        print(f"  écriture {e['ecriture']:.3f} $ + relectures {e['lectures']:.3f} $ + sortie {e['sortie']:.3f} $ "
              f"≈ {e['total']:.2f} $ (si le cache du run est expiré, ce qui est probable)")
        return

    res = rattrapage.executer(prep)
    print(f"\n{res['nb_nouvelles']} ligne(s) ajoutée(s) pour {res['nb_omis']} paragraphe(s) revu(s).")
    print(f"Référentiel consolidé : {res['consolide']} ({len(prep['finales']) + res['nb_nouvelles']} lignes)")
    print(json.dumps(couts.bilan(), indent=1, ensure_ascii=False))
    traces.vider()


if __name__ == "__main__":
    main()
