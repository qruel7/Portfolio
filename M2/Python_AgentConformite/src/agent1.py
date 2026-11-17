"""Agent 1 : du texte réglementaire au référentiel pivot, en CAG, en deux temps.

Structure de chaque requête, du plus stable au plus variable (décision 4.6) :
    système[0] = consignes communes (fichier versionné, variables injectées)
    système[1] = <document>…</document>   ← point de cache_control (dernier bloc stable)
    message    = « TÂCHE : EXTRACTION … » ou « TÂCHE : ENRICHISSEMENT … » (seule partie variable)
Le préfixe étant identique pour les deux tâches, une seule écriture de cache sert aux deux.

Étape 1, extraction (ref, cit, dom, obl, typ, crit), en deux modes (décision 4.5) :
    « section » : une requête par section, le document entier restant en préfixe ;
    « unique »  : une seule requête pour tout le document (témoin de l'essoufflement).
Étape 2, enrichissement (ctrl, test), par lots de lignes extraites.
"""

import json
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path

from src import appel_llm, config
from src.decoupage import Section
from src.schema import VERSION_SCHEMA, Enrichissement, LigneExtraite, analyser_sortie, fusionner
from src.verif_citations import IndexTexte, verifier_ligne

DOSSIER_PROMPTS = Path(__file__).resolve().parent / "prompts"
VERSION_PROMPT = "v3"
EFFORT_DEFAUT = "medium"  # mesuré le 22/10 sur S13 : même couverture que « high » pour 44 % du coût
MAX_TOKENS_DEFAUT = 32_000
TAILLE_LOT_DEFAUT = 20  # lignes par requête d'enrichissement
MAX_TOKENS_ENRICHISSEMENT = 8_000  # 20 lignes × ~180 tokens ≈ 3 600 : marge ×2


def charger_prompt(nom: str, version: str = VERSION_PROMPT) -> str:
    """Lit src/prompts/<nom>_<version>.txt sans l'en-tête de commentaires (# …) du début."""
    lignes = (DOSSIER_PROMPTS / f"{nom}_{version}.txt").read_text(encoding="utf-8").splitlines()
    while lignes and (lignes[0].startswith("#") or not lignes[0].strip()):
        lignes.pop(0)
    return "\n".join(lignes).strip() + "\n"


def detecter_langue(texte: str) -> str:
    """Heuristique simple et générique sur les mots outils les plus fréquents."""
    mots = re.findall(r"[a-zà-ÿ']+", texte[:200_000].lower())
    fr = sum(mots.count(w) for w in ("le", "la", "les", "des", "est", "une", "dans"))
    en = sum(mots.count(w) for w in ("the", "of", "and", "is", "an", "shall", "in"))
    return "français" if fr > en else "anglais"


def construire_systeme(texte: str, nom_document: str, langue: str, version: str = VERSION_PROMPT) -> list:
    consignes = charger_prompt("agent1_systeme", version).format(nom_document=nom_document, langue=langue)
    return [
        {"type": "text", "text": consignes},
        {
            "type": "text",
            "text": f"<document>\n{texte}\n</document>",
            "cache_control": {"type": "ephemeral"},  # TTL par défaut : 5 minutes
        },
    ]


def _amorce(texte: str, n: int = 160) -> str:
    """Début d'un passage sur une ligne, pour désigner une zone sans ambiguïté."""
    return re.sub(r"\s+", " ", texte[:n]).strip()


def consigne_section(texte: str, sections: list[Section], k: int, version: str = VERSION_PROMPT) -> str:
    s = sections[k]
    fin = _amorce(sections[k + 1].texte(texte)) if k + 1 < len(sections) else "(fin du document)"
    return charger_prompt("agent1_section", version).format(
        id_section=s.id,
        titre_section=s.titre,
        debut_section=_amorce(s.texte(texte)),
        fin_section=fin,
        prefixe_id=s.id,
    )


def consigne_enrichissement(lot: list[dict], version: str = VERSION_PROMPT) -> str:
    exigences = "\n".join(
        json.dumps({"id": l["id"], "ref": l["ref"], "obl": l["obl"]}, ensure_ascii=False) for l in lot
    )
    return charger_prompt("agent1_enrichissement", version).format(nb=len(lot), exigences=exigences)


def consigne_rattrapage(texte: str, omis: list[dict], prefixe_id: str, version: str = VERSION_PROMPT) -> str:
    """Consigne ciblée sur des paragraphes omis (liste de dicts de src.couverture.paragraphes_omis)."""
    liste = "\n".join(f"- {o['paragraphe']} : « {_amorce(texte[o['debut']:o['fin']], 120)} »" for o in omis)
    return charger_prompt("agent1_rattrapage", version).format(liste_paragraphes=liste, prefixe_id=prefixe_id)


def mini_document(texte: str, sections: list[Section], ids: list[str]) -> tuple[str, list[Section]]:
    """Document réduit aux sections choisies (mise au point bon marché, ou préfixes de longueur croissante)."""
    morceaux, nouvelles, pos = [], [], 0
    for s in sections:
        if s.id in ids:
            t = s.texte(texte)
            morceaux.append(t)
            nouvelles.append(Section(s.id, s.titre, pos, pos + len(t), s.tokens_estimes, s.cles))
            pos += len(t)
    return "".join(morceaux), nouvelles


class _Run:
    """Écriture du fichier de résultats au fil de l'eau (jamais de résultat payé perdu)."""

    def __init__(self, dossier, id_run, entete):
        dossier = Path(dossier or config.DOSSIER_RESULTATS)
        dossier.mkdir(parents=True, exist_ok=True)
        self.chemin = dossier / f"{id_run}.jsonl"
        self.ecrire({"type": "entete", **entete})

    def ecrire(self, enregistrement: dict):
        with self.chemin.open("a", encoding="utf-8") as f:
            f.write(json.dumps(enregistrement, ensure_ascii=False) + "\n")


def executer(
    *,
    texte: str,
    sections: list[Section],
    mode: str,
    nom_document: str,
    sha_texte: str,
    ids: list[str] | None = None,
    langue: str | None = None,
    modele: str | None = None,
    max_tokens: int = MAX_TOKENS_DEFAUT,
    effort: str | None = EFFORT_DEFAUT,
    enrichir: bool = True,
    taille_lot: int = TAILLE_LOT_DEFAUT,
    version: str = VERSION_PROMPT,
    etiquette: str | None = None,
    params_decoupage: dict | None = None,
    taches: list[tuple[str, str]] | None = None,
    meta_run: dict | None = None,
    dossier_resultats: Path | None = None,
    journal=None,
    dossier_cache=None,
) -> dict:
    """Exécute l'extraction puis (par défaut) l'enrichissement, et enregistre tout sur disque."""
    if mode not in ("section", "unique", "rattrapage"):
        raise ValueError("mode = 'section', 'unique' ou 'rattrapage'")
    if mode == "rattrapage" and not taches:
        raise ValueError("le mode 'rattrapage' exige des tâches explicites")
    modele = modele or config.MODELE_EXTRACTION
    langue = langue or detecter_langue(texte)
    etiquette = etiquette or f"agent1-{mode}"
    systeme = construire_systeme(texte, nom_document, langue, version)
    index = IndexTexte(texte)

    if taches:
        pass  # tâches fournies par l'appelant (rattrapage)
    elif mode == "unique":
        taches = [("U", charger_prompt("agent1_unique", version).format(prefixe_id="U"))]
    else:
        choix = [k for k, s in enumerate(sections) if ids is None or s.id in ids]
        taches = [(sections[k].id, consigne_section(texte, sections, k, version)) for k in choix]

    horodatage = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    id_run = f"{mode}-{sha_texte[:8]}-{version}-{horodatage}"
    entete = {
        "id_run": id_run, "mode": mode, "modele": modele, "effort": effort,
        "max_tokens": max_tokens, "version_prompt": version, "schema": VERSION_SCHEMA,
        "ttl": "5m", "sha256_texte": sha_texte, "nom_document": nom_document, "langue": langue,
        "sections": [{"id": s.id, "titre": s.titre, "debut": s.debut, "fin": s.fin} for s in sections],
        "params_decoupage": params_decoupage or {}, "taches": [t for t, _ in taches],
        "enrichissement": enrichir, "taille_lot": taille_lot,
        "max_tokens_enrichissement": MAX_TOKENS_ENRICHISSEMENT,
        **(meta_run or {}),
    }
    try:
        import anthropic

        entete["version_sdk"] = anthropic.__version__
    except ImportError:
        pass
    run = _Run(dossier_resultats, id_run, entete)
    commun = dict(modele=modele, systeme=systeme, version_prompt=version, max_tokens=max_tokens,
                  effort=effort, journal=journal, dossier_cache=dossier_cache)
    nb_appels = 0

    def _appel(consigne, etiq, meta, plafond=None):
        nonlocal nb_appels
        params = {**commun, "max_tokens": plafond or max_tokens}
        reponse = appel_llm.appeler(messages=[{"role": "user", "content": consigne}],
                                    etiquette=etiq, meta={"id_run": id_run, **meta}, **params)
        usage = reponse.get("usage", {})
        if nb_appels >= 1 and not reponse["_vient_du_cache"] and not usage.get("cache_read_input_tokens"):
            warnings.warn(f"{meta} : aucune lecture de cache serveur. Le préfixe a-t-il changé ?")
        nb_appels += 1
        return reponse, usage

    # ---- Étape 1 : extraction ----------------------------------------------------------
    extraites = []
    for id_tache, consigne in taches:
        reponse, usage = _appel(consigne, f"{etiquette}-extraction", {"etape": "extraction", "tache": id_tache})
        brut = appel_llm.texte_de_reponse(reponse)
        lignes, rejets = analyser_sortie(brut, LigneExtraite)
        for l in lignes:
            l["_verif"] = verifier_ligne(index, l)
            l["_tache"] = id_tache
        extraites += lignes
        run.ecrire({"type": "extraction", "tache": id_tache, "stop_reason": reponse.get("stop_reason"),
                    "tronquee": reponse.get("stop_reason") == "max_tokens", "usage": usage,
                    "vient_du_cache_disque": reponse["_vient_du_cache"], "nb_lignes": len(lignes),
                    "rejets": rejets, "lignes": lignes, "reponse_brute": brut})
        statuts = [l["_verif"]["statut"] for l in lignes]
        print(f"  extraction {id_tache}: {len(lignes)} lignes, {statuts.count('valide')} citations valides, "
              f"{len(rejets)} rejets, stop={reponse.get('stop_reason')}, sortie {usage.get('output_tokens')}"
              f"{' (disque)' if reponse['_vient_du_cache'] else ''}")

    # ---- Étape 2 : enrichissement -------------------------------------------------------
    enrichissements = []
    if enrichir and extraites:
        lots = [extraites[i : i + taille_lot] for i in range(0, len(extraites), taille_lot)]
        for n, lot in enumerate(lots, 1):
            reponse, usage = _appel(consigne_enrichissement(lot, version), f"{etiquette}-enrichissement",
                                    {"etape": "enrichissement", "lot": n}, MAX_TOKENS_ENRICHISSEMENT)
            brut = appel_llm.texte_de_reponse(reponse)
            objets, rejets = analyser_sortie(brut, Enrichissement)
            attendus = {l["id"] for l in lot}
            objets = [o for o in objets if o["id"] in attendus]
            enrichissements += objets
            run.ecrire({"type": "enrichissement", "lot": n, "ids": sorted(attendus),
                        "stop_reason": reponse.get("stop_reason"), "usage": usage,
                        "vient_du_cache_disque": reponse["_vient_du_cache"], "nb_enrichis": len(objets),
                        "rejets": rejets, "enrichissements": objets, "reponse_brute": brut})
            print(f"  enrichissement lot {n}/{len(lots)}: {len(objets)}/{len(lot)} lignes, "
                  f"stop={reponse.get('stop_reason')}, sortie {usage.get('output_tokens')}")

    finales, manquants = fusionner(extraites, enrichissements) if enrichir else (extraites, [])
    run.ecrire({"type": "synthese", "nb_lignes": len(finales), "non_enrichies": manquants,
                "lignes": finales})
    return {"id_run": id_run, "fichier": str(run.chemin), "nb_lignes": len(finales),
            "non_enrichies": manquants, "lignes": finales}
