"""Tests du suivi des coûts : AUCUN appel API, journal dans un dossier temporaire."""

import pytest

from src import couts
from src.couts import BudgetDepasse

SONNET = "claude-sonnet-5-5"


def test_cout_entree_seule():
    # 1 000 000 tokens × 2 $/M = 2,00 $
    assert couts.cout(SONNET, {"input_tokens": 1_000_000}) == pytest.approx(2.0)


def test_cout_premier_appel_section_avec_ecriture_du_document_en_cache():
    # 1 000 × 2 + 167 807 × 2,50 + 3 000 × 10 = 2 000 + 419 517,5 + 30 000 = 451 517,5
    # → 451 517,5 / 1 000 000 = 0,4515175 $
    usage = {"input_tokens": 1_000, "cache_creation_input_tokens": 167_807, "output_tokens": 3_000}
    assert couts.cout(SONNET, usage) == pytest.approx(0.4515175)


def test_cout_lecture_cache_puis_batch():
    # 167 807 × 0,20 = 33 561,4 → 0,0335614 $, divisé par 2 en batch → 0,0167807 $
    usage = {"cache_read_input_tokens": 167_807}
    assert couts.cout(SONNET, usage, batch=True) == pytest.approx(0.0167807)


def test_usage_objet_sdk_avec_champs_none():
    class Usage:  # imite l'objet du SDK, où les champs de cache peuvent valoir None
        input_tokens = 10
        output_tokens = 20
        cache_creation_input_tokens = None
        cache_read_input_tokens = None

    # 10 × 2 + 20 × 10 = 220 → 0,00022 $
    assert couts.cout(SONNET, Usage()) == pytest.approx(0.00022)


def test_modele_sans_tarif_ou_interdit_refuse():
    with pytest.raises(ValueError):
        couts.cout("claude-modele-inconnu", {"input_tokens": 1})
    with pytest.raises(ValueError, match="interdit"):
        couts.cout("claude-fable-5", {"input_tokens": 1})


def test_journal_append_only_et_depense(tmp_path):
    j = tmp_path / "couts.jsonl"
    couts.journaliser(SONNET, {"input_tokens": 1_000_000}, "debug", chemin=j)
    couts.journaliser(SONNET, {"output_tokens": 100_000}, "agent1-section", chemin=j)
    assert len(j.read_text(encoding="utf-8").splitlines()) == 2
    # 2,00 $ + 100 000 × 10 / 10⁶ = 2,00 + 1,00 = 3,00 $
    assert couts.depense(chemin=j) == pytest.approx(3.0)


def test_verifier_budget(tmp_path):
    j = tmp_path / "couts.jsonl"
    couts.journaliser(SONNET, {"output_tokens": 8_000_000}, "debug", chemin=j)  # 80 $
    # plafond = 100 × 0,9 = 90 $ ; 80 + 5 = 85 ≤ 90 → marge 5 $
    assert couts.verifier_budget(5, budget=100, seuil=0.9, chemin=j) == pytest.approx(5.0)
    # 80 + 15 = 95 > 90 → refus
    with pytest.raises(BudgetDepasse):
        couts.verifier_budget(15, budget=100, seuil=0.9, chemin=j)


def test_bilan(tmp_path):
    j = tmp_path / "couts.jsonl"
    couts.journaliser(SONNET, {"cache_creation_input_tokens": 1_000}, "agent1-section", chemin=j)
    couts.journaliser(SONNET, {"cache_read_input_tokens": 19_000}, "agent1-section", chemin=j)
    b = couts.bilan(chemin=j)
    assert b["nb_appels"] == 2
    assert b["ratio_lecture_ecriture"] == 19.0
    assert set(b["par_etiquette"]) == {"agent1-section"}
