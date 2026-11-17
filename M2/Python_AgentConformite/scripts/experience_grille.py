"""Expérience « grille de contrôle » : même extraction, enrichissements différents, Agent 2.

L'extraction est FIGÉE (un référentiel déjà produit) : seule la consigne d'enrichissement varie
d'une version à l'autre. Pour chaque version et chaque répétition : enrichissement seul, puis
Agent 2 contre le référentiel de référence. La différence de couverture et de qualité ne peut
donc venir que de l'enrichissement. Commencer par --simulation (gratuit).

    python scripts/experience_grille.py --ia resultats/section-xxxx_consolide_dedoublonne.json \\
        --document data/corpus/sapin2-legifrance-2026-10-24.pdf --nom "…" \\
        --referentiel data/referentiels/referentiel_sapin_2.xlsx --versions v4a,v4 --k 3 --simulation
puis la même commande avec --confirmer à la place de --simulation.
"""

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import agent1, agent2, config, couts, metriques, tableau, traces  # noqa: E402
from src.enrichissement import enrichir  # noqa: E402
from src.extraction import charger_document  # noqa: E402
from src.referentiels import charger_referentiel  # noqa: E402

CLES = ("couverture_stricte", "couverture_large", "qualite_moyenne")


def welch(a, b):
    if len(a) < 2 or len(b) < 2:
        return None
    va, vb = st.variance(a), st.variance(b)
    se = math.sqrt(va / len(a) + vb / len(b))
    if se == 0:
        return 0.0 if st.fmean(a) != st.fmean(b) else 1.0
    t = (st.fmean(a) - st.fmean(b)) / se
    ddl = (va / len(a) + vb / len(b)) ** 2 / ((va / len(a)) ** 2 / (len(a) - 1) + (vb / len(b)) ** 2 / (len(b) - 1))
    return metriques._p_bilaterale_t(t, max(1, round(ddl)))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ia", required=True, type=Path, help="extraction figée (consolidé / dédoublonné)")
    p.add_argument("--document", required=True, type=Path)
    p.add_argument("--nom", required=True)
    p.add_argument("--referentiel", required=True, type=Path)
    p.add_argument("--versions", default="v4a,v4")
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--simulation", action="store_true")
    p.add_argument("--confirmer", action="store_true")
    a = p.parse_args()

    source, lignes = tableau.lignes_referentiel(a.ia)  # .json (consolidé) ou .jsonl (run)
    source = {k: v for k, v in source.items() if k in ("run", "rattrapage", "sha256_texte", "version_prompt", "id_run")}
    versions = [v.strip() for v in a.versions.split(",")]
    doc = charger_document(a.document)
    if source.get("sha256_texte") and source["sha256_texte"] != doc["sha256_texte"]:
        sys.exit("L'extraction figée ne porte pas sur ce document (empreintes différentes).")
    ref = charger_referentiel(a.referentiel)
    t = config.TARIFS[config.MODELE_EXTRACTION]
    prefixe = int(len(doc["texte"]) / 3.04) + 2_400
    lots = -(-len(lignes) // agent1.TAILLE_LOT_DEFAUT)
    enr = (prefixe * t["ecriture_cache"] + (a.k * lots - 1) * prefixe * t["lecture_cache"]
           + a.k * len(lignes) * 260 * t["sortie"]) / 1e6
    a2 = 0.35  # mesuré : 0,28 à 0,31 $ par run d'Agent 2 sur Sapin 2 (52 lignes de référence)
    total = len(versions) * (enr + a.k * a2)
    print(f"Extraction figée : {a.ia.name} ({len(lignes)} lignes) | versions {versions} | k = {a.k}")
    print(f"Par version : enrichissement ≈ {enr:.2f} $ ({a.k * lots} appels) + Agent 2 ≈ {a.k} × {a2:.2f} $")
    print(f"TOTAL ≈ {total:.2f} $ (déjà dépensé ce mois : {couts.depense():.2f} $)")
    if a.simulation:
        return
    if not a.confirmer:
        sys.exit("Ajouter --confirmer pour lancer (appels payants).")
    couts.verifier_budget(total * 1.5)

    resultats = {v: [] for v in versions}
    for v in versions:
        for r in range(1, a.k + 1):
            e = enrichir(lignes, texte=doc["texte"], nom_document=a.nom, version=v, repetition=r)
            chemin = a.ia.with_name(f"{a.ia.stem}_grille-{v}-r{r}.json")
            chemin.write_text(json.dumps({**{k: x for k, x in source.items() if k != "lignes"},
                                          "experience": {"version_enrichissement": v, "repetition": r,
                                                         "non_enrichies": e["non_enrichies"]},
                                          "lignes": e["lignes"]}, ensure_ascii=False, indent=1), encoding="utf-8")
            res = agent2.executer(lignes_ia=e["lignes"], referentiel=ref, nom_document=a.nom, id_source=chemin.stem)
            m = res["metriques"]
            resultats[v].append({"fichier_ia": chemin.name, "run_agent2": Path(res["fichier"]).name,
                                 **{k: m.get(k) for k in CLES}, "non_enrichies": len(e["non_enrichies"])})
            print(f"  {v} r{r} : " + " | ".join(f"{k} {100 * m[k]:.1f} %" for k in CLES if m.get(k) is not None))

    print("\nRésultat (moyenne ± écart-type sur les répétitions) :")
    print(f"{'':22}" + "".join(f"{v:>18}" for v in versions) + ("   p (Welch)" if len(versions) == 2 else ""))
    for k in CLES:
        cel = []
        for v in versions:
            x = [100 * r[k] for r in resultats[v] if r[k] is not None]
            cel.append(f"{st.fmean(x):.1f}" + (f" ± {st.stdev(x):.1f}" if len(x) > 1 else "") if x else "—")
        pv = ""
        if len(versions) == 2:
            pw = welch(*[[r[k] for r in resultats[v] if r[k] is not None] for v in versions])
            pv = f"   {pw:.3g}" if pw is not None else "   —"
        print(f"{k:22}" + "".join(f"{c:>18}" for c in cel) + pv)
    sortie = a.ia.with_name(f"{a.ia.stem}_experience_grille.json")
    sortie.write_text(json.dumps(resultats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nÉcrit : {sortie}")
    print(json.dumps(couts.bilan(), indent=1, ensure_ascii=False))
    traces.vider()


if __name__ == "__main__":
    main()
