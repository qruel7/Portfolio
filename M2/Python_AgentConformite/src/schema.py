"""Schéma pivot de l'Agent 1 (décision 4.1), produit en DEUX TEMPS depuis la v2.

1. Extraction   : ref, cit, dom, obl, typ, crit  → sert à mesurer l'essoufflement
                  (sortie compacte : le passage unique ne bute plus sur la limite de sortie).
2. Enrichissement : ctrl, test, pour chaque ligne extraite.
La ligne finale (Ligne) est la fusion des deux ; elle est identique quel que soit le corpus.
"""

import json
import re
from typing import Literal

from pydantic import BaseModel, ValidationError

VERSION_SCHEMA = "pivot-v2"


class LigneExtraite(BaseModel):
    id: str  # identifiant stable, ex. "S05-003"
    ref: str  # référence dans le texte (paragraphe, article)
    cit: str  # citation EXACTE du passage qui fonde la ligne
    dom: str  # domaine / thème
    obl: str  # l'obligation, en une phrase
    typ: Literal["mesure", "controle", "documentation"]
    crit: Literal["critique", "majeure", "significative", "mineure"]


class Enrichissement(BaseModel):
    id: str
    ctrl: str  # le contrôle clé attendu chez l'entité
    test: str  # le test de conformité / la recommandation opérationnelle


class Ligne(LigneExtraite):
    ctrl: str
    test: str


class Referentiel(BaseModel):
    lignes: list[Ligne]


_BLOC_JSON = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _objets_un_par_un(brut: str) -> list:
    """Repli pour une sortie tronquée : récupère chaque objet {"id": …} complet.

    On lit les objets les uns après les autres avec raw_decode et on s'arrête au
    premier objet cassé (en général le dernier, coupé par max_tokens).
    """
    dec, objets = json.JSONDecoder(), []
    k = re.search(r'\{\s*"id"', brut)
    k = k.start() if k else -1
    while k >= 0:
        try:
            obj, fin = dec.raw_decode(brut, k)
        except json.JSONDecodeError:
            break
        objets.append(obj)
        m = re.search(r'\{\s*"id"', brut[fin:])
        k = fin + m.start() if m else -1
    return objets


def analyser_sortie(texte: str, modele=LigneExtraite) -> tuple[list[dict], list[dict]]:
    """Extrait et valide les objets d'une réponse du modèle.

    Renvoie (objets valides, rejets). Un objet mal formé n'invalide pas les autres :
    on le met de côté avec la raison, pour mesurer la validité structurelle
    (au sens de LongDA) séparément de la justesse. Une sortie TRONQUÉE est
    récupérée objet par objet ; le rejet signale la troncature.
    """
    brut = texte.strip()
    m = _BLOC_JSON.search(brut)
    if m:
        brut = m.group(1).strip()
    rejets = []
    try:
        debut, fin = brut.find("{"), brut.rfind("}")
        donnees = json.loads(brut[debut : fin + 1] if debut >= 0 else brut)
        candidats = donnees.get("lignes", []) if isinstance(donnees, dict) else donnees
    except json.JSONDecodeError as e:
        candidats = _objets_un_par_un(brut)
        rejets.append({"raison": f"JSON global illisible ({e.msg}) : {len(candidats)} objets "
                                 "complets récupérés, la suite est perdue", "extrait": brut[-200:]})
    if not isinstance(candidats, list):
        return [], [{"raison": "pas de liste 'lignes'", "extrait": str(candidats)[:200]}]
    valides = []
    for c in candidats:
        try:
            valides.append(modele.model_validate(c).model_dump())
        except ValidationError as e:
            rejets.append({"raison": e.errors()[0]["msg"], "ligne": c})
    return valides, rejets


def fusionner(extraites: list[dict], enrichissements: list[dict]) -> tuple[list[dict], list[str]]:
    """Ligne finale = extraction + enrichissement de même id. Renvoie (lignes, ids non enrichis)."""
    par_id = {e["id"]: e for e in enrichissements}
    finales, manquants = [], []
    for l in extraites:
        e = par_id.get(l["id"])
        if e is None:
            manquants.append(l["id"])
            finales.append({**l, "ctrl": "", "test": ""})
        else:
            finales.append({**l, "ctrl": e["ctrl"], "test": e["test"]})
    return finales, manquants
