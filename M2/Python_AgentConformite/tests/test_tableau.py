"""Tests de la couche de données du dashboard. AUCUN appel API, fichiers inventés."""

import json

from src import couts, tableau


def test_couts_detail_et_par_jour(tmp_path):
    j = tmp_path / "c.jsonl"
    u1 = {"input_tokens": 10, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 0, "output_tokens": 100}
    u2 = {"input_tokens": 10, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 1000, "output_tokens": 100}
    couts.journaliser("claude-sonnet-5-5", u1, "agent1-section-extraction", chemin=j)
    couts.journaliser("claude-sonnet-5-5", u2, "agent1-section-extraction", batch=True, chemin=j)
    journal = couts.lire_journal(j)
    d = tableau.couts_detail(journal)[0]
    assert d["appels"] == 2 and d["cache_lu"] == 1000 and d["part_lue_en_cache"] == round(1000 / 2020, 3)
    assert d["cout_batch_usd"] == round(journal[1]["cout_usd"], 4)
    assert len(tableau.couts_par_jour(journal)) == 1


def test_lister_runs_et_agent2(tmp_path):
    lignes = [{"id": "S01-001", "_verif": {"statut": "valide"}}, {"id": "S01-002", "_verif": {"statut": "introuvable"}}]
    (tmp_path / "section-x.jsonl").write_text("\n".join(json.dumps(e) for e in [
        {"type": "entete", "id_run": "section-x", "mode": "section", "nom_document": "Doc",
         "sections": [{"id": "S01"}, {"id": "S02"}]},
        {"type": "extraction", "usage": {"output_tokens": 50}},
        {"type": "synthese", "nb_lignes": 2, "lignes": lignes}]), encoding="utf-8")
    ev = {"id_ref": "L3", "couverture": "partielle", "score": 0.5,
          "verdict": {"justification": "j", "elements": [{"niveau": "principe", "lignes": ["S01-001"]},
                                                         {"niveau": "absent", "lignes": []}]}}
    (tmp_path / "agent2-y.jsonl").write_text("\n".join(json.dumps(e) for e in [
        {"type": "entete", "id_run": "agent2-y", "regle_appariement": "v1", "referentiel": "r.xlsx"},
        {"type": "synthese", "metriques": {"couverture_large": 1.0}, "evaluations": [ev], "pertinences": []}]),
        encoding="utf-8")
    runs = {r["fichier"]: r for r in tableau.lister_runs(tmp_path)}
    assert runs["section-x.jsonl"]["citations_valides"] == 1 and runs["section-x.jsonl"]["sections"] == "S01–S02 (2)"
    assert runs["agent2-y.jsonl"]["agent"] == "agent2"
    e = tableau.evaluation_agent2(tmp_path / "agent2-y.jsonl")
    t = tableau.table_couverture(e, {"lignes": [{"id_ref": "L3", "champs": {"Finding": "texte"}}]})[0]
    assert (t["principe"], t["absent"], t["lignes_ia"], t["ligne_reference"]) == (1, 1, "S01-001", "Finding : texte")


def test_courbes_rc_positionnees_sur_le_document_complet():
    rep = {"unique:S11-S12": {"k": 2, "r_c_moyen": [
        {"section": "S11", "r_large": {"moyenne": 0.8, "ecart_type": 0.1, "k": 2}, "r_stricte": {"moyenne": 0.5}},
        {"section": "S12", "r_large": {"moyenne": 0.6, "ecart_type": None, "k": 2}, "r_stricte": {}}]},
        "_comparaisons": {}}
    pts = [p for p in tableau.courbes_rc(rep) if p["regle"] == "large"]
    assert [p["c"] for p in pts] == [11, 12] and abs(pts[0]["bas"] - 0.7) < 1e-9 and pts[1]["haut"] == 0.6


def test_comparatif_versions(tmp_path):
    def run(nom, source, doc, large, lignes):
        (tmp_path / f"{nom}.jsonl").write_text("\n".join(json.dumps(e) for e in [
            {"type": "entete", "source_ia": source, "nom_document": doc, "nb_lignes_ia": lignes},
            {"type": "synthese", "metriques": {"couverture_large": large, "couverture_stricte": 0.0,
                                               "qualite_moyenne": 0.4}, "evaluations": []}]), encoding="utf-8")
    run("agent2-a-v1-1", "section-5b820c13-v3-20261022T181226_consolide", "IFRS 9 Financial Instruments", 0.9, 10)
    run("agent2-a-v1-2", "section-5b820c13-v4b-20261027T003657_consolide_dedoublonne", "IFRS 9", 1.0, 12)
    run("agent2-b-v1-1", "section-ce42aa5e-v4b-X_consolide", "Loi Sapin 2", 0.8, 4)
    run("agent2-b-v1-2", "section-ce42aa5e-v4b-Y_consolide", "Loi Sapin 2", 0.6, 6)
    run("agent2-b-v1-3", "section-ce42aa5e-v4a-Z_consolide_grille-v4-r1", "Loi Sapin 2", 0.1, 6)  # écarté
    run("agent2-c-v1-1", "section-5b820c13-v4b-W", "IFRS 9", 0.0, 3)  # contrôle, écarté
    (tmp_path / "section-ce42aa5e-v4b-X_consolide.json").write_text(json.dumps({"lignes": [
        {"id": "a", "_verif": {"statut": "valide"}}, {"id": "b", "_verif": {"statut": "introuvable"}}]}), encoding="utf-8")
    lignes = tableau.comparatif_versions(tmp_path, exclus={"agent2-c-v1-1.jsonl"})
    assert [(l["texte"], l["version"], l["runs_agent2"]) for l in lignes] == [
        ("IFRS 9", "v3", 1), ("IFRS 9", "v4b", 1), ("Sapin 2", "v4b", 2)]
    sapin = lignes[2]
    assert abs(sapin["couverture_large"] - 0.7) < 1e-9 and sapin["lignes_ia"] == 5 and sapin["hallucination"] == 0.5


def test_fiche_ligne_et_referentiel_evalue(tmp_path):
    lignes_ia = [{"id": "S05-001", "ref": "5.5.1", "cit": "An entity shall recognise", "obl": "o1",
                  "_verif": {"statut": "valide"}},
                 {"id": "S05-002", "ref": "5.5.3", "cit": "c2", "obl": "o2", "_verif": {"statut": "valide"}}]
    (tmp_path / "section-x_consolide.json").write_text(json.dumps({"lignes": lignes_ia}), encoding="utf-8")
    ev = {"entete": {"source_ia": "section-x_consolide"}, "evaluations": [
        {"id_ref": "L14", "couverture": "partielle", "score": 0.5, "verdict": {"justification": "j", "elements": [
            {"element": "e1", "niveau": "principe", "lignes": ["S05-002", "S05-001"], "justification": "a"},
            {"element": "e2", "niveau": "equivalent", "lignes": ["S05-001", "S99-999"], "justification": "b"}]}}]}
    chemin, lignes = tableau.referentiel_ia_evalue(ev, tmp_path)
    assert chemin.name == "section-x_consolide.json" and len(lignes) == 2
    ref = {"lignes": [{"id_ref": "L14", "champs": {"Finding": "f", "Recommendation": "r"}}]}
    f = tableau.fiche_ligne(ev, "L14", ref, lignes)
    assert f["champs"]["Finding"] == "f" and f["couverture"] == "partielle" and len(f["elements"]) == 2
    assert [l["id"] for l in f["lignes"]] == ["S05-002", "S05-001", "S99-999"]  # ordre d'apparition, sans doublon
    assert f["lignes"][1]["cit"] == "An entity shall recognise" and not f["lignes"][2]["trouvee"]
    assert tableau.fiche_ligne(ev, "L99", ref, lignes) is None
