"""Dédoublonne un référentiel de l'Agent 1 (v2 : Sonnet, jugement par paire). Commencer par --simulation (gratuit).

    python scripts/dedoublonner.py resultats/section-xxxx_consolide.json --simulation
    python scripts/dedoublonner.py resultats/section-xxxx_consolide.json

Accepte un _consolide.json ou un fichier de run .jsonl (sa synthèse). Écrit :
    <entrée>_dedoublonne.json      même structure que le consolidé (clé "lignes"), plus les fusions ;
    <entrée>_dedoublonnage.xlsx    une ligne par fusion, pour la relecture humaine.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, couts, dedoublonnage, traces  # noqa: E402


def charger(chemin: Path) -> tuple[dict, list[dict]]:
    if chemin.suffix == ".json":
        d = json.loads(chemin.read_text(encoding="utf-8"))
        return d, d["lignes"]
    enreg = [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]
    synthese = next(e for e in reversed(enreg) if e["type"] == "synthese")
    return {"run": enreg[0]["id_run"], "sha256_texte": enreg[0]["sha256_texte"]}, synthese["lignes"]


def revue_excel(res: dict, lignes_entree: list[dict], chemin: Path) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    par_id = {l["id"]: l for l in lignes_entree}
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Fusions"
    ws.append(["Fusion", "Origine", "Rôle", "id", "ref", "obl", "cit", "Raison", "Avis relecteur (OK / À SÉPARER)"])
    for k, f in enumerate(res["fusions"], 1):
        for role, i in [("conservée", f["representant"])] + [("fusionnée", x) for x in f["fusionnes"]]:
            l = par_id[i]
            ws.append([k, f["origine"], role, i, l.get("ref"), l.get("obl"), l.get("cit"),
                       f["raison"] if role == "conservée" else "", ""])
            if role == "conservée":
                for c in ws[ws.max_row]:
                    c.fill = PatternFill("solid", fgColor="E8F0FE")
    for c in ws[1]:
        c.font = Font(bold=True)
    for col, largeur in zip("ABCDEFGHI", (8, 10, 11, 10, 12, 60, 60, 40, 22)):
        ws.column_dimensions[col].width = largeur
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws3 = wb.create_sheet("Paires jugées")
    ws3.append(["Grappe", "a", "b", "Doublon", "Différence relevée", "obl a", "obl b"])
    for g, v in res["verdicts"].items():
        for pr in v.get("paires", []):
            ws3.append([g, pr["a"], pr["b"], "oui" if pr["doublon"] else "non", pr["difference"],
                        par_id[pr["a"]].get("obl"), par_id[pr["b"]].get("obl")])
    for c in ws3[1]:
        c.font = Font(bold=True)
    for col, largeur in zip("ABCDEFG", (8, 10, 10, 9, 50, 60, 60)):
        ws3.column_dimensions[col].width = largeur
    ws2 = wb.create_sheet("Statistiques")
    for k, v in res["stats"].items():
        ws2.append([k, v])
    wb.save(chemin)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("entree", type=Path)
    p.add_argument("--modele", default=None)
    p.add_argument("--simulation", action="store_true")
    a = p.parse_args()

    meta, lignes = charger(a.entree)
    modele = a.modele or config.MODELE_EXTRACTION
    if a.simulation:
        exacts = dedoublonnage.doublons_exacts(lignes)
        paires = dedoublonnage.candidats(lignes)
        gr = dedoublonnage.grappes(lignes, paires)
        n_req = -(-len(gr) // dedoublonnage.GRAPPES_PAR_REQUETE)
        par_id = {l["id"]: l for l in lignes}
        entree = sum(len(dedoublonnage._ligne_compacte(par_id[i])) for g in gr for i in g) / 3.0 + 700 * n_req
        sortie = sum(70 * len(g) * (len(g) - 1) // 2 for g in gr)  # ~70 tokens par paire jugée
        t = config.TARIFS[modele]
        cout = (entree * t["entree"] + sortie * t["sortie"]) / 1e6
        motifs = {}
        for x in paires:
            for m in x["motifs"]:
                motifs[m] = motifs.get(m, 0) + 1
        print(f"{len(lignes)} lignes | doublons exacts : {sum(len(g) - 1 for g in exacts)} | paires candidates : "
              f"{len(paires)} {motifs}")
        print(f"{len(gr)} grappes ({sum(len(g) for g in gr)} lignes, la plus grande : {max(map(len, gr), default=0)}) "
              f"→ {n_req} requête(s) {modele}")
        print(f"  entrée ≈ {entree:,.0f} tokens × {t['entree']} / 10⁶ + sortie ≈ {sortie:,} × {t['sortie']} / 10⁶ "
              f"= {cout:.3f} $".replace(",", " "))
        print(f"Déjà dépensé ce mois : {couts.depense():.2f} $")
        return

    res = dedoublonnage.executer(lignes, modele=modele)
    s = res["stats"]
    print(f"{s['nb_lignes_entree']} → {s['nb_lignes_sortie']} lignes | exacts {s['doublons_exacts']} | "
          f"grappes {s['grappes']} ({s['lignes_en_grappe']} lignes) | fusions LLM {s['fusions_llm']} "
          f"({s['lignes_absorbees_llm']} lignes absorbées) | anomalies {s['anomalies']}")
    for an in res["anomalies"][:10]:
        print(f"  anomalie : {an}")
    sortie = a.entree.with_name(a.entree.stem + "_dedoublonne.json")
    sortie.write_text(json.dumps({**{k: v for k, v in meta.items() if k != "lignes"},
                                  "source": a.entree.name, "dedoublonnage": {k: v for k, v in res.items()
                                                                            if k != "lignes"},
                                  "lignes": res["lignes"]}, ensure_ascii=False, indent=1), encoding="utf-8")
    xlsx = a.entree.with_name(a.entree.stem + "_dedoublonnage.xlsx")
    revue_excel(res, lignes, xlsx)
    print(f"Écrit : {sortie}\n        {xlsx}")
    print(json.dumps(couts.bilan(), indent=1, ensure_ascii=False))
    traces.vider()


if __name__ == "__main__":
    main()
