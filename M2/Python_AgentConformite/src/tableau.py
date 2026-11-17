"""Couche de données du dashboard : lecture des fichiers produits par le projet. AUCUN appel API.

Tout ce que montre le dashboard vient de fichiers déjà sur disque :
    logs/couts.jsonl            journal des coûts (source de vérité comptable)
    resultats/*.jsonl           runs de l'Agent 1 (section, unique, rattrapage, batch) et de l'Agent 2
    resultats/*_consolide*.json référentiels consolidés / dédoublonnés
    resultats/*_reanalyse.json  ré-analyses de l'Agent 2
    resultats/*_essoufflement.json, repetitions*.json   mesures d'essoufflement
Les fonctions sont pures et testées (tests/test_tableau.py) ; app_streamlit.py ne fait qu'afficher.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

from src import config, couts


def _jsonl(chemin: Path) -> list[dict]:
    try:
        return [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, json.JSONDecodeError):
        return []


def _json(chemin: Path):
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ------------------------------------------------------------------------------ coûts


def couts_par_jour(journal: list[dict]) -> list[dict]:
    jours = defaultdict(float)
    for l in journal:
        jours[l["horodatage"][:10]] += l["cout_usd"]
    return [{"jour": j, "cout_usd": round(c, 4)} for j, c in sorted(jours.items())]


def couts_detail(journal: list[dict]) -> list[dict]:
    """Une ligne par étiquette : nb d'appels, coût, part batch, tokens et taux de lecture du cache."""
    groupes = defaultdict(lambda: {"appels": 0, "cout_usd": 0.0, "cout_batch_usd": 0.0, "entree": 0,
                                   "cache_ecrit": 0, "cache_lu": 0, "sortie": 0})
    for l in journal:
        g, u = groupes[l["etiquette"]], l["usage"]
        g["appels"] += 1
        g["cout_usd"] += l["cout_usd"]
        g["cout_batch_usd"] += l["cout_usd"] if l.get("batch") else 0.0
        g["entree"] += u.get("input_tokens", 0)
        g["cache_ecrit"] += u.get("cache_creation_input_tokens", 0)
        g["cache_lu"] += u.get("cache_read_input_tokens", 0)
        g["sortie"] += u.get("output_tokens", 0)
    sortie = []
    for etiquette, g in sorted(groupes.items(), key=lambda kv: -kv[1]["cout_usd"]):
        total_entree = g["entree"] + g["cache_ecrit"] + g["cache_lu"]
        sortie.append({"etiquette": etiquette, **{k: round(v, 4) if isinstance(v, float) else v for k, v in g.items()},
                       "part_lue_en_cache": round(g["cache_lu"] / total_entree, 3) if total_entree else None})
    return sortie


def resume_budget(chemin_journal: Path | None = None) -> dict:
    """Dépense du DERNIER mois présent dans le journal (en démo, après la fin du projet, le mois
    courant serait vide), et total du projet sur toute la durée."""
    journal = couts.lire_journal(chemin_journal)
    mois_ref = max((l["horodatage"][:7] for l in journal), default=None)
    mois = couts.depense(mois_ref, chemin=chemin_journal) if mois_ref else 0.0
    plafond = config.BUDGET_MENSUEL_USD * config.SEUIL_BUDGET
    return {"mois": mois_ref, "depense_mois": mois, "total_projet": sum(l["cout_usd"] for l in journal),
            "budget": config.BUDGET_MENSUEL_USD, "seuil": config.SEUIL_BUDGET,
            "plafond_blocage": plafond, "reste_avant_blocage": plafond - mois, "nb_appels": len(journal),
            "par_jour": couts_par_jour(journal), "par_etiquette": couts_detail(journal)}


# --------------------------------------------------------------------------- runs


def _plage_sections(sections) -> str | None:
    """« S01–S27 (27) » ; accepte une liste de dicts {id: …} ou de chaînes (runs de rattrapage)."""
    if not sections:
        return None
    ids = [x.get("id") if isinstance(x, dict) else str(x) for x in sections]
    return f"{ids[0]}–{ids[-1]} ({len(ids)})"


def lister_runs(dossier: Path | None = None) -> list[dict]:
    """Tous les fichiers de run (.jsonl) avec leur en-tête résumé, du plus récent au plus ancien."""
    dossier = Path(dossier or config.DOSSIER_RESULTATS)
    runs = []
    for f in sorted(dossier.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.stem.endswith("_reanalyse"):
            continue
        enreg = _jsonl(f)
        if not enreg or enreg[0].get("type") != "entete":
            continue
        try:
            runs.append(_resume_run(f, enreg))
        except Exception as exc:  # un fichier inattendu ne doit jamais casser le dashboard
            runs.append({"fichier": f.name, "chemin": str(f), "agent": "?", "erreur": f"{type(exc).__name__}: {exc}"})
    return runs


def _resume_run(f: Path, enreg: list[dict]) -> dict:
    e = enreg[0]
    agent = "agent2" if "regle_appariement" in e or f.name.startswith("agent2-") else "agent1"
    synthese = next((x for x in reversed(enreg) if x.get("type") == "synthese"), {})
    appels = [x for x in enreg if x.get("type") in ("extraction", "enrichissement", "appariement", "pertinence")]
    sortie_tok = sum((x.get("usage") or {}).get("output_tokens", 0) for x in appels)
    lignes = synthese.get("lignes", [])
    return {
        "fichier": f.name, "chemin": str(f), "agent": agent, "id_run": e.get("id_run"),
        "mode": e.get("mode") or ("agent2" if agent == "agent2" else None),
        "document": e.get("nom_document"), "modele": e.get("modele"), "effort": e.get("effort"),
        "version_prompt": e.get("version_prompt"), "batch": bool(e.get("batch_id")),
        "repetition": e.get("repetition"),
        "sections": _plage_sections(e.get("sections")),
        "nb_lignes": synthese.get("nb_lignes", len(lignes)) if agent == "agent1" else None,
        "citations_valides": sum((l.get("_verif") or {}).get("statut") == "valide" for l in lignes) if lignes else None,
        "metriques": synthese.get("metriques") if agent == "agent2" else None,
        "sortie_tokens": sortie_tok, "complet": bool(synthese),
    }


def statuts_citations(lignes: list[dict]) -> dict:
    c = defaultdict(int)
    for l in lignes:
        c[(l.get("_verif") or {}).get("statut", "non vérifiée")] += 1
    return dict(c)


def lignes_referentiel(chemin: Path) -> tuple[dict, list[dict]]:
    """Référentiel pivot (consolidé, dédoublonné) ou synthèse d'un run d'Agent 1."""
    chemin = Path(chemin)
    if chemin.suffix == ".json":
        d = _json(chemin) or {}
        return d, d.get("lignes", [])
    enreg = _jsonl(chemin)
    synthese = next((x for x in reversed(enreg) if x.get("type") == "synthese"), {})
    return (enreg[0] if enreg else {}), synthese.get("lignes", [])


def lister_referentiels_ia(dossier: Path | None = None) -> list[Path]:
    dossier = Path(dossier or config.DOSSIER_RESULTATS)
    return sorted(dossier.glob("*_consolide*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


# ------------------------------------------------------------------------- agent 2


def evaluation_agent2(chemin_run: Path) -> dict | None:
    """Résultat de l'Agent 2 : la ré-analyse si elle existe (corrige les verdicts mal formés), sinon la synthèse."""
    chemin_run = Path(chemin_run)
    enreg = _jsonl(chemin_run)
    if not enreg:
        return None
    entete = enreg[0]
    reanalyse = _json(chemin_run.with_name(chemin_run.stem + "_reanalyse.json"))
    synthese = next((x for x in reversed(enreg) if x.get("type") == "synthese"), None)
    source = reanalyse or synthese
    if not source:
        return None
    return {"entete": entete, "source": "ré-analyse" if reanalyse else "synthèse du run", **{
        k: source.get(k) for k in ("metriques", "evaluations", "pertinences")}}


def table_couverture(evaluation: dict, referentiel: dict | None = None) -> list[dict]:
    """Une ligne par ligne de référence : statut, score, éléments par niveau, lignes IA mobilisées."""
    textes = {}
    if referentiel:
        for l in referentiel.get("lignes", []):
            textes[l["id_ref"]] = " | ".join(f"{k} : {v}" for k, v in l["champs"].items() if v)
    sortie = []
    for e in evaluation.get("evaluations") or []:
        elements = (e.get("verdict") or {}).get("elements", [])
        niveaux = defaultdict(int)
        mobilisees = set()
        for el in elements:
            niveaux[el.get("niveau")] += 1
            mobilisees |= set(el.get("lignes") or [])
        sortie.append({"id_ref": e["id_ref"], "couverture": e["couverture"], "score": e.get("score"),
                       "equivalent": niveaux["equivalent"], "principe": niveaux["principe"],
                       "absent": niveaux["absent"], "lignes_ia": ", ".join(sorted(mobilisees)),
                       "justification": (e.get("verdict") or {}).get("justification", ""),
                       "ligne_reference": textes.get(e["id_ref"], "")})
    return sortie


def table_elements(evaluation: dict) -> list[dict]:
    return [{"id_ref": e["id_ref"], "element": el.get("element"), "niveau": el.get("niveau"),
             "lignes_ia": ", ".join(el.get("lignes") or []), "justification": el.get("justification", "")}
            for e in evaluation.get("evaluations") or [] for el in (e.get("verdict") or {}).get("elements", [])]


# --------------------------------------------------------------------- essoufflement


def lister_mesures(dossier: Path | None = None) -> dict:
    """Mesures d'essoufflement. Les fichiers d'expériences complémentaires (préfixes, Sapin 2)
    sont exclus de « repetitions » : leurs clés (« unique:complet »…) écraseraient celles d'IFRS 9."""
    dossier = Path(dossier or config.DOSSIER_RESULTATS)
    a_part = ("repetitions_prefixes.json", "repetitions_sapin2.json")
    return {"repetitions": sorted(p for p in dossier.glob("repetitions*.json") if p.name not in a_part),
            "complementaires": {p.name: p for p in dossier.glob("*.json") if p.name in a_part + (
                "longueur_prefixes.json", "controles_couverture.json")},
            "essoufflement": sorted(dossier.glob("*_essoufflement.json"), key=lambda p: p.stat().st_mtime,
                                    reverse=True)}


def courbes_rc(repetitions: dict) -> list[dict]:
    """Points r(c) moyens (et écart-type) de chaque configuration, prêts pour un graphique."""
    points = []
    for config_nom, g in repetitions.items():
        if config_nom.startswith("_"):
            continue
        for c, s in enumerate(g.get("r_c_moyen", []), start=1):
            for regle in ("large", "stricte"):
                r = s.get(f"r_{regle}") or {}
                if r.get("moyenne") is None:
                    continue
                et = r.get("ecart_type") or 0.0
                num = re.match(r"\D*(\d+)", s["section"] or "")
                points.append({"configuration": config_nom, "regle": regle, "c": int(num.group(1)) if num else c,
                               "section": s["section"],
                               "rappel": r["moyenne"], "bas": max(0.0, r["moyenne"] - et),
                               "haut": min(1.0, r["moyenne"] + et), "k": r.get("k")})
    return points


def synthese_repetitions(repetitions: dict) -> list[dict]:
    lignes = []
    for nom, g in repetitions.items():
        if nom.startswith("_"):
            continue
        pente = g.get("pente_lignes_large") or {}
        lignes.append({"configuration": nom, "k": g.get("k"),
                       "rappel_large": (g.get("rappel_large") or {}).get("moyenne"),
                       "ecart_type_rappel": (g.get("rappel_large") or {}).get("ecart_type"),
                       "pente_large": pente.get("moyenne"),
                       "ic95_pente": (f"[{pente['ic95'][0]:+.3f} ; {pente['ic95'][1]:+.3f}]" if pente.get("ic95") else None),
                       "p_valeur_pente": pente.get("p_valeur"),
                       "jaccard_lignes": (g.get("jaccard_lignes_R*") or {}).get("jaccard_moyen"),
                       "jaccard_paragraphes": (g.get("jaccard_paragraphes") or {}).get("jaccard_moyen"),
                       "lignes_par_run": (g.get("nb_lignes") or {}).get("moyenne"),
                       "reflexion_tokens": (g.get("reflexion_tokens") or {}).get("moyenne")})
    return lignes


# ------------------------------------------------------------------------ comparatif

_SOURCE = re.compile(r"^section-([0-9a-f]{8})-(v\w+?)-")


def _texte(nom_document: str) -> str:
    n = (nom_document or "").lower()
    return "IFRS 9" if "ifrs" in n else ("Sapin 2" if "sapin" in n else (nom_document or "?"))


def comparatif_versions(dossier: Path | None = None, exclus: set[str] = frozenset()) -> list[dict]:
    """Une ligne par (texte, version du prompt de l'Agent 1) : moyennes des runs de l'Agent 2.

    La version est lue dans le nom du référentiel évalué (« section-<empreinte>-<version>-… »).
    Sont écartés : les runs de contrôle (`exclus`) et ceux de l'expérience de la grille
    (« _grille- » : extraction figée, seul l'enrichissement varie). L'hallucination factuelle
    est recalculée sur le référentiel évalué quand son fichier est présent.
    """
    dossier = Path(dossier or config.DOSSIER_RESULTATS)
    groupes = defaultdict(list)
    for f in sorted(dossier.glob("agent2-*.jsonl")):
        if f.name in exclus:
            continue
        ev = evaluation_agent2(f)
        if not ev or not ev.get("metriques"):
            continue
        src = str(ev["entete"].get("source_ia", ""))
        m = _SOURCE.match(src)
        if not m or "_grille-" in src:
            continue
        halluc = None
        for suffixe in (".json", ".jsonl"):
            if (dossier / f"{src}{suffixe}").exists():
                _, lignes = lignes_referentiel(dossier / f"{src}{suffixe}")
                if lignes:
                    s = statuts_citations(lignes)
                    halluc = (s.get("introuvable", 0) + s.get("ref_incoherente", 0)) / len(lignes)
                break
        groupes[(_texte(ev["entete"].get("nom_document")), m.group(2))].append(
            {**ev["metriques"], "nb_lignes_ia": ev["entete"].get("nb_lignes_ia"), "hallucination": halluc})

    def moyenne(xs):
        xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else None

    sortie = []
    for (texte, version), runs in sorted(groupes.items()):
        sortie.append({"texte": texte, "version": version, "runs_agent2": len(runs),
                       "lignes_ia": moyenne([r["nb_lignes_ia"] for r in runs]),
                       "couverture_large": moyenne([r.get("couverture_large") for r in runs]),
                       "couverture_stricte": moyenne([r.get("couverture_stricte") for r in runs]),
                       "qualite": moyenne([r.get("qualite_moyenne") for r in runs]),
                       "hallucination": moyenne([r["hallucination"] for r in runs])})
    return sortie


# ------------------------------------------------------------------- fiche d'une ligne


def referentiel_ia_evalue(evaluation: dict, dossier: Path | None = None) -> tuple[Path | None, list[dict]]:
    """Le référentiel de l'Agent 1 évalué par un run de l'Agent 2 (d'après « source_ia »), s'il est sur disque."""
    dossier = Path(dossier or config.DOSSIER_RESULTATS)
    src = str((evaluation.get("entete") or {}).get("source_ia", ""))
    for suffixe in (".json", ".jsonl"):
        chemin = dossier / f"{src}{suffixe}"
        if src and chemin.exists():
            return chemin, lignes_referentiel(chemin)[1]
    return None, []


def fiche_ligne(evaluation: dict, id_ref: str, referentiel: dict | None, lignes_ia: list[dict]) -> dict | None:
    """Tout ce qu'il faut pour juger UNE ligne du référentiel : son texte, le verdict élément par
    élément, et les lignes de l'Agent 1 citées par le juge (avec leur citation de la norme),
    dans l'ordre où elles apparaissent dans les éléments."""
    e = next((x for x in evaluation.get("evaluations") or [] if x["id_ref"] == id_ref), None)
    if e is None:
        return None
    champs = next((l["champs"] for l in (referentiel or {}).get("lignes", []) if l["id_ref"] == id_ref), {})
    verdict = e.get("verdict") or {}
    index = {l.get("id"): l for l in lignes_ia}
    ordre, elements = [], []
    for el in verdict.get("elements", []):
        ids = list(el.get("lignes") or [])
        elements.append({"element": el.get("element"), "niveau": el.get("niveau"), "lignes_ia": ", ".join(ids),
                         "justification": el.get("justification", "")})
        ordre += [i for i in ids if i not in ordre]
    lignes = []
    for i in ordre:
        l = index.get(i)
        lignes.append({"id": i, "trouvee": l is not None, **({k: l.get(k) for k in (
            "ref", "obl", "cit", "dom", "typ", "crit", "ctrl", "test")} if l else {}),
            "statut_citation": ((l or {}).get("_verif") or {}).get("statut")})
    return {"id_ref": id_ref, "champs": champs, "couverture": e.get("couverture"), "score": e.get("score"),
            "justification": verdict.get("justification", ""), "elements": elements, "lignes": lignes}
