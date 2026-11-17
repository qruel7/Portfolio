"""Mesure de l'essoufflement : rappel d'un run (passage unique) contre la pseudo-référence R*.
GRATUIT (aucun appel API).

    python scripts/essoufflement.py resultats/unique-xxxx.jsonl \\
        --reference resultats/section-xxxx_consolide.json \\
        --document data/corpus/ifrs-9-financial-instruments.pdf

R* = lignes du référentiel consolidé (mode section + rattrapage) dont la citation est
valide. Le run et R* doivent porter sur le même texte (empreintes vérifiées).
Écrit <run>_essoufflement.json (et un graphique .png si matplotlib est installé).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import agent1, metriques  # noqa: E402
from src.decoupage import decouper  # noqa: E402
from src.extraction import charger_document, empreinte  # noqa: E402


def lignes_du_run(chemin: Path) -> tuple[dict, list[dict]]:
    enreg = [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]
    lignes = [l for e in enreg if e["type"] == "extraction" for l in e["lignes"]]
    return enreg[0], lignes


def pct(x):
    return "   —  " if x is None else f"{100 * x:5.1f} %"


def graphique(res: dict, sortie: Path) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    ps = [x for x in res["par_section"] if x["n_ref"]]
    fig, ax = plt.subplots(figsize=(9, 4))
    for regle, style in (("large", "o-"), ("stricte", "s--")):
        ax.plot([x["c"] for x in ps], [x[f"r_{regle}"] for x in ps], style, label=f"rappel {regle}")
        reg = res["regressions"][f"sections_{regle}"]
        if reg.get("pente") is not None:
            xs = [ps[0]["c"], ps[-1]["c"]]
            ax.plot(xs, [reg["constante"] + reg["pente"] * v for v in xs], ":", color="grey")
    ax.set_xlabel("section c (position dans le texte)")
    ax.set_ylabel("rappel r(c) contre R*")
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.set_title("Passage unique : rappel par section")
    fig.tight_layout()
    fig.savefig(sortie, dpi=130)
    return True


def evaluer(chemin_run: Path, chemin_reference: Path, doc: dict, verbeux: bool = True) -> dict:
    """Essoufflement d'un run contre R* ; gère les runs sur mini-document. Aucun appel API.

    `doc` : résultat de charger_document() pour le document complet (chargé une seule fois).
    """
    entete, run = lignes_du_run(chemin_run)
    ref = json.loads(chemin_reference.read_text(encoding="utf-8"))
    texte = doc["texte"]
    if doc["sha256_texte"] != ref["sha256_texte"]:
        sys.exit("La référence et le document ne portent pas sur le même texte (empreintes).")
    # Sections du mode section par section : c'est le découpage dans lequel R* a été produit.
    sections = decouper(texte, **entete["params_decoupage"])
    lignes_ref = ref["lignes"]
    ids = None
    if entete["sha256_texte"] != doc["sha256_texte"]:
        # Run sur un mini-document (sous-ensemble de sections) : on reconstruit le mini-texte,
        # on ramène les citations du run à leurs positions dans le texte complet, et on
        # restreint R* aux sections traitées.
        ids = [s["id"] for s in entete["sections"]]
        mini, sections_mini = agent1.mini_document(texte, sections, ids)
        if empreinte(mini) != entete["sha256_texte"]:
            sys.exit("Le run ne correspond ni au document ni à un mini-document de ses sections (empreintes).")
        origine = {s.id: s for s in sections}
        decalage = [(m.debut, m.fin, origine[m.id].debut - m.debut) for m in sections_mini]
        for l in run:
            v = l.get("_verif") or {}
            if v.get("debut") is None:
                continue
            delta = next(dl for d, f, dl in decalage if d <= v["debut"] < f or v["debut"] == f == len(mini))
            l["_verif"] = {**v, "debut": v["debut"] + delta, "fin": v["fin"] + delta}
        sections = [origine[i] for i in ids]
        lignes_ref = [l for l in lignes_ref if (l.get("_verif") or {}).get("debut") is not None
                      and any(s.debut <= l["_verif"]["debut"] < s.fin for s in sections)]
        if verbeux:
            print(f"Mini-document : sections {ids[0]} à {ids[-1]} ({len(ids)}), positions ramenées au texte complet")

    res = metriques.essoufflement(lignes_ref, run, sections, len(texte))
    res["densite"] = metriques.densite_par_section(run, sections)
    res["run"], res["reference"] = entete["id_run"], ref.get("run")
    res["config"] = {"mode": entete["mode"], "sections": "complet" if ids is None else f"{ids[0]}-{ids[-1]}",
                     "repetition": entete.get("repetition"), "batch_id": entete.get("batch_id")}
    res["paragraphes_couverts"] = sorted({l["_verif"]["paragraphe"] for l in run
                                          if (l.get("_verif") or {}).get("statut") == "valide"
                                          and l["_verif"].get("paragraphe")})
    statuts = {}
    for l in run:
        s = (l.get("_verif") or {}).get("statut", "inconnu")
        statuts[s] = statuts.get(s, 0) + 1
    res["statuts_citations_run"] = statuts
    enreg = [json.loads(x) for x in chemin_run.read_text(encoding="utf-8").splitlines() if x.strip()]
    usages = [e.get("usage") or {} for e in enreg if e["type"] == "extraction"]
    res["sortie_tokens"] = sum(u.get("output_tokens", 0) for u in usages)
    res["reflexion_tokens"] = sum((u.get("output_tokens_details") or {}).get("thinking_tokens") or 0 for u in usages)
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run", type=Path, help="run à évaluer (ex. passage unique), fichier .jsonl")
    p.add_argument("--reference", required=True, type=Path, help="_consolide.json du mode section (R*)")
    p.add_argument("--document", required=True, type=Path)
    a = p.parse_args()

    res = evaluer(a.run, a.reference, charger_document(a.document))
    print(f"Run {res['run']} : {res['n_run']} lignes, citations {res['statuts_citations_run']}")
    print(f"R* : {res['n_reference']} lignes à citation valide ({res['reference']})\n")
    print(f"{'c':>3} {'sect':5} {'|R_c|':>6} {'strict':>8} {'large':>8} {'densité run':>12}")
    for x, d in zip(res["par_section"], res["densite"]):
        dens = "—" if d["densite_par_mille_tokens"] is None else f"{d['densite_par_mille_tokens']:.1f}"
        print(f"{x['c']:>3} {x['section']:5} {x['n_ref']:>6} {pct(x['r_stricte']):>8} {pct(x['r_large']):>8} {dens:>12}")
    print(f"\nRappel global : strict {pct(res['rappel_stricte'])} | large {pct(res['rappel_large'])}")
    for nom, reg in res["regressions"].items():
        if reg.get("pente") is None:
            print(f"  {nom:16} : régression impossible (n = {reg['n']})")
            continue
        lo, hi = reg["ic95"]
        unite = "par section" if nom.startswith("sections") else "du début à la fin du texte"
        print(f"  {nom:16} : pente {reg['pente']:+.4f} {unite}  IC95 [{lo:+.4f} ; {hi:+.4f}]  "
              f"p = {reg['p_valeur']:.3g}  n = {reg['n']}  R² = {reg['r2']:.3f}")

    sortie = a.run.with_name(a.run.stem + "_essoufflement.json")
    sortie.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
    print(f"\nÉcrit : {sortie}")
    png = sortie.with_suffix(".png")
    if graphique(res, png):
        print(f"        {png}")


if __name__ == "__main__":
    main()
