"""Comptabilité des appels API : calcul du coût, journal append-only, garde-fou budgétaire.

Le journal logs/couts.jsonl est la SOURCE DE VÉRITÉ comptable du projet.
On n'y fait que des ajouts : une ligne JSON par appel facturé, jamais de modification.
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from src import config

CHAMPS_USAGE = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)


class BudgetDepasse(RuntimeError):
    """Levée quand un appel ou un lot ferait dépasser le seuil budgétaire."""


def _lire_usage(usage) -> dict:
    """Accepte un dict ou l'objet `usage` du SDK ; les champs absents ou None valent 0."""
    valeurs = {}
    for champ in CHAMPS_USAGE:
        v = usage.get(champ) if isinstance(usage, dict) else getattr(usage, champ, None)
        valeurs[champ] = int(v or 0)
    return valeurs


def cout(modele: str, usage, batch: bool = False, ttl: str = "5m") -> float:
    """Coût en USD d'un appel, à partir de son objet `usage`.

    coût = (entrée × tarif_entrée + écriture_cache × tarif_écriture
            + lecture_cache × tarif_lecture + sortie × tarif_sortie) / 1 000 000
    puis × 0,5 en batch.
    """
    config.verifier_modele(modele)
    if ttl not in ("5m", "1h"):
        raise ValueError(f"TTL inconnu : {ttl}")
    t = config.TARIFS[modele]
    u = _lire_usage(usage)
    tarif_ecriture = (
        t["ecriture_cache"] if ttl == "5m" else t["entree"] * config.MULTIPLICATEUR_ECRITURE_1H
    )
    total = (
        u["input_tokens"] * t["entree"]
        + u["cache_creation_input_tokens"] * tarif_ecriture
        + u["cache_read_input_tokens"] * t["lecture_cache"]
        + u["output_tokens"] * t["sortie"]
    ) / 1_000_000
    if batch:
        total *= config.REMISE_BATCH
    return total


def journaliser(
    modele: str,
    usage,
    etiquette: str,
    batch: bool = False,
    ttl: str = "5m",
    meta: dict | None = None,
    chemin: Path | None = None,
) -> dict:
    """Ajoute une ligne au journal et la renvoie. `meta` : version du prompt, custom_id, effort…"""
    chemin = Path(chemin or config.JOURNAL_COUTS)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    ligne = {
        "horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modele": modele,
        "etiquette": etiquette,
        "batch": batch,
        "ttl": ttl,
        "usage": _lire_usage(usage),
        "cout_usd": round(cout(modele, usage, batch=batch, ttl=ttl), 6),
        "meta": meta or {},
    }
    with chemin.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    return ligne


def lire_journal(chemin: Path | None = None) -> list[dict]:
    chemin = Path(chemin or config.JOURNAL_COUTS)
    if not chemin.exists():
        return []
    with chemin.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _mois_courant() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def depense(mois: str | None = None, chemin: Path | None = None) -> float:
    """Total dépensé sur un mois (format AAAA-MM, mois courant UTC par défaut)."""
    mois = mois or _mois_courant()
    return sum(l["cout_usd"] for l in lire_journal(chemin) if l["horodatage"].startswith(mois))


def verifier_budget(
    estimation_usd: float = 0.0,
    budget: float | None = None,
    seuil: float | None = None,
    chemin: Path | None = None,
) -> float:
    """À appeler AVANT chaque lot ou appel coûteux. Lève BudgetDepasse si
    dépense du mois + estimation > budget × seuil. Renvoie la marge restante en USD."""
    budget = config.BUDGET_MENSUEL_USD if budget is None else budget
    seuil = config.SEUIL_BUDGET if seuil is None else seuil
    plafond = budget * seuil
    deja = depense(chemin=chemin)
    if deja + estimation_usd > plafond:
        raise BudgetDepasse(
            f"Refusé : {deja:.2f} $ déjà dépensés + {estimation_usd:.2f} $ estimés "
            f"> plafond {plafond:.2f} $ ({seuil:.0%} de {budget:.0f} $)."
        )
    return plafond - deja - estimation_usd


def bilan(mois: str | None = None, chemin: Path | None = None) -> dict:
    """Rituel du vendredi : total, répartition par étiquette, taux de succès du cache."""
    mois = mois or _mois_courant()
    lignes = [l for l in lire_journal(chemin) if l["horodatage"].startswith(mois)]
    par_etiquette = defaultdict(float)
    ecrit = lu = 0
    for l in lignes:
        par_etiquette[l["etiquette"]] += l["cout_usd"]
        ecrit += l["usage"]["cache_creation_input_tokens"]
        lu += l["usage"]["cache_read_input_tokens"]
    return {
        "mois": mois,
        "nb_appels": len(lignes),
        "total_usd": round(sum(par_etiquette.values()), 4),
        "par_etiquette": {k: round(v, 4) for k, v in sorted(par_etiquette.items())},
        "tokens_cache_ecrits": ecrit,
        "tokens_cache_lus": lu,
        # cache_read / cache_creation : > 1 dès que chaque écriture est relue plus d'une fois
        "ratio_lecture_ecriture": round(lu / ecrit, 2) if ecrit else None,
    }


if __name__ == "__main__":
    # python -m src.couts  → affiche le bilan du mois
    print(json.dumps(bilan(), indent=2, ensure_ascii=False))
