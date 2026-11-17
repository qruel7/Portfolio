"""Passe de rattrapage (logique partagée par scripts/rattraper.py et le pipeline LangGraph).

La RÈGLE décide quels paragraphes revoir (src/couverture.py), le LLM extrait, sur EXACTEMENT
le même préfixe que le run d'origine. Le run d'origine n'est jamais modifié ; le résultat est
un référentiel consolidé <run>_consolide.json (lignes du run + lignes marquées "_rattrapage").
"""

import json
from pathlib import Path

from src import agent1, config
from src.couverture import paragraphes_omis
from src.decoupage import decouper, section_de_position
from src.extraction import charger_document, empreinte

TAILLE_LOT_PARAGRAPHES = 20


class RattrapageImpossible(ValueError):
    pass


def preparer(chemin_run: Path, chemin_document: Path, seuil: int = 1, mini: bool = False,
             doc: dict | None = None) -> dict:
    """Relit le run, reconstruit le texte, repère les paragraphes omis. Aucun appel API."""
    chemin_run = Path(chemin_run)
    reanalyse = chemin_run.with_name(chemin_run.stem + "_reanalyse.jsonl")
    source = reanalyse if reanalyse.exists() else chemin_run  # citations revérifiées si disponibles
    enreg = [json.loads(l) for l in source.read_text(encoding="utf-8").splitlines() if l.strip()]
    entete = enreg[0]
    if entete.get("mode") == "rattrapage":
        raise RattrapageImpossible("Donner le run d'origine, pas un run de rattrapage.")
    texte = (doc or charger_document(Path(chemin_document)))["texte"]
    sections = decouper(texte, **entete["params_decoupage"])
    if mini:
        texte, sections = agent1.mini_document(texte, sections, entete["taches"])
    if empreinte(texte) != entete["sha256_texte"]:
        raise RattrapageImpossible("Le texte reconstruit ne correspond pas à celui du run (empreintes différentes).")
    lignes_par_tache, finales = {}, []
    for e in enreg[1:]:
        if e["type"] == "extraction":
            lignes_par_tache.setdefault(e["tache"], []).extend(e["lignes"])
        elif e["type"] == "synthese":
            finales = e["lignes"]
    omis = [o for o in paragraphes_omis(texte, sections, lignes_par_tache) if o["prescriptif"] >= seuil]
    version = entete["version_prompt"]
    lots = [omis[i: i + TAILLE_LOT_PARAGRAPHES] for i in range(0, len(omis), TAILLE_LOT_PARAGRAPHES)]
    taches = [(f"R{k}", agent1.consigne_rattrapage(texte, lot, f"R{k}", version)) for k, lot in enumerate(lots, 1)]
    return {"chemin_run": chemin_run, "source": source, "entete": entete, "texte": texte, "sections": sections,
            "finales": finales, "omis": omis, "taches": taches}


def estimer(prep: dict) -> dict:
    """Coût prévisionnel (hypothèse : une ligne par paragraphe revu, cache du run expiré)."""
    entete, t = prep["entete"], config.TARIFS[prep["entete"]["modele"]]
    prefixe = int(len(prep["texte"]) / 3.04) + 2_400
    n_lignes = len(prep["omis"])
    n_appels = len(prep["taches"]) + -(-n_lignes // entete.get("taille_lot", 20)) if n_lignes else 0
    ecriture = prefixe * t["ecriture_cache"] / 1e6 if n_appels else 0.0
    lectures = max(0, n_appels - 1) * prefixe * t["lecture_cache"] / 1e6
    sortie = n_lignes * (190 + 210) * t["sortie"] / 1e6
    return {"appels": n_appels, "prefixe": prefixe, "ecriture": ecriture, "lectures": lectures, "sortie": sortie,
            "total": ecriture + lectures + sortie}


def chemin_consolide(chemin_run: Path) -> Path:
    chemin_run = Path(chemin_run)
    return chemin_run.with_name(chemin_run.stem + "_consolide.json")


def executer(prep: dict, journal=None, dossier_cache=None, dossier_resultats=None) -> dict:
    """Lance l'extraction ciblée (s'il y a des paragraphes omis) et écrit le consolidé dans tous les cas."""
    entete, sections = prep["entete"], prep["sections"]
    nouvelles, id_rattrapage = [], None
    if prep["omis"]:
        res = agent1.executer(
            texte=prep["texte"], sections=sections, mode="rattrapage", nom_document=entete["nom_document"],
            sha_texte=entete["sha256_texte"], langue=entete["langue"], modele=entete["modele"],
            max_tokens=entete["max_tokens"], effort=entete["effort"], taille_lot=entete.get("taille_lot", 20),
            version=entete["version_prompt"], params_decoupage=entete["params_decoupage"], taches=prep["taches"],
            etiquette="agent1-rattrapage", journal=journal, dossier_cache=dossier_cache,
            dossier_resultats=dossier_resultats,
            meta_run={"rattrapage_de": entete["id_run"], "paragraphes_revus": [o["paragraphe"] for o in prep["omis"]]},
        )
        id_rattrapage = res["id_run"]
        for l in res["lignes"]:  # section d'origine retrouvée par la position de la citation
            pos = (l.get("_verif") or {}).get("debut")
            s_ = section_de_position(sections, pos) if pos is not None else None
            nouvelles.append({**l, "_rattrapage": True, "_tache": s_.id if s_ else l.get("_tache")})
    consolide = chemin_consolide(prep["chemin_run"])
    consolide.write_text(json.dumps({
        "run": entete["id_run"], "rattrapage": id_rattrapage, "sha256_texte": entete["sha256_texte"],
        "version_prompt": entete["version_prompt"], "nb_lignes_run": len(prep["finales"]),
        "nb_lignes_rattrapage": len(nouvelles), "lignes": prep["finales"] + nouvelles,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"consolide": consolide, "nb_nouvelles": len(nouvelles), "nb_omis": len(prep["omis"]),
            "id_rattrapage": id_rattrapage}
