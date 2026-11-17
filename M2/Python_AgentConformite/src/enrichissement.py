"""Enrichissement SEUL (ctrl, test) d'une extraction figée, avec une version de prompt donnée.

Sert aux expériences « toutes choses égales par ailleurs » : on garde exactement les mêmes
lignes extraites (ref, cit, dom, obl, typ, crit) et on ne fait varier que la consigne
d'enrichissement. Les requêtes sont celles de l'Agent 1 (même système, même document en
cache, mêmes lots) ; seule l'étiquette de répétition change, pour que le cache disque ne
renvoie pas la réponse d'une répétition précédente.
"""

from src import agent1, appel_llm, config
from src.schema import Enrichissement, analyser_sortie, fusionner

CHAMPS_EXTRACTION = ("id", "ref", "cit", "dom", "obl", "typ", "crit", "_verif", "_tache", "_rattrapage", "_doublons")


def enrichir(lignes: list[dict], *, texte: str, nom_document: str, version: str, repetition: int,
             langue: str | None = None, modele: str | None = None, effort: str | None = agent1.EFFORT_DEFAUT,
             taille_lot: int = agent1.TAILLE_LOT_DEFAUT, journal=None, dossier_cache=None) -> dict:
    modele = modele or config.MODELE_EXTRACTION
    langue = langue or agent1.detecter_langue(texte)
    systeme = agent1.construire_systeme(texte, nom_document, langue, version)
    extraites = [{k: l[k] for k in CHAMPS_EXTRACTION if k in l} for l in lignes]
    lots = [extraites[i: i + taille_lot] for i in range(0, len(extraites), taille_lot)]
    objets, rejets, usages = [], [], []
    for n, lot in enumerate(lots, 1):
        rep = appel_llm.appeler(
            modele=modele, systeme=systeme,
            messages=[{"role": "user", "content": agent1.consigne_enrichissement(lot, version)}],
            etiquette="experience-enrichissement", version_prompt=f"{version}-enrichissement-r{repetition}",
            max_tokens=agent1.MAX_TOKENS_ENRICHISSEMENT, effort=effort,
            meta={"lot": n, "repetition": repetition, "version": version}, journal=journal,
            dossier_cache=dossier_cache)
        obj, rej = analyser_sortie(appel_llm.texte_de_reponse(rep), Enrichissement)
        attendus = {l["id"] for l in lot}
        objets += [o for o in obj if o["id"] in attendus]
        rejets += rej
        usages.append(rep.get("usage"))
    finales, manquants = fusionner(extraites, objets)
    return {"lignes": finales, "non_enrichies": manquants, "rejets": rejets, "usages": usages}
