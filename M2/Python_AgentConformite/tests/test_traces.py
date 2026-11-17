"""Tests des traces LangSmith : un faux client LangSmith capture ce qui serait envoyé.

AUCUN appel réseau. On vérifie surtout deux choses : le coût envoyé est
exactement celui du journal, et AUCUN texte (document, prompt, réponse) ne part.
"""

import pytest

pytest.importorskip("langsmith")

from src import couts, traces  # noqa: E402

SONNET = "claude-sonnet-5-5"
USAGE = {"input_tokens": 212, "cache_creation_input_tokens": 23_861,
         "cache_read_input_tokens": 0, "output_tokens": 5_481}


class FauxLangSmith:
    """Imite les méthodes du client LangSmith qu'utilise RunTree.post()."""

    def __init__(self):
        self.envois = []

    def create_run(self, **kw):
        self.envois.append(kw)

    def update_run(self, *a, **kw):
        self.envois.append(kw)

    def __getattr__(self, nom):  # toute autre méthode éventuelle : ignorée
        return lambda *a, **kw: None


def test_cout_envoye_identique_au_journal():
    um = traces.usage_metadata(SONNET, USAGE)
    # entrée : 212 × 2 + 23 861 × 2,50 = 424 + 59 652,5 = 60 076,5 → 0,0600765 $
    # sortie : 5 481 × 10 = 54 810 → 0,05481 $
    assert um["input_cost"] == pytest.approx(0.0600765, abs=2e-6)
    assert um["output_cost"] == pytest.approx(0.05481)
    assert um["total_cost"] == pytest.approx(couts.cout(SONNET, USAGE), abs=1e-6)
    # chez Anthropic, les tokens de cache s'ajoutent à input_tokens
    assert um["input_tokens"] == 212 + 23_861
    assert um["input_token_details"] == {"cache_creation": 23_861}


def test_batch_divise_par_deux():
    assert traces.usage_metadata(SONNET, USAGE, batch=True)["total_cost"] == pytest.approx(
        couts.cout(SONNET, USAGE, batch=True), abs=1e-6)


def test_trace_sans_aucun_texte():
    faux = FauxLangSmith()
    debut = traces.maintenant()
    envoye = traces.tracer(modele=SONNET, etiquette="agent1-section-extraction", usage=USAGE,
                           debut=debut, fin=traces.maintenant(), stop_reason="end_turn",
                           meta={"tache": "S04", "version_prompt": "v2",
                                 "lignes": [{"cit": "texte de la norme"}]},  # non scalaire : écarté
                           client=faux)
    assert envoye is True and faux.envois
    contenu = repr(faux.envois)
    assert "texte de la norme" not in contenu
    assert "S04" in contenu and "total_cost" in contenu


def test_inactif_sans_cle(monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    assert traces.actif() is False
    assert traces.tracer(modele=SONNET, etiquette="x", usage=USAGE,
                         debut=traces.maintenant(), fin=traces.maintenant()) is False


def test_une_erreur_de_trace_ne_casse_pas_le_run():
    class Casse(FauxLangSmith):
        def create_run(self, **kw):
            raise ConnectionError("LangSmith injoignable")

    with pytest.warns(UserWarning, match="non envoyée"):
        ok = traces.tracer(modele=SONNET, etiquette="x", usage=USAGE, debut=traces.maintenant(),
                           fin=traces.maintenant(), client=Casse())
    assert ok is False
