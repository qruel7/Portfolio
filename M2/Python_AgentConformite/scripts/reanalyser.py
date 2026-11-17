"""Relit un fichier de résultats SANS rappeler l'API (gratuit).

Ré-analyse chaque réponse brute avec la version actuelle de schema.py et
verif_citations.py, et écrit <fichier>_reanalyse.jsonl à côté. Utile quand le
code d'analyse s'améliore après un run déjà payé.

    python scripts/reanalyser.py resultats/section-xxxx.jsonl data/corpus/ifrs-9-financial-instruments.pdf --mini
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import agent1  # noqa: E402
from src.decoupage import decouper  # noqa: E402
from src.extraction import charger_document, empreinte  # noqa: E402
from src.schema import Ligne, LigneExtraite, analyser_sortie  # noqa: E402
from src.verif_citations import IndexTexte, verifier_ligne  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("resultats")
    p.add_argument("document")
    p.add_argument("--mini", action="store_true", help="le run portait sur un mini-document")
    a = p.parse_args()

    enreg = [json.loads(l) for l in Path(a.resultats).read_text(encoding="utf-8").splitlines() if l.strip()]
    entete = enreg[0]
    texte = charger_document(Path(a.document))["texte"]
    if a.mini:
        dec = entete.get("params_decoupage") or {"min_tokens": 4_000, "max_tokens": 12_000}  # v1 : anciens défauts
        texte, _ = agent1.mini_document(texte, decouper(texte, **dec), entete["taches"])
    if empreinte(texte) != entete["sha256_texte"]:
        sys.exit("Le texte reconstruit ne correspond pas à celui du run (empreintes différentes).")
    index = IndexTexte(texte)

    sortie = Path(a.resultats).with_name(Path(a.resultats).stem + "_reanalyse.jsonl")
    v1 = entete.get("schema") == "pivot-v1"
    with sortie.open("w", encoding="utf-8") as f:
        f.write(json.dumps(entete, ensure_ascii=False) + "\n")
        for t in enreg[1:]:
            if t["type"] not in ("tache", "extraction"):  # enrichissements et synthèse recopiés tels quels
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
                continue
            lignes, rejets = analyser_sortie(t["reponse_brute"], Ligne if v1 else LigneExtraite)
            for l in lignes:
                l["_verif"] = verifier_ligne(index, l)
                l["_tache"] = t["tache"]
            t = {**t, "lignes": lignes, "rejets": rejets, "nb_lignes": len(lignes)}
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
            statuts = Counter(l["_verif"]["statut"] for l in lignes)
            u = t["usage"]
            reflexion = (u.get("output_tokens_details") or {}).get("thinking_tokens")
            print(f"{t['tache']}: {len(lignes)} lignes {dict(statuts)} | stop={t['stop_reason']} | "
                  f"sortie {u['output_tokens']} tokens dont réflexion {reflexion}")
    print(f"Écrit : {sortie}")


if __name__ == "__main__":
    main()
