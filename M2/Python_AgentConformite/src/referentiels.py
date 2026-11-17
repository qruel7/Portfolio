"""Lecture GÉNÉRIQUE d'un référentiel de référence (fichier Excel), sans format imposé.

Aucune colonne n'est codée en dur : on repère la ligne d'en-tête, on garde toutes les
colonnes, et le juge de l'Agent 2 lit la ligne entière. Un identifiant est pris dans une
colonne dont l'en-tête contient « id » si ses valeurs sont uniques, sinon on utilise le
numéro de ligne Excel (« L3 », « L4 »…), stable et vérifiable dans le fichier.
Les cellules vides sont signalées (ex. une criticité manquante), jamais imputées.
"""

import hashlib
from pathlib import Path

import openpyxl


def _texte(v) -> str:
    return "" if v is None else str(v).strip()


def charger_referentiel(chemin: Path, feuille: int | str = 0) -> dict:
    """Renvoie {colonnes, lignes: [{id_ref, ligne_excel, champs, champs_vides}], sha256, feuille}."""
    chemin = Path(chemin)
    wb = openpyxl.load_workbook(chemin, data_only=True, read_only=True)
    ws = wb.worksheets[feuille] if isinstance(feuille, int) else wb[feuille]
    lignes_brutes = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()

    # En-tête : première ligne avec au moins 3 cellules texte non vides (un titre fusionné
    # au-dessus du tableau, comme dans le référentiel IFRS 9, n'en a qu'une).
    k_entete = next(i for i, r in enumerate(lignes_brutes) if sum(bool(_texte(c)) for c in r) >= 3)
    entete = [_texte(c) for c in lignes_brutes[k_entete]]
    colonnes = [(j, nom) for j, nom in enumerate(entete) if nom]

    donnees = []
    for i, r in enumerate(lignes_brutes[k_entete + 1 :], start=k_entete + 2):  # numéro Excel
        champs = {nom: _texte(r[j]) if j < len(r) else "" for j, nom in colonnes}
        if sum(bool(v) for v in champs.values()) < 2:
            continue  # ligne vide ou résiduelle
        donnees.append({"ligne_excel": i, "champs": champs,
                        "champs_vides": [n for n, v in champs.items() if not v]})

    col_id = next((nom for _, nom in colonnes if "id" in nom.lower().replace("_", " ").split()
                   or nom.lower().endswith("_id")), None)
    valeurs = [d["champs"].get(col_id, "") for d in donnees] if col_id else []
    ids_uniques = col_id and all(valeurs) and len(set(valeurs)) == len(valeurs)
    for d in donnees:
        d["id_ref"] = d["champs"][col_id] if ids_uniques else f"L{d['ligne_excel']}"

    empreinte = hashlib.sha256(chemin.read_bytes()).hexdigest()
    return {"fichier": chemin.name, "feuille": ws.title, "colonnes": [n for _, n in colonnes],
            "colonne_id": col_id if ids_uniques else None, "lignes": donnees, "sha256": empreinte}


def ligne_en_texte(ligne: dict) -> str:
    """Bloc balisé envoyé au juge : toutes les colonnes, dans l'ordre du fichier."""
    corps = "\n".join(f"{nom} : {valeur or '(vide)'}" for nom, valeur in ligne["champs"].items())
    return f'<ligne_reference id_ref="{ligne["id_ref"]}">\n{corps}\n</ligne_reference>'
