"""Orchestration de la chaîne complète avec LangGraph.

    préparation → Agent 1 (mode section) → rattrapage → dédoublonnage → Agent 2 → export → fin

Chaque nœud appelle les modules du projet (aucune logique dupliquée) et écrit ses fichiers dans
resultats/, exactement comme les scripts. L'état du graphe ne transporte que des chemins et des
compteurs, jamais le texte de la norme ni les référentiels.

Garde-fous (règles d'implémentation, section 7) :
- `recursion_limit` passé à LangGraph ET compteur d'étapes dans l'état : le graphe est linéaire,
  mais un nœud qui dépasserait MAX_ETAPES lève une erreur au lieu de boucler ;
- budget : estimation de toute la chaîne et verifier_budget() AVANT le premier appel ; chaque
  appel repasse ensuite par appel_llm (budget, journal, cache disque, traces) ;
- reprise : toute réponse est mémorisée sur disque. Relancer la chaîne après une panne ne
  repaie que les appels qui n'avaient pas abouti.
Les étapes sont optionnelles (`etapes`) ; l'Agent 2 et l'export exigent un référentiel.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from src import agent1, agent2, config, couts, dedoublonnage, rattrapage
from src.decoupage import decouper
from src.export import exporter
from src.extraction import charger_document
from src.referentiels import charger_referentiel

ETAPES = ("agent1", "rattrapage", "dedoublonnage", "agent2", "export")
MAX_ETAPES = 12
RECURSION_LIMIT = 20


class Etat(TypedDict, total=False):
    # entrées
    document: str
    nom: str
    referentiel: str | None
    feuille: int | str
    etapes: list[str]
    effort: str
    version: str
    seuil_rattrapage: int
    dossier_resultats: str | None
    # sorties (chemins de fichiers et compteurs uniquement)
    sha_texte: str
    run_agent1: str
    consolide: str
    dedoublonne: str
    run_agent2: str
    gap_analysis: str
    export: str
    nb_etapes: int
    journal_etapes: list[dict]


def _pas(etat: Etat, nom: str, **infos) -> dict:
    n = etat.get("nb_etapes", 0) + 1
    if n > MAX_ETAPES:
        raise RuntimeError(f"Garde-fou : plus de {MAX_ETAPES} étapes, arrêt du pipeline.")
    trace = list(etat.get("journal_etapes", [])) + [
        {"etape": nom, "horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "depense_mois": round(couts.depense(), 4), **infos}]
    print(f"[pipeline] {n}. {nom} : " + ", ".join(f"{k}={v}" for k, v in infos.items()))
    return {"nb_etapes": n, "journal_etapes": trace}


def _dossier(etat: Etat) -> Path:
    return Path(etat.get("dossier_resultats") or config.DOSSIER_RESULTATS)


# ----------------------------------------------------------------------------- nœuds


def noeud_agent1(etat: Etat) -> dict:
    doc = charger_document(Path(etat["document"]))
    params = {"min_tokens": config.DECOUPAGE_MIN_TOKENS, "max_tokens": config.DECOUPAGE_MAX_TOKENS}
    sections = decouper(doc["texte"], **params)
    res = agent1.executer(texte=doc["texte"], sections=sections, mode="section", nom_document=etat["nom"],
                          sha_texte=doc["sha256_texte"], effort=etat.get("effort", agent1.EFFORT_DEFAUT),
                          params_decoupage=params, etiquette="agent1-section",
                          version=etat.get("version") or agent1.VERSION_PROMPT,
                          dossier_resultats=_dossier(etat), meta_run={"pipeline": True})
    return {"sha_texte": doc["sha256_texte"], "run_agent1": res["fichier"],
            **_pas(etat, "agent1", lignes=res["nb_lignes"], fichier=Path(res["fichier"]).name)}


def noeud_rattrapage(etat: Etat) -> dict:
    prep = rattrapage.preparer(Path(etat["run_agent1"]), Path(etat["document"]),
                               seuil=etat.get("seuil_rattrapage", 1))
    res = rattrapage.executer(prep, dossier_resultats=_dossier(etat))
    return {"consolide": str(res["consolide"]),
            **_pas(etat, "rattrapage", paragraphes_omis=res["nb_omis"], lignes_ajoutees=res["nb_nouvelles"])}


def _sans_rattrapage(etat: Etat) -> str:
    """Si le rattrapage est sauté, le consolidé est la synthèse du run, réécrite au même format."""
    prep = rattrapage.preparer(Path(etat["run_agent1"]), Path(etat["document"]), seuil=10**9)
    return str(rattrapage.executer(prep)["consolide"])  # aucun paragraphe → aucun appel


def noeud_dedoublonnage(etat: Etat) -> dict:
    entree = Path(etat.get("consolide") or _sans_rattrapage(etat))
    meta = json.loads(entree.read_text(encoding="utf-8"))
    res = dedoublonnage.executer(meta["lignes"])
    sortie = entree.with_name(entree.stem + "_dedoublonne.json")
    sortie.write_text(json.dumps({**{k: v for k, v in meta.items() if k != "lignes"}, "source": entree.name,
                                  "dedoublonnage": {k: v for k, v in res.items() if k != "lignes"},
                                  "lignes": res["lignes"]}, ensure_ascii=False, indent=1), encoding="utf-8")
    try:  # fichier de relecture humaine (même format que scripts/dedoublonner.py)
        from scripts.dedoublonner import revue_excel

        revue_excel(res, meta["lignes"], entree.with_name(entree.stem + "_dedoublonnage.xlsx"))
    except ImportError:
        pass
    s = res["stats"]
    return {"consolide": str(entree), "dedoublonne": str(sortie),
            **_pas(etat, "dedoublonnage", entree=s["nb_lignes_entree"], sortie=s["nb_lignes_sortie"])}


def _referentiel_ia(etat: Etat) -> Path:
    return Path(etat.get("dedoublonne") or etat.get("consolide") or _sans_rattrapage(etat))


def noeud_agent2(etat: Etat) -> dict:
    from src.rapport_agent2 import ecrire_gap_analysis

    ref = charger_referentiel(Path(etat["referentiel"]), etat.get("feuille", 0))
    source = _referentiel_ia(etat)
    lignes_ia = json.loads(source.read_text(encoding="utf-8"))["lignes"]
    res = agent2.executer(lignes_ia=lignes_ia, referentiel=ref, nom_document=etat["nom"], id_source=source.stem,
                          effort=etat.get("effort", agent2.EFFORT_DEFAUT), dossier_resultats=_dossier(etat))
    chemin = Path(res["fichier"])
    gap = ecrire_gap_analysis(res, ref, lignes_ia, chemin.with_name(chemin.stem + "_gap_analysis.xlsx"))
    m = res["metriques"]
    return {"run_agent2": str(chemin), "gap_analysis": str(gap),
            **_pas(etat, "agent2", couverture_stricte=m.get("couverture_stricte"),
                   couverture_large=m.get("couverture_large"), qualite=m.get("qualite_moyenne"))}


def noeud_export(etat: Etat) -> dict:
    source = _referentiel_ia(etat)
    fmt = Path(etat["referentiel"])
    sortie = source.with_name(f"{source.stem}_export_{fmt.stem}.xlsx")
    r = exporter(json.loads(source.read_text(encoding="utf-8"))["lignes"], fmt, sortie, etat.get("feuille", 0))
    return {"export": r["fichier"], **_pas(etat, "export", lignes=r["nb_lignes"], anomalies=len(r["anomalies"]))}


# ----------------------------------------------------------------------------- graphe


def _suivante(apres: str):
    """Routeur : prochaine étape demandée (et réalisable) après `apres`, sinon fin."""
    def routeur(etat: Etat) -> str:
        demandees = etat.get("etapes") or list(ETAPES)
        for e in ETAPES[ETAPES.index(apres) + 1:] if apres in ETAPES else ETAPES:
            if e in demandees and (e not in ("agent2", "export") or etat.get("referentiel")):
                return e
        return END
    return routeur


def construire_graphe():
    g = StateGraph(Etat)
    noeuds = {"agent1": noeud_agent1, "rattrapage": noeud_rattrapage, "dedoublonnage": noeud_dedoublonnage,
              "agent2": noeud_agent2, "export": noeud_export}
    for nom, f in noeuds.items():
        g.add_node(nom, f)
    cibles = {e: e for e in ETAPES} | {END: END}
    g.add_conditional_edges(START, _suivante("debut"), cibles)
    for nom in ETAPES:
        g.add_conditional_edges(nom, _suivante(nom), cibles)
    return g.compile()


def estimer(etat: Etat) -> dict:
    """Estimation prudente de toute la chaîne, AVANT tout appel (aucun appel payant).

    Agent 1 : formule du lanceur (préfixe estimé, 5 lignes par millier de tokens, 400 tokens de
    sortie par ligne extraite et enrichie). Rattrapage et dédoublonnage : plafonds tirés des coûts
    MESURÉS (≤ 0,8 $ et ≤ 0,2 $). Agent 2 : formule du lanceur (préfixe ≈ 120 tokens par ligne de
    l'IA, 700 tokens de verdict par ligne de référence, 40 par ligne supplémentaire), doublée par
    prudence. Les scripts --simulation donnent le détail étape par étape.
    """
    demandees = etat.get("etapes") or list(ETAPES)
    doc = charger_document(Path(etat["document"]))
    t = config.TARIFS[config.MODELE_EXTRACTION]
    sections = decouper(doc["texte"], min_tokens=config.DECOUPAGE_MIN_TOKENS, max_tokens=config.DECOUPAGE_MAX_TOKENS)
    prefixe = int(len(doc["texte"]) / 3.04) + 2_400
    lignes = sum(s.tokens_estimes for s in sections) / 1000 * 5.0
    appels = len(sections) + -(-int(lignes) // agent1.TAILLE_LOT_DEFAUT)
    detail = {}
    if "agent1" in demandees:
        detail["agent1"] = (prefixe * t["ecriture_cache"] + (appels - 1) * prefixe * t["lecture_cache"]
                            + lignes * 400 * t["sortie"]) / 1e6
    if "rattrapage" in demandees:
        detail["rattrapage"] = 0.8
    if "dedoublonnage" in demandees:
        detail["dedoublonnage"] = 0.2
    if "agent2" in demandees and etat.get("referentiel"):
        n_ref = len(charger_referentiel(Path(etat["referentiel"]), etat.get("feuille", 0))["lignes"])
        prefixe_ia = int(lignes) * 120  # lignes de l'IA compactées dans le préfixe
        n_supp = max(0, int(lignes) - 3 * n_ref)
        n_req = -(-n_ref // 2) + -(-n_supp // agent2.LOT_PERTINENCE)
        brut = (prefixe_ia * t["ecriture_cache"] + (n_req - 1) * prefixe_ia * t["lecture_cache"]
                + (n_ref * 700 + n_supp * 40) * t["sortie"]) / 1e6
        detail["agent2"] = 2 * brut  # ×2 : prudence (mesuré : 1,42 $ sur IFRS 9, 0,30 $ sur Sapin 2)
    return {"detail": {k: round(v, 2) for k, v in detail.items()}, "total": round(sum(detail.values()), 2),
            "sections": len(sections), "prefixe_estime": prefixe, "lignes_estimees": int(lignes)}


def executer(etat: Etat) -> Etat:
    """Vérifie le budget sur l'estimation de toute la chaîne, puis exécute le graphe."""
    est = estimer(etat)
    couts.verifier_budget(est["total"])
    return construire_graphe().invoke({**etat, "nb_etapes": 0, "journal_etapes": []},
                                      config={"recursion_limit": RECURSION_LIMIT})
