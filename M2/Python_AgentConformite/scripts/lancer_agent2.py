"""Lance l'Agent 2 : couverture d'un référentiel de référence par le référentiel de l'Agent 1.
Commencer TOUJOURS par --simulation (gratuit).

    python scripts/lancer_agent2.py --ia resultats/section-xxxx_consolide.json \\
        --referentiel data/referentiels/referentiel_IFRS9.xlsx --nom "IFRS 9 Financial Instruments" --simulation

--ia accepte un référentiel consolidé (_consolide.json) ou un fichier de run (.jsonl, sa synthèse).
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import agent2, config, couts, traces  # noqa: E402
from src.referentiels import charger_referentiel  # noqa: E402

SORTIE_PAR_LIGNE_REF = 700  # verdict élément par élément, justifications comprises (estimation)
SORTIE_PAR_LIGNE_SUPP = 40  # verdict de pertinence court


def charger_ia(chemin: Path) -> tuple[list[dict], str]:
    if chemin.suffix == ".json":
        d = json.loads(chemin.read_text(encoding="utf-8"))
        return d["lignes"], d.get("run", chemin.stem)
    enreg = [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]
    synthese = next(e for e in reversed(enreg) if e["type"] == "synthese")
    return synthese["lignes"], enreg[0]["id_run"]


def simuler(lignes_ia, ref, a, modele):
    m = lambda x: f"{x:,}".replace(",", " ")
    systeme = agent2.construire_systeme(lignes_ia, a.nom)
    try:
        import anthropic

        config.exiger_cle()
        prefixe = anthropic.Anthropic().messages.count_tokens(
            model=modele, system=systeme, messages=[{"role": "user", "content": "x"}]).input_tokens
        source = "count_tokens (exact)"
    except Exception as e:
        prefixe = int(sum(len(b["text"]) for b in systeme) / 3.04)
        source = f"estimation ({e.__class__.__name__})"
    n_ref = len(ref["lignes"])
    n_blocs = len(agent2._blocs(ref["lignes"], agent2.LIGNES_PAR_BLOC, ref.get("colonne_id")))
    n_supp = 0 if a.sans_pertinence else max(0, len(lignes_ia) - 3 * n_ref)  # ~3 lignes IA mobilisées par ligne
    n_pert = -(-n_supp // agent2.LOT_PERTINENCE)
    n = n_blocs + n_pert
    t = config.TARIFS[modele]
    ecriture = prefixe * t["ecriture_cache"] / 1e6
    lectures = (n - 1) * prefixe * t["lecture_cache"] / 1e6
    sortie = (n_ref * SORTIE_PAR_LIGNE_REF + n_supp * SORTIE_PAR_LIGNE_SUPP) * t["sortie"] / 1e6
    print(f"Modèle {modele} | effort {a.effort} | préfixe {m(prefixe)} tokens [{source}]")
    print(f"Référentiel : {ref['fichier']} — {n_ref} lignes en {n_blocs} blocs ; référentiel IA : {len(lignes_ia)} lignes")
    print(f"Requêtes : {n_blocs} d'appariement + {n_pert} de pertinence (≈ {n_supp} lignes supplémentaires) = {n}")
    print(f"  écriture du préfixe : {m(prefixe)} × {t['ecriture_cache']} / 10⁶ = {ecriture:.3f} $")
    print(f"  relectures          : {n - 1} × {m(prefixe)} × {t['lecture_cache']} / 10⁶ = {lectures:.3f} $")
    print(f"  sortie prévue       : {sortie:.3f} $")
    print(f"  TOTAL PRÉVU ≈ {ecriture + lectures + sortie:.2f} $")
    print(f"Déjà dépensé ce mois : {couts.depense():.2f} $ sur {config.BUDGET_MENSUEL_USD:.0f} $")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ia", required=True, type=Path)
    p.add_argument("--referentiel", required=True, type=Path)
    p.add_argument("--feuille", default=0, help="indice ou nom de la feuille Excel")
    p.add_argument("--nom", required=True, help="intitulé du texte réglementaire")
    p.add_argument("--effort", choices=["low", "medium", "high"], default=agent2.EFFORT_DEFAUT)
    p.add_argument("--modele", default=None)
    p.add_argument("--sans-pertinence", action="store_true", help="appariement seul")
    p.add_argument("--simulation", action="store_true")
    a = p.parse_args()

    feuille = int(a.feuille) if str(a.feuille).isdigit() else a.feuille
    ref = charger_referentiel(a.referentiel, feuille)
    lignes_ia, id_source = charger_ia(a.ia)
    modele = a.modele or config.MODELE_EXTRACTION
    if a.simulation:
        simuler(lignes_ia, ref, a, modele)
        return

    res = agent2.executer(lignes_ia=lignes_ia, referentiel=ref, nom_document=a.nom, id_source=id_source,
                          modele=modele, effort=a.effort, pertinence=not a.sans_pertinence)
    m = res["metriques"]
    pct = lambda x: "—" if x is None else f"{100 * x:.1f} %"
    print(f"\nLignes de référence : {m['nb_lignes_reference']} dont {m['nb_hors_perimetre']} hors périmètre, "
          f"{m['nb_non_evaluees']} non évaluée(s)")
    print(f"Couverture : totale {m['comptes']['totale']}, partielle {m['comptes']['partielle']}, "
          f"absente {m['comptes']['absente']}")
    print(f"Couverture stricte {pct(m['couverture_stricte'])} | large {pct(m['couverture_large'])} | "
          f"qualité moyenne {pct(m['qualite_moyenne'])}")
    print(f"Lignes IA supplémentaires : {m['pertinence_supplementaires']} "
          f"(pertinentes : {pct(m['taux_pertinence_supplementaires'])})")
    print(f"→ {res['fichier']}")
    print(json.dumps(couts.bilan(), indent=1, ensure_ascii=False))
    traces.vider()
    if traces.actif():
        print(f"Traces envoyées au projet LangSmith « {os.getenv('LANGSMITH_PROJECT', 'projet-conformite')} ».")


if __name__ == "__main__":
    main()
