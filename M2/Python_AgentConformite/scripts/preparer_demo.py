"""Prépare le dossier demo/ que relit l'application déployée (mode démonstration, sans clé API).

    python scripts/preparer_demo.py

1. calcule les tableaux des expériences complémentaires (écrits dans resultats/ ET demo/resultats/) :
   - longueur_prefixes.json    : rappel du passage unique selon la longueur (préfixes S01…Sk) ;
   - controles_couverture.json : contrôles de l'Agent 2 (placebo, sous-échantillons), dénominateur fixe ;
2. copie dans demo/ les résultats utiles, le journal des coûts et les référentiels ;
3. vérifie qu'aucun secret ne part dans demo/ (motif de clé API, fichier .env).

Ce qui n'est JAMAIS copié : les PDF et textes des normes (data/corpus), le cache disque
(.cache_llm), le fichier .env. Gratuit : aucun appel API.

CONFIDENTIALITÉ : demo/ contient les référentiels Deloitte et des extraits cités d'IFRS 9.
Il ne doit aller que dans un dépôt PRIVÉ, et l'application doit être restreinte aux
destinataires (paramètres de partage de Streamlit Cloud).
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, demo, tableau  # noqa: E402

# Runs de mise au point du 22/10 (prompts v1 et v2, extraits de 2–3 sections) : hors démo.
EXCLUS = (re.compile(r"^section-[0-9a-f]{8}-v[12]-"), re.compile(r"^batch-.*\.json$"))
MOTIF_CLE = re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}")


def _nom(chemin: str) -> str:
    """Nom de fichier depuis un chemin Windows ou POSIX."""
    return re.split(r"[\\/]", chemin)[-1]


def _citees(ev: dict) -> set[str]:
    """Identifiants des lignes IA citées par les verdicts d'un run de l'Agent 2."""
    return {i for e in ev["evaluations"] for el in (e.get("verdict") or {}).get("elements", []) for i in el.get("lignes") or []}


def tableau_controles(dossier: Path) -> dict | None:
    """Associe chaque fichier controle-*_consolide.json au run de l'Agent 2 qui l'a évalué.

    L'en-tête du run ne nomme pas le fichier de contrôle (lancer_agent2 y écrit le champ « run »
    hérité du référentiel source, commun à tous les contrôles). On l'identifie donc par le nombre
    de lignes évaluées ET par les lignes citées dans les verdicts, qui doivent toutes appartenir
    au fichier de contrôle (les tirages de même taille ont des lignes différentes).
    """
    runs2 = {}
    for f in sorted(dossier.glob("agent2-*.jsonl")):
        ev = tableau.evaluation_agent2(f)
        if ev and ev.get("evaluations"):
            runs2[f] = ev
    fichiers = sorted(dossier.glob("controle-*_consolide.json"))
    if not fichiers:
        print("Aucun fichier controle-*_consolide.json : contrôles de couverture ignorés.")
        return None
    meta0 = tableau._json(fichiers[0]) or {}
    source_ref = Path(_nom(meta0.get("source", ""))).stem
    references = [(f, ev) for f, ev in sorted(runs2.items()) if ev["entete"].get("source_ia") == source_ref]
    if not references:
        print(f"Run de l'Agent 2 sur le référentiel complet ({source_ref}) introuvable : contrôles ignorés.")
        return None
    fichier_ref, ref = references[-1]
    exclues = {e["id_ref"] for e in ref["evaluations"] if e["couverture"] == "hors_perimetre"}
    runs = [{"nom": "référentiel complet", "nb_lignes_ia": ref["entete"].get("nb_lignes_ia"),
             "evaluations": ref["evaluations"]}]
    deja, runs_controles = set(), {}
    for fc in fichiers:
        d = tableau._json(fc) or {}
        ids = {l.get("id") for l in d.get("lignes", [])}
        candidats = [f for f, ev in runs2.items() if f not in deja and ev["entete"].get("nb_lignes_ia") == len(ids)
                     and ev["entete"].get("source_ia") != source_ref and _citees(ev) <= ids]
        nom = fc.name.removeprefix("controle-").removesuffix("_consolide.json")
        if not candidats:
            print(f"  {nom} : aucun run de l'Agent 2 correspondant, ignoré.")
            continue
        # Plusieurs runs : le même contrôle relancé (servi par le cache disque, résultats identiques).
        # On retient le plus récent ; tous sont marqués comme contrôles pour les menus.
        choisi = sorted(candidats)[-1]
        deja.update(candidats)
        runs_controles[nom] = choisi.name
        for i, autre in enumerate((c for c in candidats if c != choisi), start=1):
            runs_controles[f"{nom} (doublon {i})"] = autre.name
        ev = runs2[choisi]
        identiques = all(runs2[c]["metriques"] == ev["metriques"] for c in candidats)
        note = "" if len(candidats) == 1 else (f" (+ {len(candidats) - 1} doublon(s) " +
                                              ("identique(s))" if identiques else "DIFFÉRENT(S), le plus récent est retenu)"))
        print(f"  {nom} ({len(ids)} lignes) ← {choisi.name}{note}")
        runs.append({"nom": nom, "nb_lignes_ia": len(ids), "evaluations": ev["evaluations"]})
    lignes = demo.controles_couverture(runs, exclues)
    return {"source": source_ref, "run_reference": fichier_ref.name, "runs_controles": runs_controles,
            "exclues_fixes": sorted(exclues), "nb_lignes_reference": len(ref["evaluations"]),
            "lignes": sorted(lignes, key=lambda l: (l["lignes_ia"] or 0, l["controle"]))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sections", type=Path, default=None,
                   help="sections du document complet (decouper.py --compter) ; défaut : *ifrs*_sections.json")
    p.add_argument("--prefixes", type=Path, default=config.DOSSIER_RESULTATS / "repetitions_prefixes.json")
    p.add_argument("--sortie", type=Path, default=config.RACINE / "demo")
    a = p.parse_args()
    if config.MODE_DEMO:
        sys.exit("À lancer SANS MODE_DEMO=1 : le script lit resultats/ et reconstruit demo/.")
    res = config.DOSSIER_RESULTATS

    # 1) tableaux calculés
    sections_f = a.sections or next(iter(sorted(config.DOSSIER_CORPUS.glob("*ifrs*_sections.json"))), None)
    prefixes = tableau._json(a.prefixes)
    if prefixes and sections_f and sections_f.exists():
        sections = json.loads(sections_f.read_text(encoding="utf-8"))["sections"]
        points = demo.courbe_longueur(prefixes, sections)
        reg = demo.regression_longueur(points)
        sortie = {"document": sections_f.name.removesuffix("_sections.json"), "points": points, "regression": reg}
        (res / "longueur_prefixes.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"longueur_prefixes.json : {len(points)} préfixes, pente {reg.get('pente_par_10k_tokens', 0):+.4f} "
              f"par 10 000 tokens (t = {reg.get('t', float('nan')):.1f}, R² = {reg.get('r2', float('nan')):.2f})")
    else:
        print("Courbe selon la longueur non calculée (repetitions_prefixes.json ou *_sections.json absent).")
    ctrl = tableau_controles(res)
    if ctrl:
        (res / "controles_couverture.json").write_text(json.dumps(ctrl, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"controles_couverture.json : {len(ctrl['lignes'])} lignes, dénominateur fixe "
              f"{ctrl['nb_lignes_reference'] - len(ctrl['exclues_fixes'])} (exclues : {ctrl['exclues_fixes']})")

    # 2) copie
    cible = a.sortie
    if cible.exists():
        shutil.rmtree(cible)
    (cible / "resultats").mkdir(parents=True)
    (cible / "logs").mkdir()
    (cible / "referentiels").mkdir()
    copies, taille = 0, 0
    for f in sorted(res.iterdir()):
        if not f.is_file() or any(m.search(f.name) for m in EXCLUS):
            continue
        shutil.copy2(f, cible / "resultats" / f.name)
        copies += 1
        taille += f.stat().st_size
    if config.JOURNAL_COUTS.exists():
        shutil.copy2(config.JOURNAL_COUTS, cible / "logs" / "couts.jsonl")
    for f in sorted((config.RACINE / "data" / "referentiels").glob("*.xlsx")):
        shutil.copy2(f, cible / "referentiels" / f.name)
    print(f"Copiés : {copies} fichiers de résultats ({taille / 1e6:.1f} Mo), journal des coûts, référentiels.")

    # 3) contrôle des secrets
    fuites = []
    for f in cible.rglob("*"):
        if f.is_file() and f.suffix in (".json", ".jsonl", ".txt", ".md", ".csv"):
            if MOTIF_CLE.search(f.read_text(encoding="utf-8", errors="ignore")):
                fuites.append(f)
        if f.name in (".env", "secrets.toml"):
            fuites.append(f)
    if fuites:
        shutil.rmtree(cible)
        sys.exit(f"ARRÊT : secret détecté dans {fuites}. demo/ a été supprimé.")
    print(f"Aucun secret détecté. Dossier prêt : {cible}")


if __name__ == "__main__":
    main()
