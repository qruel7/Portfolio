"""Traces LangSmith : observabilité des appels, SANS contenu confidentiel.

Choix de conception (22/10) :
- on n'utilise PAS l'enveloppe `langsmith.wrappers.wrap_anthropic` :
  1. elle ne trace le streaming que si l'on lit `text_stream` ou si l'on itère
     sur le flux ; notre appel à `get_final_message()` ne serait pas tracé ;
  2. elle enverrait à LangSmith (service tiers) le prompt complet, donc le texte
     de la norme, et plus tard les référentiels Deloitte, qui ne doivent pas
     être déposés dans une interface tierce ;
- on crée donc chaque trace à la main (RunTree) avec seulement des MÉTADONNÉES :
  modèle, étiquette, tâche, version du prompt, usage, motif d'arrêt, durée ;
- le coût est fourni EXPLICITEMENT (input_cost, output_cost, total_cost),
  calculé avec les mêmes tarifs que le journal : LangSmith affiche donc
  exactement le même montant que logs/couts.jsonl, même s'il ne connaît pas
  le modèle. Le journal reste la source de vérité comptable.

Le traçage ne doit jamais bloquer ni faire échouer un run : toute erreur
est convertie en avertissement.
"""

import os
import warnings
from datetime import datetime, timezone

from src import config
from src.couts import _lire_usage

_CLIENT = None


def actif() -> bool:
    return os.getenv("LANGSMITH_TRACING", "").lower() == "true" and bool(os.getenv("LANGSMITH_API_KEY"))


def usage_metadata(modele: str, usage, batch: bool = False, ttl: str = "5m") -> dict:
    """Usage au format LangSmith, avec les coûts calculés par nos tarifs.

    Chez Anthropic, les tokens de cache s'AJOUTENT à input_tokens : on les somme
    dans input_tokens, comme le fait LangSmith lui-même pour Anthropic.
    """
    config.verifier_modele(modele)
    t = config.TARIFS[modele]
    u = _lire_usage(usage)
    f = config.REMISE_BATCH if batch else 1.0
    ecriture = t["ecriture_cache"] if ttl == "5m" else t["entree"] * config.MULTIPLICATEUR_ECRITURE_1H
    cout_entree = f * (u["input_tokens"] * t["entree"]
                       + u["cache_creation_input_tokens"] * ecriture
                       + u["cache_read_input_tokens"] * t["lecture_cache"]) / 1e6
    cout_sortie = f * u["output_tokens"] * t["sortie"] / 1e6
    entree = u["input_tokens"] + u["cache_creation_input_tokens"] + u["cache_read_input_tokens"]
    details = {}
    if u["cache_read_input_tokens"]:
        details["cache_read"] = u["cache_read_input_tokens"]
    if u["cache_creation_input_tokens"]:
        details["cache_creation"] = u["cache_creation_input_tokens"]
    um = {
        "input_tokens": entree,
        "output_tokens": u["output_tokens"],
        "total_tokens": entree + u["output_tokens"],
        "input_cost": round(cout_entree, 6),
        "output_cost": round(cout_sortie, 6),
        "total_cost": round(cout_entree + cout_sortie, 6),
    }
    if details:
        um["input_token_details"] = details
    return um


def _client():
    global _CLIENT
    if _CLIENT is None:
        from langsmith.run_trees import get_cached_client

        _CLIENT = get_cached_client()
    return _CLIENT


def tracer(
    *,
    modele: str,
    etiquette: str,
    usage,
    debut: datetime,
    fin: datetime,
    meta: dict | None = None,
    stop_reason: str | None = None,
    batch: bool = False,
    ttl: str = "5m",
    client=None,
) -> bool:
    """Envoie une trace « llm » à LangSmith. Renvoie True si elle a été envoyée."""
    if client is None and not actif():
        return False
    try:
        from langsmith.run_trees import RunTree

        meta = {k: v for k, v in (meta or {}).items() if isinstance(v, (str, int, float, bool)) or v is None}
        um = usage_metadata(modele, usage, batch=batch, ttl=ttl)
        run = RunTree(
            name=etiquette,
            run_type="llm",
            inputs={"etiquette": etiquette, **meta},  # métadonnées seulement, jamais le texte
            start_time=debut,
            extra={"metadata": {"ls_provider": "anthropic", "ls_model_name": modele,
                                "batch": batch, "ttl": ttl, **meta}},
            tags=[etiquette, modele] + (["batch"] if batch else []),
            project_name=os.getenv("LANGSMITH_PROJECT", "projet-conformite"),
            ls_client=client or _client(),
        )
        run.end(outputs={"usage_metadata": um, "stop_reason": stop_reason}, end_time=fin)
        run.post()
        return True
    except Exception as e:
        warnings.warn(f"Trace LangSmith non envoyée : {e.__class__.__name__}: {e}")
        return False


def vider() -> None:
    """À appeler en fin de script : les traces partent en arrière-plan et seraient perdues sinon."""
    if not actif() or _CLIENT is None:
        return
    try:
        _CLIENT.flush()
    except Exception as e:
        warnings.warn(f"Envoi final des traces LangSmith incomplet : {e}")


def maintenant() -> datetime:
    return datetime.now(timezone.utc)
