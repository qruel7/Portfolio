"""Tests du module batch. AUCUN appel API : faux client des lots."""

import json
from types import SimpleNamespace as NS

import pytest

from src import batch, couts
from src.decoupage import decouper
from tests.test_agent1 import TEXTE


def _sections():
    return decouper(TEXTE, min_tokens=10, max_tokens=120)


def _reponse(custom_id, texte_doc):
    # cite la première phrase du document : citation valide, référence 1.1
    cit = "The operator shall keep a register of incidents number 1 for at least five years"
    lignes = [{"id": "U-001", "ref": "1.1", "cit": cit, "dom": "registre", "obl": "Tenir un registre.",
               "typ": "mesure", "crit": "majeure"}]
    usage = NS(input_tokens=10, cache_creation_input_tokens=1000, cache_read_input_tokens=0, output_tokens=200,
               model_dump=lambda: {"input_tokens": 10, "cache_creation_input_tokens": 1000,
                                   "cache_read_input_tokens": 0, "output_tokens": 200})
    msg = NS(model="claude-sonnet-5-5", usage=usage, stop_reason="end_turn",
             content=[NS(type="text", text=json.dumps({"lignes": lignes}))])
    return NS(custom_id=custom_id, result=NS(type="succeeded", message=msg))


class FauxLots:
    def __init__(self):
        self.requetes, self.statut = None, "in_progress"

    def create(self, requests):
        self.requetes = list(requests)
        return NS(id="msgbatch_test12345678", processing_status="in_progress")

    def retrieve(self, batch_id):
        return NS(id=batch_id, processing_status=self.statut, request_counts=None)

    def results(self, batch_id):
        return [_reponse(r["custom_id"], TEXTE) for r in self.requetes]


def _client():
    lots = FauxLots()
    return NS(messages=NS(batches=lots)), lots


def test_construire_requetes_identiques_entre_repetitions():
    secs = _sections()
    plan = [{"mode": "unique", "ids": None, "k": 3}, {"mode": "section", "ids": [secs[0].id], "k": 1}]
    req, runs = batch.construire(texte=TEXTE, sections=secs, plan=plan, nom_document="Règlement fictif")
    ids = [r["custom_id"] for r in req]
    assert len(ids) == len(set(ids)) == 4 and len(runs) == 4
    uniques = [r["params"] for r in req if r["custom_id"].startswith("u-complet")]
    assert uniques[0] == uniques[1] == uniques[2]  # seule l'étiquette change
    for r in req:
        p = r["params"]
        assert p["output_config"] == {"effort": "medium"}
        assert not {"temperature", "top_p", "top_k"} & set(p)
        assert p["system"][-1]["cache_control"] == {"type": "ephemeral"}  # TTL 5 min par défaut


def test_ttl_1h_refuse_sous_20_requetes():
    with pytest.raises(ValueError, match="TTL 1h interdit"):
        batch.construire(texte=TEXTE, sections=_sections(), plan=[{"mode": "unique", "ids": None, "k": 5}],
                         nom_document="x", ttl="1h")
    req, _ = batch.construire(texte=TEXTE, sections=_sections(), plan=[{"mode": "unique", "ids": None, "k": 20}],
                              nom_document="x", ttl="1h")
    assert req[0]["params"]["system"][-1]["cache_control"]["ttl"] == "1h"


def test_soumettre_recuperer_journalise_une_seule_fois(tmp_path, monkeypatch):
    journal = tmp_path / "j.jsonl"
    monkeypatch.setattr(couts.config, "JOURNAL_COUTS", journal)
    secs = _sections()
    client, lots = _client()
    req, runs = batch.construire(texte=TEXTE, sections=secs, plan=[{"mode": "unique", "ids": None, "k": 2}],
                                 nom_document="Règlement fictif")
    man = batch.soumettre(req, runs, max_usd=0.01, dossier=tmp_path, client=client)
    assert "TEXTE" not in man.read_text(encoding="utf-8") and "register of incidents" not in man.read_text(encoding="utf-8")
    assert batch.recuperer(man, TEXTE, secs, client=client, journal=journal, dossier=tmp_path)["termine"] is False
    lots.statut = "ended"
    bilan = batch.recuperer(man, TEXTE, secs, client=client, journal=journal, dossier=tmp_path)
    assert [r["valides"] for r in bilan["runs"]] == [1, 1]
    lignes_journal = journal.read_text(encoding="utf-8").splitlines()
    assert len(lignes_journal) == 2 and all(json.loads(l)["batch"] for l in lignes_journal)
    # coût batch = moitié : (10×2 + 1000×2,5 + 200×10) / 10⁶ × 0,5
    assert json.loads(lignes_journal[0])["cout_usd"] == pytest.approx((20 + 2500 + 2000) / 1e6 * 0.5)
    batch.recuperer(man, TEXTE, secs, client=client, journal=journal, dossier=tmp_path)  # relance
    assert len(journal.read_text(encoding="utf-8").splitlines()) == 2  # rien de journalisé deux fois
    run = [json.loads(l) for l in open(bilan["runs"][0]["fichier"], encoding="utf-8")]
    assert run[0]["type"] == "entete" and run[0]["repetition"] == 1 and run[-1]["type"] == "synthese"


def test_amorcage_un_appel_par_prefixe(tmp_path):
    journal = tmp_path / "j.jsonl"
    appels = []

    def create(**req):
        appels.append(req)
        return NS(usage=NS(input_tokens=5, cache_creation_input_tokens=900, cache_read_input_tokens=0,
                           output_tokens=2))

    client = NS(messages=NS(create=create))
    secs = _sections()
    req, _ = batch.construire(texte=TEXTE, sections=secs, nom_document="x", ttl="1h",
                              plan=[{"mode": "section", "ids": None, "k": 20}])
    sorties = batch.amorcer(req, client=client, journal=journal)
    assert len(appels) == 1 and appels[0]["max_tokens"] == 16  # un seul préfixe (document complet)
    assert appels[0]["system"][-1]["cache_control"]["ttl"] == "1h" and sorties[0]["cache_ecrit"] == 900
    assert json.loads(journal.read_text(encoding="utf-8"))["ttl"] == "1h"
