"""Envoie à LangSmith les appels du journal qui n'y sont pas encore. GRATUIT (aucun appel Anthropic).

Sert à rattraper les appels faits avant l'activation de LangSmith, ou un run où
le traçage a échoué : LangSmith et logs/couts.jsonl affichent alors le même total.
Les identifiants déjà envoyés sont notés dans logs/langsmith_envoyes.txt :
relancer le script n'envoie jamais deux fois le même appel.

    python scripts/traces_depuis_journal.py
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, couts, traces  # noqa: E402

DEJA = config.DOSSIER_LOGS / "langsmith_envoyes.txt"


def main():
    if not traces.actif():
        sys.exit("LangSmith inactif : LANGSMITH_TRACING=true et LANGSMITH_API_KEY requis dans .env")
    deja = set(DEJA.read_text(encoding="utf-8").split()) if DEJA.exists() else set()
    envoyes, total = 0, 0.0
    for l in couts.lire_journal():
        cle = l["meta"].get("id_reponse") or f"{l['horodatage']}-{l['etiquette']}"
        if cle in deja:
            continue
        instant = datetime.fromisoformat(l["horodatage"])
        duree = l["meta"].get("duree_s")
        debut = instant if duree is None else instant.fromtimestamp(instant.timestamp() - duree, instant.tzinfo)
        ok = traces.tracer(modele=l["modele"], etiquette=l["etiquette"], usage=l["usage"], debut=debut,
                           fin=instant, meta={**l["meta"], "rejoue_depuis_journal": True},
                           stop_reason=l["meta"].get("stop_reason"), batch=l["batch"], ttl=l["ttl"])
        if ok:
            deja.add(cle)
            envoyes += 1
            total += l["cout_usd"]
    traces.vider()
    DEJA.parent.mkdir(parents=True, exist_ok=True)
    DEJA.write_text("\n".join(sorted(deja)) + "\n", encoding="utf-8")
    print(f"{envoyes} appel(s) envoyé(s) à LangSmith, pour {total:.4f} $.")
    print(f"Total du journal ce mois : {couts.depense():.4f} $ — il doit correspondre à LangSmith.")


if __name__ == "__main__":
    main()
