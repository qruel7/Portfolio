"""Gap analysis lisible (Excel) à partir des résultats de l'Agent 2. Aucun appel API.

Feuille « Couverture » : une ligne par ligne de référence (couverture, score, éléments).
Feuille « Éléments » : un élément par ligne, avec les lignes IA qui le couvrent.
Feuille « Supplémentaires » : verdict de pertinence des lignes IA non mobilisées.
Feuille « Métriques » : les chiffres de synthèse.
Le fichier contient des extraits du référentiel de référence : il reste dans resultats/ (non versionné).
"""

from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

COULEURS = {"totale": "C6EFCE", "partielle": "FFEB9C", "absente": "FFC7CE", "hors_perimetre": "D9D9D9",
            "non_evaluee": "D9D9D9", "equivalent": "C6EFCE", "principe": "FFEB9C", "absent": "FFC7CE"}


def _feuille(wb, titre, entete, lignes, largeurs):
    ws = wb.create_sheet(titre)
    ws.append(entete)
    for c in ws[1]:
        c.font = Font(bold=True)
    for l in lignes:
        ws.append(l)
    for k, w in enumerate(largeurs):
        ws.column_dimensions[openpyxl.utils.get_column_letter(k + 1)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if isinstance(c.value, str) and c.value in COULEURS:
                c.fill = PatternFill("solid", fgColor=COULEURS[c.value])
    ws.freeze_panes = "A2"
    return ws


def ecrire_gap_analysis(resultat: dict, referentiel: dict, lignes_ia: list[dict], chemin: Path) -> Path:
    par_ref = {l["id_ref"]: l for l in referentiel["lignes"]}
    par_ia = {l["id"]: l for l in lignes_ia}
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    couv, elems = [], []
    for e in resultat["evaluations"]:
        champs = par_ref[e["id_ref"]]["champs"]
        resume_ref = " | ".join(v[:300] for v in champs.values() if v)
        v = e["verdict"] or {}
        couv.append([e["id_ref"], e["couverture"], None if e["score"] is None else round(e["score"], 2),
                     len(v.get("elements", [])), v.get("justification", ""), ", ".join(e["ids_inventes"]),
                     ", ".join(e["champs_vides"]), resume_ref])
        for el in v.get("elements", []):
            elems.append([e["id_ref"], el["element"], el["niveau"], ", ".join(el["lignes"]),
                          " || ".join(f"{i} : {par_ia[i]['obl']}" for i in el["lignes"] if i in par_ia),
                          el["justification"]])
    _feuille(wb, "Couverture", ["Ligne de référence", "Couverture", "Score qualité", "Nb éléments",
                                "Justification du juge", "Id inventés (retirés)", "Champs vides", "Ligne de référence (extrait)"],
             couv, [12, 14, 10, 9, 60, 16, 14, 90])
    _feuille(wb, "Éléments", ["Ligne de référence", "Élément", "Niveau", "Lignes IA", "Obligations IA citées", "Justification"],
             elems, [12, 60, 12, 24, 80, 60])
    supp = [[p["id"], p["p"], p.get("raison", ""), par_ia.get(p["id"], {}).get("ref", ""),
             par_ia.get(p["id"], {}).get("obl", "")] for p in resultat["pertinences"]]
    _feuille(wb, "Supplémentaires", ["Ligne IA", "Pertinence", "Raison", "Réf.", "Obligation"], supp, [12, 16, 40, 12, 90])
    m = resultat["metriques"]
    lignes_m = [[k, str(v) if isinstance(v, dict) else v] for k, v in m.items()]
    _feuille(wb, "Métriques", ["Indicateur", "Valeur"], lignes_m, [36, 60])
    chemin = Path(chemin)
    wb.save(chemin)
    return chemin
