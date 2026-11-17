"""Dédoublonnage du référentiel produit par l'Agent 1 (décision 4.5).

Principe « la règle décide, le LLM extrait », appliqué en trois temps :
1. DÉTERMINISTE — doublons exacts (même citation ET même obligation après normalisation) :
   fusionnés sans LLM.
2. DÉTERMINISTE — rapprochement de candidats : deux lignes sont candidates si leurs citations
   se chevauchent dans le texte source, si elles portent sur le même paragraphe avec des
   obligations proches, ou si leurs obligations sont très proches (trigrammes de caractères).
   VETO (v2) : deux lignes produites par la MÊME tâche (même section, même passe) ne sont
   jamais candidates, sauf citations chevauchantes. Une tâche traite chaque passage une fois :
   si le modèle a listé deux lignes, c'est qu'il voyait deux dispositions. Les vrais doublons
   viennent d'une autre tâche (règle répétée ailleurs dans le texte, rattrapage).
   Les candidats forment des grappes (composantes connexes), de taille bornée.
3. LLM — à l'intérieur de chaque grappe, le modèle juge CHAQUE PAIRE (doublon oui/non, et la
   différence s'il y en a une). Le code ne fusionne que des groupes dont toutes les paires sont
   jugées doublons (cliques) : pas de fusion par chaînage. Il ne réécrit rien, rejette tout
   identifiant inconnu et choisit lui-même la ligne conservée.

Mesure du 26/10 (relecture des 20 fusions de la v1, Haiku) : environ la moitié fusionnait des
dispositions parallèles (deux modifications successives, trois cas distincts d'une même
mesure d'allègement, trois ordonnances différentes). D'où, en v2 : le veto « même tâche »,
le jugement par paire et Sonnet par défaut (coût négligeable : quelques centimes).

Aucune ligne n'est perdue : la ligne conservée garde la trace des lignes fusionnées
(`_doublons` : id, ref, cit), si bien que l'Agent 2 peut ramener tout identifiant fusionné
à son représentant.
"""

import json
import re
import unicodedata
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from src import agent1, appel_llm, config

VERSION_PROMPT = "v2"
SEUIL_OBL = 0.45  # Jaccard des trigrammes de l'obligation, toutes positions confondues
SEUIL_OBL_MEME_PARAGRAPHE = 0.30  # plus permissif quand les deux lignes visent le même paragraphe
TAILLE_MAX_GRAPPE = 6
GRAPPES_PAR_REQUETE = 12
MAX_TOKENS = 8_000


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"[«»“”\"'’`]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _trigrammes(s: str) -> set:
    s = _norm(s)
    return {s[i: i + 3] for i in range(len(s) - 2)}


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def _verif(l: dict) -> dict:
    return l.get("_verif") or {}


def _tache(l: dict):
    """Tâche qui a produit la ligne : (section traitée, passe de rattrapage ou non).
    Sans information de tâche, chaque ligne est sa propre tâche (aucun veto)."""
    return (l.get("_tache"), bool(l.get("_rattrapage"))) if l.get("_tache") else ("_seule", l["id"])


# ----------------------------------------------------------------------- étape 1


def doublons_exacts(lignes: list[dict]) -> list[list[str]]:
    """Groupes de lignes à citation ET obligation identiques après normalisation."""
    groupes = {}
    for l in lignes:
        groupes.setdefault((_norm(l.get("cit", "")), _norm(l.get("obl", ""))), []).append(l["id"])
    return [g for g in groupes.values() if len(g) > 1]


# ----------------------------------------------------------------------- étape 2


def candidats(lignes: list[dict], seuil: float = SEUIL_OBL,
              seuil_paragraphe: float = SEUIL_OBL_MEME_PARAGRAPHE) -> list[dict]:
    """Paires candidates, avec le motif du rapprochement et la similarité des obligations."""
    tri = {l["id"]: _trigrammes(l.get("obl", "")) for l in lignes}
    paires = []
    for a, b in combinations(lignes, 2):
        va, vb = _verif(a), _verif(b)
        chevauche = (va.get("debut") is not None and vb.get("debut") is not None
                     and va["debut"] < vb["fin"] and vb["debut"] < va["fin"])
        if _tache(a) == _tache(b) and not chevauche:
            continue  # veto « même tâche » (voir l'en-tête)
        meme_par = bool(va.get("paragraphe")) and va.get("paragraphe") == vb.get("paragraphe")
        sim = _jaccard(tri[a["id"]], tri[b["id"]])
        motifs = [m for m, ok in (("citations_chevauchantes", chevauche),
                                  ("meme_paragraphe", meme_par and sim >= seuil_paragraphe),
                                  ("obligations_proches", sim >= seuil)) if ok]
        if motifs:
            paires.append({"a": a["id"], "b": b["id"], "motifs": motifs, "similarite": round(sim, 3)})
    return paires


def grappes(lignes: list[dict], paires: list[dict], taille_max: int = TAILLE_MAX_GRAPPE) -> list[list[str]]:
    """Composantes connexes des paires candidates, découpées si elles dépassent taille_max.

    Une grappe trop grande (chaînage de ressemblances) est découpée en morceaux consécutifs
    dans l'ordre du texte ; les paires coupées sont comptées par l'appelant.
    """
    parent = {l["id"]: l["id"] for l in lignes}

    def racine(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in paires:
        ra, rb = racine(p["a"]), racine(p["b"])
        if ra != rb:
            parent[rb] = ra
    composantes = {}
    for l in lignes:
        composantes.setdefault(racine(l["id"]), []).append(l)
    sortie = []
    for comp in composantes.values():
        if len(comp) < 2:
            continue
        comp.sort(key=lambda l: (_verif(l).get("debut") is None, _verif(l).get("debut") or 0, l["id"]))
        ids = [l["id"] for l in comp]
        sortie += [ids[i: i + taille_max] for i in range(0, len(ids), taille_max) if len(ids[i: i + taille_max]) > 1]
    return sortie


# ----------------------------------------------------------------------- étape 3


def _ligne_compacte(l: dict) -> str:
    return json.dumps({"id": l["id"], "ref": l.get("ref"), "obl": l.get("obl"), "cit": l.get("cit")},
                      ensure_ascii=False)


def consigne(lots: list[tuple[str, list[dict]]], version: str = VERSION_PROMPT) -> str:
    blocs = "\n\n".join(f'<grappe id="{g}">\n' + "\n".join(_ligne_compacte(l) for l in ls) + "\n</grappe>"
                        for g, ls in lots)
    return agent1.charger_prompt("dedoublonnage", version).format(nb_grappes=len(lots), grappes=blocs)


def _cliques(ids: list[str], vrais: set[frozenset]) -> list[list[str]]:
    """Groupes où TOUTES les paires sont jugées doublons, construits gloutonnement dans l'ordre."""
    groupes, pris = [], set()
    for i in ids:
        if i in pris:
            continue
        groupe = [i]
        for j in ids:
            if j != i and j not in pris and all(frozenset((j, k)) in vrais for k in groupe):
                groupe.append(j)
        if len(groupe) > 1:
            groupes.append(groupe)
            pris |= set(groupe)
    return groupes


def lire_verdicts(brut: str, attendues: dict[str, list[str]]) -> tuple[dict, list[dict]]:
    """Valide la réponse (jugements par paire) : renvoie ({grappe: {groupes, paires}}, anomalies).
    Rien d'inventé ne passe ; une paire non jugée vaut « pas doublon »."""
    anomalies = []
    try:
        debut, fin = brut.find("{"), brut.rfind("}")
        entrees = json.loads(brut[debut: fin + 1]).get("grappes", [])
    except (json.JSONDecodeError, AttributeError) as e:
        return {}, [{"raison": f"réponse illisible ({e.__class__.__name__})", "extrait": brut[:200]}]
    verdicts = {}
    for e in entrees:
        g = e.get("grappe")
        if g not in attendues:
            anomalies.append({"raison": "grappe inconnue", "grappe": g})
            continue
        membres, vrais, paires = set(attendues[g]), set(), []
        for p in e.get("paires") or []:
            a, b = p.get("a"), p.get("b")
            if a not in membres or b not in membres or a == b:
                anomalies.append({"raison": "paire hors grappe ignorée", "grappe": g, "paire": [a, b]})
                continue
            doublon = p.get("doublon") is True
            paires.append({"a": a, "b": b, "doublon": doublon, "difference": p.get("difference", "")})
            if doublon:
                vrais.add(frozenset((a, b)))
        groupes = _cliques(attendues[g], vrais)
        raison = "; ".join(f"{p['a']}={p['b']}" for p in paires if p["doublon"]) or "aucun doublon"
        verdicts[g] = {"groupes": groupes, "paires": paires, "raison": raison}
    for g in attendues:
        if g not in verdicts:
            anomalies.append({"raison": "grappe sans verdict (conservée telle quelle)", "grappe": g})
    return verdicts, anomalies


def representant(groupe: list[dict]) -> dict:
    """Choix DÉTERMINISTE de la ligne conservée : citation valide d'abord, puis ligne issue de
    l'extraction (pas du rattrapage), puis référence la plus précise, puis la première du texte."""
    def cle(l):
        v = _verif(l)
        return (v.get("statut") != "valide", bool(l.get("_rattrapage")), -len(l.get("ref") or ""),
                v.get("debut") if v.get("debut") is not None else 10**12, l["id"])
    return min(groupe, key=cle)


def appliquer(lignes: list[dict], groupes: list[tuple[list[str], str, str]]) -> tuple[list[dict], list[dict]]:
    """Fusionne les groupes (ids, origine, raison). Renvoie (lignes conservées, journal des fusions)."""
    par_id = {l["id"]: l for l in lignes}
    absorbe, fusions = {}, []
    for ids, origine, raison in groupes:
        ids = [i for i in ids if i in par_id and i not in absorbe]
        if len(ids) < 2:
            continue
        rep = representant([par_id[i] for i in ids])
        autres = [i for i in ids if i != rep["id"]]
        for i in autres:
            absorbe[i] = rep["id"]
        fusions.append({"representant": rep["id"], "fusionnes": autres, "origine": origine, "raison": raison})
    conservees = []
    for l in lignes:
        if l["id"] in absorbe:
            continue
        # traces cumulées : celles déjà portées par la ligne, les lignes absorbées et LEURS traces
        doublons = list(l.get("_doublons") or [])
        for f in fusions:
            if f["representant"] == l["id"]:
                for i in f["fusionnes"]:
                    doublons.append({"id": i, "ref": par_id[i].get("ref"), "cit": par_id[i].get("cit")})
                    doublons += par_id[i].get("_doublons") or []
        conservees.append({**l, "_doublons": doublons} if doublons else l)
    return conservees, fusions


def executer(lignes: list[dict], *, modele: str | None = None, version: str = VERSION_PROMPT,
             grappes_par_requete: int = GRAPPES_PAR_REQUETE, etiquette: str = "dedoublonnage",
             journal=None, dossier_cache=None) -> dict:
    """Dédoublonne une liste de lignes au format pivot. Renvoie lignes, fusions et statistiques."""
    modele = modele or config.MODELE_EXTRACTION
    exacts = doublons_exacts(lignes)
    lignes_1, fusions_1 = appliquer(lignes, [(g, "exact", "citation et obligation identiques") for g in exacts])

    paires = candidats(lignes_1)
    gr = grappes(lignes_1, paires)
    par_id = {l["id"]: l for l in lignes_1}
    nommees = [(f"G{k:03d}", ids) for k, ids in enumerate(gr, 1)]
    attendues = {g: list(ids) for g, ids in nommees}
    verdicts, anomalies, appels = {}, [], []
    for i in range(0, len(nommees), grappes_par_requete):
        lot = [(g, [par_id[x] for x in ids]) for g, ids in nommees[i: i + grappes_par_requete]]
        rep = appel_llm.appeler(modele=modele, systeme=[{"type": "text", "text": "Tu regroupes des doublons."}],
                                messages=[{"role": "user", "content": consigne(lot, version)}],
                                etiquette=etiquette, version_prompt=f"dedoublonnage-{version}",
                                max_tokens=MAX_TOKENS, effort=agent1.EFFORT_DEFAUT,
                                meta={"lot": i // grappes_par_requete + 1, "nb_grappes": len(lot)},
                                journal=journal, dossier_cache=dossier_cache)
        brut = appel_llm.texte_de_reponse(rep)
        v, a = lire_verdicts(brut, {g: attendues[g] for g, _ in lot})
        verdicts.update(v)
        anomalies += a
        appels.append({"lot": i // grappes_par_requete + 1, "grappes": [g for g, _ in lot],
                       "stop_reason": rep.get("stop_reason"), "usage": rep.get("usage"),
                       "vient_du_cache_disque": rep["_vient_du_cache"], "reponse_brute": brut})
    groupes_llm = [(grp, g, verdicts[g]["raison"]) for g, _ in nommees if g in verdicts
                   for grp in verdicts[g]["groupes"]]
    finales, fusions_2 = appliquer(lignes_1, groupes_llm)

    stats = {"nb_lignes_entree": len(lignes), "nb_lignes_sortie": len(finales),
             "doublons_exacts": sum(len(f["fusionnes"]) for f in fusions_1),
             "paires_candidates": len(paires), "grappes": len(gr), "lignes_en_grappe": sum(len(g) for g in gr),
             "fusions_llm": len(fusions_2), "lignes_absorbees_llm": sum(len(f["fusionnes"]) for f in fusions_2),
             "anomalies": len(anomalies), "appels": len(appels)}
    return {"lignes": finales, "fusions": fusions_1 + fusions_2, "grappes": dict(nommees),
            "verdicts": verdicts, "anomalies": anomalies, "appels": appels, "stats": stats,
            "modele": modele, "version_prompt": version,
            "horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def table_de_correspondance(fusions: list[dict]) -> dict[str, str]:
    """id fusionné → id conservé en fin de chaîne (pour ramener un verdict de l'Agent 2 à son représentant)."""
    direct = {i: f["representant"] for f in fusions for i in f["fusionnes"]}
    final = {}
    for i in direct:
        j = direct[i]
        while j in direct:
            j = direct[j]
        final[i] = j
    return final
