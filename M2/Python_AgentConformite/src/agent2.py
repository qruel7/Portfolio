"""Agent 2 : évalue un référentiel de l'Agent 1 contre un référentiel de référence.

Principe (docs/regle_appariement.md) : le juge LLM rend des verdicts ÉLÉMENT PAR ÉLÉMENT ;
le CODE en déduit la couverture de chaque ligne, les métriques et la gap analysis.

Structure des requêtes, du plus stable au plus variable :
    système[0] = consignes (fichier versionné, règle d'appariement)
    système[1] = <referentiel_ia>…</referentiel_ia>  ← point de cache_control
    message    = « TÂCHE : APPARIEMENT » + lignes de référence, ou « TÂCHE : PERTINENCE » + ids
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field

from src import appel_llm, config
from src.referentiels import ligne_en_texte
from src.schema import analyser_sortie

DOSSIER_PROMPTS = Path(__file__).resolve().parent / "prompts"
VERSION_PROMPT = "v1"
EFFORT_DEFAUT = "medium"
MAX_TOKENS_APPARIEMENT = 16_000
MAX_TOKENS_PERTINENCE = 8_000
LIGNES_PAR_BLOC = 4  # lignes de référence par requête d'appariement
LOT_PERTINENCE = 40  # lignes IA par requête de pertinence
SCORES = {"equivalent": 2, "principe": 1, "absent": 0}


class Element(BaseModel):
    element: str
    niveau: Literal["equivalent", "principe", "absent"]
    lignes: list[str] = Field(default_factory=list)
    justification: str = ""


class Verdict(BaseModel):
    # le juge écrit parfois « id » au lieu de « id_ref » (observé le 24/10, bloc 2) : on accepte les deux
    id_ref: str = Field(validation_alias=AliasChoices("id_ref", "id"))
    hors_perimetre: bool = False
    justification: str = ""
    elements: list[Element] = Field(default_factory=list)


class Pertinence(BaseModel):
    id: str
    p: Literal["pertinente", "faible", "non_pertinente"]
    raison: str = ""


def charger_prompt(nom: str, version: str = VERSION_PROMPT) -> str:
    lignes = (DOSSIER_PROMPTS / f"{nom}_{version}.txt").read_text(encoding="utf-8").splitlines()
    while lignes and (lignes[0].startswith("#") or not lignes[0].strip()):
        lignes.pop(0)
    return "\n".join(lignes).strip() + "\n"


def compacter(lignes_ia: list[dict]) -> str:
    """Référentiel IA en JSON Lines compact (les champs utiles au juge, rien d'autre)."""
    champs = ("id", "ref", "dom", "obl", "ctrl", "test")
    return "\n".join(json.dumps({k: l.get(k, "") for k in champs}, ensure_ascii=False) for l in lignes_ia)


def construire_systeme(lignes_ia: list[dict], nom_document: str, version: str = VERSION_PROMPT) -> list:
    consignes = charger_prompt("agent2_systeme", version).format(nom_document=nom_document)
    return [
        {"type": "text", "text": consignes},
        {"type": "text", "text": f"<referentiel_ia>\n{compacter(lignes_ia)}\n</referentiel_ia>",
         "cache_control": {"type": "ephemeral"}},
    ]


def _blocs(lignes_ref: list[dict], taille: int, colonne_id: str | None = None) -> list[list[dict]]:
    """Blocs de lignes consécutives partageant la première colonne qui n'est pas l'identifiant
    (Classification, Domaine…), à la manière de l'évaluation par blocs de LongDA ;
    taille maximale `taille`."""
    blocs, courant, cle = [], [], None
    for l in lignes_ref:
        c = next((v for k, v in l["champs"].items() if k != colonne_id), "")
        if courant and (c != cle or len(courant) >= taille):
            blocs.append(courant)
            courant = []
        courant.append(l)
        cle = c
    if courant:
        blocs.append(courant)
    return blocs


def couverture_ligne(verdict: dict) -> tuple[str, float | None]:
    """La RÈGLE décide (section 4 de la règle) : (couverture, score de qualité entre 0 et 1)."""
    if verdict["hors_perimetre"]:
        return "hors_perimetre", None
    niveaux = [e["niveau"] for e in verdict["elements"]]
    if not niveaux:
        return "absente", 0.0
    score = sum(SCORES[n] for n in niveaux) / len(niveaux) / 2
    if all(n == "equivalent" for n in niveaux):
        return "totale", score
    if any(n != "absent" for n in niveaux):
        return "partielle", score
    return "absente", score


def nettoyer_verdict(verdict: dict, ids_ia: set) -> tuple[dict, list[str]]:
    """Retire les id de lignes IA inexistants ; un élément sans id valide redevient « absent »."""
    inventes = []
    for e in verdict["elements"]:
        valides = [i for i in e["lignes"] if i in ids_ia]
        inventes += [i for i in e["lignes"] if i not in ids_ia]
        e["lignes"] = valides
        if e["niveau"] != "absent" and not valides:
            e["niveau"] = "absent"
            e["justification"] = (e["justification"] + " [rétrogradé : aucun id valide]").strip()
    return verdict, inventes


def evaluer_bloc(brut: str, bloc: list[dict], ids_ia: set) -> tuple[list[dict], list[dict]]:
    """Réponse brute du juge → évaluations des lignes du bloc (la règle calcule la couverture)."""
    verdicts, rejets = analyser_sortie(brut.replace('"verdicts"', '"lignes"', 1), Verdict)
    par_id = {v["id_ref"]: v for v in verdicts}
    evaluations = []
    for l in bloc:
        v = par_id.get(l["id_ref"])
        if v is None:  # verdict manquant : signalé, jamais imputé
            evaluations.append({"id_ref": l["id_ref"], "couverture": "non_evaluee", "score": None,
                                "verdict": None, "ids_inventes": [], "champs_vides": l["champs_vides"]})
            continue
        v, inventes = nettoyer_verdict(v, ids_ia)
        couv, score = couverture_ligne(v)
        evaluations.append({"id_ref": l["id_ref"], "couverture": couv, "score": score, "verdict": v,
                            "ids_inventes": inventes, "champs_vides": l["champs_vides"]})
    return evaluations, rejets


def reanalyser(chemin: Path, lignes_ia: list[dict], referentiel: dict) -> dict:
    """Relit un run de l'Agent 2 et recalcule TOUT depuis les réponses brutes, sans appel (gratuit)."""
    enreg = [json.loads(l) for l in Path(chemin).read_text(encoding="utf-8").splitlines() if l.strip()]
    ids_ia = {l["id"] for l in lignes_ia}
    par_id = {l["id_ref"]: l for l in referentiel["lignes"]}
    evaluations, pertinences = [], []
    for e in enreg:
        if e["type"] == "appariement":
            bloc = [par_id[i] for i in e["ids_ref"]]
            evals, _ = evaluer_bloc(e["reponse_brute"], bloc, ids_ia)
            evaluations += evals
        elif e["type"] == "pertinence":
            objets, _ = analyser_sortie(e["reponse_brute"].replace('"verdicts"', '"lignes"', 1), Pertinence)
            pertinences += [o for o in objets if o["id"] in set(e["ids"])]
    ok = [e for e in evaluations if e["couverture"] != "non_evaluee"]
    mobilisees = {i for e in ok if e["verdict"] for el in e["verdict"]["elements"] for i in el["lignes"]}
    # les lignes nouvellement mobilisées ne sont plus « supplémentaires »
    pertinences = [p for p in pertinences if p["id"] not in mobilisees]
    m = metriques(ok, pertinences, len(lignes_ia))
    m["nb_non_evaluees"] = len(evaluations) - len(ok)
    return {"metriques": m, "evaluations": evaluations, "pertinences": pertinences}


def metriques(evaluations: list[dict], pertinences: list[dict], nb_lignes_ia: int) -> dict:
    evaluees = [e for e in evaluations if e["couverture"] != "hors_perimetre"]
    n = len(evaluees)
    compte = {c: sum(e["couverture"] == c for e in evaluees) for c in ("totale", "partielle", "absente")}
    p = {v: sum(x["p"] == v for x in pertinences) for v in ("pertinente", "faible", "non_pertinente")}
    return {
        "nb_lignes_reference": len(evaluations),
        "nb_hors_perimetre": len(evaluations) - n,
        "nb_evaluees": n,
        "comptes": compte,
        "couverture_stricte": compte["totale"] / n if n else None,
        "couverture_large": (compte["totale"] + compte["partielle"]) / n if n else None,
        "qualite_moyenne": sum(e["score"] for e in evaluees) / n if n else None,
        "nb_lignes_ia": nb_lignes_ia,
        "nb_lignes_ia_mobilisees": nb_lignes_ia - len(pertinences),
        "pertinence_supplementaires": p,
        "taux_pertinence_supplementaires": p["pertinente"] / len(pertinences) if pertinences else None,
    }


def executer(
    *,
    lignes_ia: list[dict],
    referentiel: dict,
    nom_document: str,
    id_source: str,
    modele: str | None = None,
    effort: str | None = EFFORT_DEFAUT,
    pertinence: bool = True,
    version: str = VERSION_PROMPT,
    dossier_resultats: Path | None = None,
    journal=None,
    dossier_cache=None,
) -> dict:
    modele = modele or config.MODELE_EXTRACTION
    systeme = construire_systeme(lignes_ia, nom_document, version)
    ids_ia = {l["id"] for l in lignes_ia}
    horodatage = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    id_run = f"agent2-{referentiel['sha256'][:8]}-{version}-{horodatage}"
    dossier = Path(dossier_resultats or config.DOSSIER_RESULTATS)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{id_run}.jsonl"

    def ecrire(enreg):
        with chemin.open("a", encoding="utf-8") as f:
            f.write(json.dumps(enreg, ensure_ascii=False) + "\n")

    ecrire({"type": "entete", "id_run": id_run, "modele": modele, "effort": effort,
            "version_prompt": version, "regle_appariement": "docs/regle_appariement.md v1",
            "source_ia": id_source, "nb_lignes_ia": len(lignes_ia), "referentiel": referentiel["fichier"],
            "sha256_referentiel": referentiel["sha256"], "colonnes": referentiel["colonnes"],
            "nom_document": nom_document})

    def appel(consigne, etape, meta, plafond):
        return appel_llm.appeler(modele=modele, systeme=systeme, messages=[{"role": "user", "content": consigne}],
                                 etiquette=f"agent2-{etape}", version_prompt=version, max_tokens=plafond,
                                 effort=effort, meta={"id_run": id_run, **meta}, journal=journal,
                                 dossier_cache=dossier_cache)

    # ---- Appariement -----------------------------------------------------------------------
    evaluations = []
    for n, bloc in enumerate(_blocs(referentiel["lignes"], LIGNES_PAR_BLOC, referentiel.get("colonne_id")), 1):
        consigne = charger_prompt("agent2_appariement", version).format(
            nb=len(bloc), lignes_reference="\n\n".join(ligne_en_texte(l) for l in bloc))
        rep = appel(consigne, "appariement", {"bloc": n}, MAX_TOKENS_APPARIEMENT)
        brut = appel_llm.texte_de_reponse(rep)
        evals_bloc, rejets = evaluer_bloc(brut, bloc, ids_ia)
        evaluations += evals_bloc
        ecrire({"type": "appariement", "bloc": n, "ids_ref": [l["id_ref"] for l in bloc],
                "usage": rep.get("usage"), "stop_reason": rep.get("stop_reason"), "rejets": rejets,
                "vient_du_cache_disque": rep["_vient_du_cache"], "reponse_brute": brut})
        etats = [e["couverture"] for e in evals_bloc]
        resume = ", ".join(l["id_ref"] + "=" + c for l, c in zip(bloc, etats))
        print(f"  appariement bloc {n}: {resume}")

    non_evaluees = [e for e in evaluations if e["couverture"] == "non_evaluee"]
    evaluations_ok = [e for e in evaluations if e["couverture"] != "non_evaluee"]

    # ---- Pertinence des lignes IA supplémentaires -----------------------------------------------
    mobilisees = {i for e in evaluations_ok if e["verdict"] for el in e["verdict"]["elements"] for i in el["lignes"]}
    supplementaires = [l["id"] for l in lignes_ia if l["id"] not in mobilisees]
    pertinences = []
    if pertinence and supplementaires:
        lots = [supplementaires[i : i + LOT_PERTINENCE] for i in range(0, len(supplementaires), LOT_PERTINENCE)]
        for n, lot in enumerate(lots, 1):
            consigne = charger_prompt("agent2_pertinence", version).format(nb=len(lot), ids="\n".join(lot))
            rep = appel(consigne, "pertinence", {"lot": n}, MAX_TOKENS_PERTINENCE)
            brut = appel_llm.texte_de_reponse(rep)
            objets, rejets = analyser_sortie(brut.replace('"verdicts"', '"lignes"', 1), Pertinence)
            objets = [o for o in objets if o["id"] in set(lot)]
            pertinences += objets
            ecrire({"type": "pertinence", "lot": n, "ids": lot, "usage": rep.get("usage"),
                    "stop_reason": rep.get("stop_reason"), "rejets": rejets, "verdicts": objets,
                    "vient_du_cache_disque": rep["_vient_du_cache"], "reponse_brute": brut})
            print(f"  pertinence lot {n}/{len(lots)}: {len(objets)}/{len(lot)} lignes jugées")

    m = metriques(evaluations_ok, pertinences, len(lignes_ia))
    m["nb_non_evaluees"] = len(non_evaluees)
    ecrire({"type": "synthese", "metriques": m, "evaluations": evaluations, "pertinences": pertinences})
    return {"id_run": id_run, "fichier": str(chemin), "metriques": m, "evaluations": evaluations,
            "pertinences": pertinences}
