"""Tests de l'export déterministe. AUCUN appel API, formats INVENTÉS."""

import openpyxl

from src.export import exporter, role_colonne

LIGNES = [{"id": "S01-001", "ref": "1.1", "cit": "shall keep a register", "dom": "Registre",
           "obl": "Tenir un registre.", "typ": "mesure", "ctrl": "Contrôle mensuel.", "test": "Échantillon de 25.",
           "crit": "majeure"},
          {"id": "S01-002", "ref": "1.2", "cit": "shall review", "dom": "Revue", "obl": "Revoir.", "typ": "controle",
           "ctrl": "Revue.", "test": "Procès-verbaux.", "crit": "mineure"}]


def _format(tmp_path, entetes, titre=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    if titre:
        ws.append([titre])
    ws.append(entetes)
    ws.append(["contenu", "qui", "ne doit", "jamais être lu"][: len(entetes)])
    chemin = tmp_path / "format.xlsx"
    wb.save(chemin)
    return chemin


def test_roles_tolerent_accents_et_coquilles():
    assert role_colonne("Classication") == "dom" and role_colonne("Contrôle clé") == "ctrl"
    assert role_colonne("Test de conformité") == "test" and role_colonne("CTRL_ID") == "id"
    assert role_colonne("Criticality") == "crit" and role_colonne("Recommendation") == "recommandation"


def test_format_constats_en_anglais(tmp_path):
    fmt = _format(tmp_path, ["Classication", "Finding", "Recommendation", "Criticality"], titre="Titre fusionné")
    r = exporter(LIGNES, fmt, tmp_path / "out.xlsx")
    ws = openpyxl.load_workbook(tmp_path / "out.xlsx").active
    lignes = list(ws.iter_rows(values_only=True))
    assert lignes[0] == ("Classication", "Finding", "Recommendation", "Criticality", "Reference (text)")
    assert lignes[1][0] == "Registre" and "« shall keep a register » (1.1)" in lignes[1][1]
    assert lignes[1][2] == "Contrôle mensuel.\nÉchantillon de 25." and lignes[1][3] == "Major"
    assert lignes[2][3] == "(mineure)" and any("mineure" in a["raison"] for a in r["anomalies"])
    assert "contenu" not in str(lignes)  # aucune ligne de contenu du format n'est recopiée


def test_format_controles_en_francais(tmp_path):
    fmt = _format(tmp_path, ["CTRL_ID", "Domaine", "Contrôle clé", "Test de conformité"])
    exporter(LIGNES, fmt, tmp_path / "out.xlsx")
    lignes = list(openpyxl.load_workbook(tmp_path / "out.xlsx").active.iter_rows(values_only=True))
    assert lignes[0] == ("CTRL_ID", "Domaine", "Contrôle clé", "Test de conformité", "Référence (texte)",
                         "Citation exacte")
    assert lignes[1] == ("S01-001", "Registre", "Contrôle mensuel.", "Échantillon de 25.", "1.1",
                         "shall keep a register")
