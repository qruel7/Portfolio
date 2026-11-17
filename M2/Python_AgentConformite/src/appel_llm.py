"""POINT D'ENTRÉE UNIQUE vers l'API pour les appels synchrones.

Chaque appel passe, dans cet ordre, par :
1. verifier_modele()  : Fable et les modèles sans tarif sont refusés ;
2. le cache disque    : une requête déjà payée n'est jamais repayée ;
3. verifier_budget()  : refus AVANT l'appel si l'estimation pessimiste dépasse le seuil ;
4. l'appel, avec réessais uniquement sur 429 / 5xx / erreurs réseau ;
5. journaliser()      : coût réel tiré de l'objet `usage`, dans logs/couts.jsonl ;
6. traces.tracer()   : trace LangSmith (métadonnées + coût exact, jamais le texte),
                       si LANGSMITH_TRACING=true. Voir src/traces.py pour le pourquoi.

Aucun paramètre d'échantillonnage (temperature, top_p, top_k) n'est jamais envoyé.
Les lots batch auront leur propre module, mais journaliseront dans le même fichier.
"""

import json

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_random_exponential

from src import cache_disque, config, couts, traces

PARAMETRES_INTERDITS = ("temperature", "top_p", "top_k")
_CLIENT = None


def _client():
    """Client Anthropic créé à la demande (non enveloppé : voir src/traces.py)."""
    global _CLIENT
    if _CLIENT is None:
        import anthropic

        config.exiger_cle()
        _CLIENT = anthropic.Anthropic(max_retries=0)  # les réessais sont gérés ici, et comptés
    return _CLIENT


def _erreur_reessayable(e: BaseException) -> bool:
    """429, 5xx (dont 529 « overloaded ») et erreurs réseau. Jamais 400/401/403/404."""
    import anthropic

    if isinstance(e, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
        return True
    if isinstance(e, anthropic.APIStatusError):
        return e.status_code == 429 or e.status_code >= 500
    return False


@retry(
    retry=retry_if_exception(_erreur_reessayable),
    wait=wait_random_exponential(multiplier=2, max=60),  # attente exponentielle avec aléa
    stop=stop_after_attempt(5),
    reraise=True,
)
def _envoyer(**requete):
    # Toujours en streaming : le SDK refuse les appels non diffusés dont la durée
    # estimée est longue (grand max_tokens, mode passage unique). Coût identique.
    with _client().messages.stream(**requete) as flux:
        return flux.get_final_message()


def estimation_pessimiste(modele: str, systeme, messages, max_tokens: int) -> float:
    """Borne haute du coût : tout le préfixe payé en écriture de cache, sortie au maximum."""
    caracteres = len(json.dumps(systeme, ensure_ascii=False)) + len(json.dumps(messages, ensure_ascii=False))
    tokens_entree = int(caracteres / 3.0)  # 3,0 plutôt que 3,04 : on se trompe du côté prudent
    usage = {"cache_creation_input_tokens": tokens_entree, "output_tokens": max_tokens}
    return couts.cout(modele, usage)


def appeler(
    *,
    modele: str,
    systeme,
    messages: list,
    etiquette: str,
    version_prompt: str,
    max_tokens: int,
    effort: str | None = None,
    meta: dict | None = None,
    journal=None,
    dossier_cache=None,
) -> dict:
    """Fait (ou relit depuis le disque) un appel et renvoie la réponse sous forme de dict.

    Le dict contient la réponse brute de l'API (`model_dump()`) et `_vient_du_cache`.
    """
    config.verifier_modele(modele)
    params = {"max_tokens": max_tokens}
    if effort and not modele.startswith("claude-haiku"):  # Haiku 4.5 ne supporte pas effort
        params["effort"] = effort

    def faire_appel(modele, systeme, messages, max_tokens, effort=None):
        couts.verifier_budget(estimation_pessimiste(modele, systeme, messages, max_tokens), chemin=journal)
        requete = {"model": modele, "system": systeme, "messages": messages, "max_tokens": max_tokens}
        if effort:
            # paramètre documenté dans le cadrage ; passé en extra_body pour ne pas
            # dépendre de la version du SDK
            requete["extra_body"] = {"output_config": {"effort": effort}}
        assert not any(p in requete for p in PARAMETRES_INTERDITS)
        debut = traces.maintenant()
        reponse = _envoyer(**requete)
        fin = traces.maintenant()
        meta_complete = {"version_prompt": version_prompt, "max_tokens": max_tokens, "effort": effort,
                         "stop_reason": reponse.stop_reason, "id_reponse": reponse.id,
                         "duree_s": round((fin - debut).total_seconds(), 1), **(meta or {})}
        couts.journaliser(modele, reponse.usage, etiquette, meta=meta_complete, chemin=journal)
        traces.tracer(modele=modele, etiquette=etiquette, usage=reponse.usage, debut=debut, fin=fin,
                      meta=meta_complete, stop_reason=reponse.stop_reason)
        return reponse.model_dump()

    resultat, vient_du_cache = cache_disque.appel_memoise(
        faire_appel,
        modele=modele,
        systeme=systeme,
        messages=messages,
        version_prompt=version_prompt,
        params=params,
        dossier=dossier_cache,
    )
    return {**resultat, "_vient_du_cache": vient_du_cache}


def texte_de_reponse(reponse: dict) -> str:
    return "".join(b.get("text", "") for b in reponse.get("content", []) if b.get("type") == "text")
