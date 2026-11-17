"""Cache disque des réponses : relancer un script ou un notebook ne doit rien coûter.

La clé est l'empreinte SHA-256 de TOUT ce qui détermine la réponse : modèle,
système (consignes + document), messages, paramètres et version du prompt.
Changer la moindre virgule d'un prompt sans changer sa version donnerait une
clé différente de toute façon, mais la version rend les entrées lisibles.
"""

import hashlib
import json
from pathlib import Path
from typing import Callable

from src import config


def cle_cache(modele, systeme, messages, version_prompt: str, params: dict | None = None) -> str:
    contenu = {
        "modele": modele,
        "systeme": systeme,
        "messages": messages,
        "params": params or {},
        "version_prompt": version_prompt,
    }
    brut = json.dumps(contenu, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(brut.encode("utf-8")).hexdigest()


def _chemin(cle: str, dossier: Path | None) -> Path:
    dossier = Path(dossier or config.DOSSIER_CACHE)
    return dossier / cle[:2] / f"{cle}.json"  # sous-dossiers pour éviter 10 000 fichiers au même niveau


def lire(cle: str, dossier: Path | None = None) -> dict | None:
    p = _chemin(cle, dossier)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def ecrire(cle: str, reponse: dict, dossier: Path | None = None) -> Path:
    p = _chemin(cle, dossier)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(reponse, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)  # écriture atomique : jamais de fichier à moitié écrit si on interrompt
    return p


def appel_memoise(
    appeler: Callable[..., dict],
    *,
    modele: str,
    systeme,
    messages,
    version_prompt: str,
    params: dict | None = None,
    dossier: Path | None = None,
) -> tuple[dict, bool]:
    """Renvoie (réponse, vient_du_cache).

    `appeler(modele=..., systeme=..., messages=..., **params)` fait le VRAI appel,
    journalise son coût et renvoie un dict sérialisable (ex. message.model_dump()).
    Sur un succès de cache, `appeler` n'est pas exécuté : coût nul, rien à journaliser.
    """
    cle = cle_cache(modele, systeme, messages, version_prompt, params)
    deja = lire(cle, dossier)
    if deja is not None:
        return deja, True
    reponse = appeler(modele=modele, systeme=systeme, messages=messages, **(params or {}))
    ecrire(cle, reponse, dossier)
    return reponse, False
