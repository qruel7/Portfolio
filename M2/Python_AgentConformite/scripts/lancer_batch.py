"""Répétitions de l'Agent 1 (extraction seule) en BATCH : soumission, suivi, récupération.

1) Chiffrer (gratuit) :
    python scripts/lancer_batch.py data/corpus/ifrs-9-financial-instruments.pdf --nom "IFRS 9 Financial Instruments" \\
        --plan unique:complet:5 --plan unique:S11-S27:5 --plan unique:S01-S10:5 --max-tokens 128000 --simulation
2) Soumettre : même commande sans --simulation → écrit resultats/batch-<id>.json (manifeste)
3) Suivre :     python scripts/lancer_batch.py <document> --nom "..." --etat resultats/batch-<id>.json
4) Récupérer :  python scripts/lancer_batch.py <document> --nom "..." --recuperer resultats/batch-<id>.json
   → un fichier de run par répétition, au format des runs synchrones (relançable sans repayer :
     les coûts ne sont journalisés qu'une fois par custom_id).

--plan MODE:SECTIONS:K   MODE = unique | section ; SECTIONS = complet | S11-S27 | S01,S04 ; K répétitions.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import agent1, batch, config, couts  # noqa: E402
from src.decoupage import decouper  # noqa: E402
from src.extraction import charger_document  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("document", type=Path)
    p.add_argument("--nom", required=True)
    p.add_argument("--langue", default=None)
    p.add_argument("--plan", action="append", default=[], help="MODE:SECTIONS:K (répétable)")
    p.add_argument("--max-tokens", type=int, default=agent1.MAX_TOKENS_DEFAUT)
    p.add_argument("--effort", choices=["low", "medium", "high"], default=agent1.EFFORT_DEFAUT)
    p.add_argument("--version", default=agent1.VERSION_PROMPT, help="version des prompts de l'Agent 1")
    p.add_argument("--modele", default=None)
    p.add_argument("--ttl", choices=["5m", "1h"], default="5m",
                   help="1h seulement si chaque préfixe sert ≥ 20 requêtes (vérifié)")
    p.add_argument("--amorcer", action="store_true",
                   help="un appel synchrone minimal par document juste avant la soumission (cache prêt)")
    p.add_argument("--simulation", action="store_true")
    p.add_argument("--etat", type=Path, help="manifeste d'un lot soumis")
    p.add_argument("--recuperer", type=Path, help="manifeste d'un lot terminé")
    a = p.parse_args()

    doc = charger_document(a.document)
    texte = doc["texte"]
    params_dec = {"min_tokens": config.DECOUPAGE_MIN_TOKENS, "max_tokens": config.DECOUPAGE_MAX_TOKENS}
    sections = decouper(texte, **params_dec)

    if a.etat:
        man = json.loads(a.etat.read_text(encoding="utf-8"))
        lot = batch.etat(man["batch_id"])
        print(f"Lot {lot.id} : {lot.processing_status} | {batch._compteurs(lot)}")
        return
    if a.recuperer:
        bilan = batch.recuperer(a.recuperer, texte, sections)
        if not bilan["termine"]:
            print(f"Pas encore terminé : {bilan['etat']} | {bilan['compteurs']}")
            return
        for r in bilan["runs"]:
            print(f"  {r['cle']:28} {r['nb_lignes']:4} lignes, {r['valides']:4} citations valides → {r['fichier']}")
        if bilan["erreurs"]:
            print(f"Requêtes en échec : {bilan['erreurs']}")
        print(json.dumps(couts.bilan(), indent=1, ensure_ascii=False))
        return

    if not a.plan:
        sys.exit("Indiquer au moins un --plan MODE:SECTIONS:K")
    plan = []
    for item in a.plan:
        mode, plage, k = item.split(":")
        plan.append({"mode": mode, "ids": batch.plage(sections, plage), "k": int(k)})
    requetes, runs = batch.construire(texte=texte, sections=sections, plan=plan, nom_document=a.nom,
                                      langue=a.langue, modele=a.modele, effort=a.effort,
                                      max_tokens=a.max_tokens, params_decoupage=params_dec, ttl=a.ttl,
                                      version=a.version)
    est = batch.estimation(requetes, ttl=a.ttl)
    modeles = {r["params"]["model"] for r in requetes}
    print(f"Modèle {', '.join(modeles)} | prompts {a.version} | effort {a.effort} | max_tokens {a.max_tokens} | TTL {a.ttl}")
    for item, cfg in zip(a.plan, plan):
        n = sum(1 for r in runs if r["mode"] == cfg["mode"] and r["ids"] == cfg["ids"])
        print(f"  {item:28} → {n} run(s)")
    print(f"Requêtes : {est['nb_requetes']}")
    print(f"  écriture des préfixes (batch, sans aucune lecture de cache) ≈ {est['ecriture_usd_batch']:.2f} $")
    print(f"  BORNE HAUTE (batch, chaque sortie au plafond)               ≈ {est['max_usd_batch']:.2f} $")
    print(f"Déjà dépensé ce mois : {couts.depense():.2f} $ sur {config.BUDGET_MENSUEL_USD:.0f} $")
    if a.simulation:
        return
    if a.amorcer:
        for x in batch.amorcer(requetes):
            print(f"  amorçage ({x['custom_id_exemple']}) : {x['cache_ecrit']} tokens écrits, "
                  f"{x['cache_lu']} lus, TTL {x['ttl']}")
    manifeste = batch.soumettre(requetes, runs, est["max_usd_batch"])
    print(f"Lot soumis. Manifeste : {manifeste}")
    print("Suivre avec --etat, puis récupérer avec --recuperer (même document et même --nom).")


if __name__ == "__main__":
    main()
