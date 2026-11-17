"""Lots batch de l'Agent 1 (extraction seule) : répétitions et campagnes sans humain devant l'écran.

Un « plan » est une liste de runs. Chaque run = (mode, sections, répétition) :
    mode       : "unique" (une requête pour le document) ou "section" (une requête par section) ;
    sections   : None pour le document complet, ou une liste d'identifiants → mini-document ;
    répétition : 1…k ; les requêtes de deux répétitions sont IDENTIQUES (même préfixe,
                 même consigne), seul le custom_id change. C'est ce qui mesure la reproductibilité.

Les requêtes sont exactement celles du mode synchrone (src/agent1.py) : mêmes consignes,
même document, même cache_control (TTL 5 min par défaut), même effort, aucun paramètre
d'échantillonnage. Les résultats sont réécrits au format des runs synchrones, si bien que
scripts/essoufflement.py, reanalyser.py, etc. s'appliquent tels quels.

Comptabilité : le coût de chaque résultat est journalisé (batch=True, remise de 50 %) à la
récupération, une seule fois par custom_id (registre dans le manifeste).
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src import agent1, appel_llm, config, couts
from src.extraction import empreinte
from src.schema import VERSION_SCHEMA, LigneExtraite, analyser_sortie
from src.verif_citations import IndexTexte, verifier_ligne

_CUSTOM_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def libelle_sections(ids: list[str] | None) -> str:
    return "complet" if not ids else (ids[0] if len(ids) == 1 else f"{ids[0]}-{ids[-1]}").lower()


def plage(sections: list, texte_plage: str) -> list[str] | None:
    """« complet » → None ; « S11-S27 » → [S11…S27] ; « S01,S04 » → [S01, S04]."""
    if texte_plage in ("complet", "tout", ""):
        return None
    ids = [s.id for s in sections]
    if "-" in texte_plage and "," not in texte_plage:
        a, b = texte_plage.upper().split("-")
        return ids[ids.index(a): ids.index(b) + 1]
    choix = [x.strip().upper() for x in texte_plage.split(",")]
    inconnus = [x for x in choix if x not in ids]
    if inconnus:
        raise ValueError(f"sections inconnues : {inconnus}")
    return choix


def construire(*, texte: str, sections: list, plan: list[dict], nom_document: str, langue: str | None = None,
               modele: str | None = None, effort: str | None = agent1.EFFORT_DEFAUT,
               max_tokens: int = agent1.MAX_TOKENS_DEFAUT, version: str = agent1.VERSION_PROMPT,
               params_decoupage: dict | None = None, ttl: str = "5m") -> tuple[list[dict], list[dict]]:
    """Renvoie (requêtes batch, description des runs). `plan` : [{mode, ids, k}].

    ttl « 1h » : autorisé UNIQUEMENT pour une réplication en batch où chaque préfixe
    (document) est partagé par au moins 20 requêtes (contrainte du cadrage, section 5).
    """
    if ttl not in ("5m", "1h"):
        raise ValueError("ttl : '5m' ou '1h'")
    modele = modele or config.MODELE_EXTRACTION
    config.verifier_modele(modele)
    langue = langue or agent1.detecter_langue(texte)
    requetes, runs = [], []
    for item in plan:
        mode, ids, k = item["mode"], item.get("ids"), item["k"]
        if mode not in ("unique", "section"):
            raise ValueError("mode batch : 'unique' ou 'section'")
        if ids:
            t, secs = agent1.mini_document(texte, sections, ids)
        else:
            t, secs = texte, sections
        systeme = agent1.construire_systeme(t, nom_document, langue, version)
        if ttl == "1h":
            systeme[-1]["cache_control"] = {"type": "ephemeral", "ttl": "1h"}
        if mode == "unique":
            taches = [("U", agent1.charger_prompt("agent1_unique", version).format(prefixe_id="U"))]
        else:
            taches = [(s.id, agent1.consigne_section(t, secs, j, version)) for j, s in enumerate(secs)]
        lib = libelle_sections(ids)
        for rep in range(1, k + 1):
            cle = f"{mode[0]}-{lib}-r{rep}-{version}"
            runs.append({"cle": cle, "mode": mode, "ids": ids, "rep": rep, "sha256_texte": empreinte(t),
                         "sections": [{"id": s.id, "titre": s.titre, "debut": s.debut, "fin": s.fin} for s in secs],
                         "taches": [x for x, _ in taches]})
            for id_tache, consigne in taches:
                custom_id = f"{cle}-{id_tache}"
                if not _CUSTOM_ID.match(custom_id):
                    raise ValueError(f"custom_id invalide : {custom_id}")
                params = {"model": modele, "max_tokens": max_tokens, "system": systeme,
                          "messages": [{"role": "user", "content": consigne}]}
                if effort and not modele.startswith("claude-haiku"):
                    params["output_config"] = {"effort": effort}
                assert not any(p in params for p in appel_llm.PARAMETRES_INTERDITS)
                requetes.append({"custom_id": custom_id, "params": params})
    if ttl == "1h":
        par_prefixe = {}
        for r in runs:
            par_prefixe[r["sha256_texte"]] = par_prefixe.get(r["sha256_texte"], 0) + len(r["taches"])
        if min(par_prefixe.values()) < 20:
            raise ValueError("TTL 1h interdit : chaque préfixe doit servir au moins 20 requêtes du lot "
                             f"(ici {par_prefixe}). Garder le TTL de 5 minutes.")
    entete_commune = {"modele": modele, "effort": effort, "max_tokens": max_tokens, "version_prompt": version,
                      "schema": VERSION_SCHEMA, "ttl": ttl, "nom_document": nom_document, "langue": langue,
                      "params_decoupage": params_decoupage or {}, "enrichissement": False}
    for r in runs:
        r["entete"] = entete_commune
    return requetes, runs


def estimation(requetes: list[dict], ttl: str = "5m") -> dict:
    """Coût en batch : borne haute (chaque requête écrit tout le préfixe et sort au plafond)
    et part « écriture du préfixe » seule (la sortie réelle dépend de ce que le modèle produit)."""
    total_max, ecriture = 0.0, 0.0
    for r in requetes:
        p = r["params"]
        t = config.TARIFS[p["model"]]
        tarif = t["ecriture_cache"] if ttl == "5m" else t["entree"] * config.MULTIPLICATEUR_ECRITURE_1H
        entree = int(len(json.dumps(p["system"], ensure_ascii=False) + json.dumps(p["messages"], ensure_ascii=False)) / 3.0)
        ecriture += entree * tarif / 1e6
        total_max += (entree * tarif + p["max_tokens"] * t["sortie"]) / 1e6
    return {"nb_requetes": len(requetes), "max_usd_batch": total_max * config.REMISE_BATCH,
            "ecriture_usd_batch": ecriture * config.REMISE_BATCH}


def amorcer(requetes: list[dict], client=None, journal=None) -> list[dict]:
    """Un appel synchrone minimal par préfixe distinct, juste avant la soumission, pour que
    le cache serveur soit déjà écrit quand le lot démarre (règle : amorçage avant tout lot).
    Jamais mémorisé sur disque : l'amorçage doit réellement atteindre l'API."""
    vus, sorties = set(), []
    for r in requetes:
        p = r["params"]
        cle = json.dumps(p["system"], ensure_ascii=False, sort_keys=True)
        if cle in vus:
            continue
        vus.add(cle)
        ttl = p["system"][-1].get("cache_control", {}).get("ttl", "5m")
        requete = {"model": p["model"], "system": p["system"], "max_tokens": 16,
                   "messages": [{"role": "user", "content": "Réponds seulement : OK."}]}
        if "output_config" in p:
            requete["extra_body"] = {"output_config": p["output_config"]}
        couts.verifier_budget(appel_llm.estimation_pessimiste(p["model"], p["system"], requete["messages"], 16)
                              * (1.6 if ttl == "1h" else 1.0), chemin=journal)
        if client is None:
            reponse = appel_llm._envoyer(**requete)
        else:
            reponse = client.messages.create(**requete)
        couts.journaliser(p["model"], reponse.usage, "agent1-amorcage", ttl=ttl,
                          meta={"custom_id_exemple": r["custom_id"]}, chemin=journal)
        sorties.append({"custom_id_exemple": r["custom_id"], "ttl": ttl,
                        "cache_ecrit": getattr(reponse.usage, "cache_creation_input_tokens", 0),
                        "cache_lu": getattr(reponse.usage, "cache_read_input_tokens", 0)})
    return sorties


def soumettre(requetes: list[dict], runs: list[dict], max_usd: float, dossier: Path | None = None,
              client=None) -> Path:
    """Vérifie le budget (borne haute), crée le lot, écrit le manifeste. Renvoie son chemin."""
    couts.verifier_budget(max_usd)
    client = client or appel_llm._client()
    lot = client.messages.batches.create(requests=requetes)
    dossier = Path(dossier or config.DOSSIER_RESULTATS)
    dossier.mkdir(parents=True, exist_ok=True)
    manifeste = dossier / f"batch-{lot.id}.json"
    manifeste.write_text(json.dumps({
        "batch_id": lot.id, "cree": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "custom_ids": [r["custom_id"] for r in requetes], "runs": runs, "journalises": [], "fichiers": {},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifeste


def etat(batch_id: str, client=None):
    client = client or appel_llm._client()
    return client.messages.batches.retrieve(batch_id)


def recuperer(manifeste: Path, texte: str, sections: list, client=None, journal=None,
              dossier: Path | None = None) -> dict:
    """Lot terminé → un fichier de run par répétition, au format synchrone ; coûts journalisés une fois."""
    client = client or appel_llm._client()
    man = json.loads(Path(manifeste).read_text(encoding="utf-8"))
    lot = client.messages.batches.retrieve(man["batch_id"])
    if lot.processing_status != "ended":
        return {"termine": False, "etat": lot.processing_status, "compteurs": _compteurs(lot)}

    resultats = {}
    for res in client.messages.batches.results(man["batch_id"]):
        resultats[res.custom_id] = res
    dossier = Path(dossier or config.DOSSIER_RESULTATS)
    deja = set(man["journalises"])
    bilan = {"termine": True, "runs": [], "erreurs": []}
    for run in man["runs"]:
        if ids := run["ids"]:
            t, _ = agent1.mini_document(texte, sections, ids)
        else:
            t = texte
        if empreinte(t) != run["sha256_texte"]:
            raise ValueError(f"{run['cle']} : le document ne correspond pas à celui du lot (empreintes)")
        index = IndexTexte(t)
        id_run = man["fichiers"].get(run["cle"], {}).get("id_run") or \
            f"{run['mode']}-{run['sha256_texte'][:8]}-{run['entete']['version_prompt']}-{run['cle']}-{man['batch_id'][-8:]}"
        enreg = [{"type": "entete", "id_run": id_run, "mode": run["mode"], "sha256_texte": run["sha256_texte"],
                  "sections": run["sections"], "taches": run["taches"], "batch_id": man["batch_id"],
                  "cle": run["cle"], "repetition": run["rep"], "ids_mini": run["ids"], **run["entete"]}]
        toutes = []
        for id_tache in run["taches"]:
            cid = f"{run['cle']}-{id_tache}"
            res = resultats.get(cid)
            if res is None or res.result.type != "succeeded":
                bilan["erreurs"].append({"custom_id": cid, "type": None if res is None else res.result.type})
                enreg.append({"type": "extraction", "tache": id_tache, "erreur": None if res is None else res.result.type,
                              "lignes": [], "nb_lignes": 0})
                continue
            msg = res.result.message
            if cid not in deja:
                couts.journaliser(msg.model, msg.usage, f"agent1-{run['mode']}{'-mini' if run['ids'] else ''}-extraction",
                                  batch=True, ttl=run["entete"]["ttl"], meta={"batch_id": man["batch_id"], "custom_id": cid,
                                                    "stop_reason": msg.stop_reason, "id_run": id_run},
                                  chemin=journal)
                deja.add(cid)
            brut = "".join(b.text for b in msg.content if b.type == "text")
            lignes, rejets = analyser_sortie(brut, LigneExtraite)
            for l in lignes:
                l["_verif"] = verifier_ligne(index, l)
                l["_tache"] = id_tache
            toutes += lignes
            usage = msg.usage.model_dump() if hasattr(msg.usage, "model_dump") else dict(msg.usage)
            enreg.append({"type": "extraction", "tache": id_tache, "stop_reason": msg.stop_reason,
                          "tronquee": msg.stop_reason == "max_tokens", "usage": usage, "nb_lignes": len(lignes),
                          "rejets": rejets, "lignes": lignes, "reponse_brute": brut})
        enreg.append({"type": "synthese", "nb_lignes": len(toutes), "non_enrichies": [], "lignes": toutes})
        chemin = dossier / f"{id_run}.jsonl"
        chemin.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in enreg) + "\n", encoding="utf-8")
        man["fichiers"][run["cle"]] = {"id_run": id_run, "fichier": chemin.name}
        valides = sum((l["_verif"] or {}).get("statut") == "valide" for l in toutes)
        bilan["runs"].append({"cle": run["cle"], "fichier": str(chemin), "nb_lignes": len(toutes),
                              "valides": valides})
        # registre mis à jour après CHAQUE run : une interruption ne fait jamais journaliser deux fois
        man["journalises"] = sorted(deja)
        Path(manifeste).write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    return bilan


def _compteurs(lot) -> dict:
    c = getattr(lot, "request_counts", None)
    return c.model_dump() if hasattr(c, "model_dump") else (dict(c) if c else {})
