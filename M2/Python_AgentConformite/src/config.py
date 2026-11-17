"""Configuration centrale du projet : chemins, modèles, tarifs, budget.

Tout ce qui peut changer sans toucher au code se règle dans le fichier .env.
L'import de ce module n'exige PAS la clé API (les tests tournent sans clé) :
les fonctions qui appellent l'API doivent appeler exiger_cle() elles-mêmes.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# --- Chemins ------------------------------------------------------------------
RACINE = Path(__file__).resolve().parent.parent
load_dotenv(RACINE / ".env")

DOSSIER_LOGS = RACINE / "logs"
JOURNAL_COUTS = Path(os.getenv("JOURNAL_COUTS", str(DOSSIER_LOGS / "couts.jsonl")))
DOSSIER_CACHE = Path(os.getenv("DOSSIER_CACHE", str(RACINE / ".cache_llm")))
DOSSIER_CORPUS = RACINE / "data" / "corpus"
DOSSIER_RESULTATS = RACINE / "resultats"
DOSSIER_REFERENTIELS = RACINE / "data" / "referentiels"

# --- Mode démonstration (application déployée, sans clé API) ---------------------
# Activé par MODE_DEMO=1 (variable d'environnement ou secret Streamlit Cloud). Tout est
# alors relu dans demo/, préparé par scripts/preparer_demo.py ; aucun appel API possible.
DOSSIER_DEMO = RACINE / "demo"
MODE_DEMO = os.getenv("MODE_DEMO", "0") == "1"
if MODE_DEMO:
    DOSSIER_RESULTATS = DOSSIER_DEMO / "resultats"
    DOSSIER_REFERENTIELS = DOSSIER_DEMO / "referentiels"
    JOURNAL_COUTS = DOSSIER_DEMO / "logs" / "couts.jsonl"

# --- Modèles (identifiants vérifiés par client.models.list() le 07/10/2026) ---
MODELE_EXTRACTION = os.getenv("MODELE_EXTRACTION", "claude-sonnet-5-5")
MODELE_MECANIQUE = os.getenv("MODELE_MECANIQUE", "claude-haiku-4-5-20251001")
MODELE_ARBITRE = os.getenv("MODELE_ARBITRE", "claude-opus-5-5")

# Fable est bloqué par le cadrage pendant tout le projet.
MOTIFS_INTERDITS = ("fable",)

# --- Découpage (décision du 22/10 : sections plus petites, réponses plus courtes) ----
DECOUPAGE_MIN_TOKENS = int(os.getenv("DECOUPAGE_MIN_TOKENS", "4000"))
DECOUPAGE_MAX_TOKENS = int(os.getenv("DECOUPAGE_MAX_TOKENS", "8000"))

# --- Budget ---------------------------------------------------------------------
# Octobre : 250 $ (report de septembre, confirmé par l'enseignant). Clé révoquée le 31/10.
BUDGET_MENSUEL_USD = float(os.getenv("BUDGET_MENSUEL_USD", "250"))
# On s'arrête avant le plafond : 0.9 = blocage à 90 % de l'enveloppe.
SEUIL_BUDGET = float(os.getenv("SEUIL_BUDGET", "0.9"))

# --- Tarifs (USD par million de tokens) -----------------------------------------
# Source : support de cadrage (versions 5). Étendus aux versions 5.5 sur
# confirmation de l'enseignant (« pas plus consommatrices »). À revérifier
# sur la page officielle des tarifs avant le chiffrage final.
_HAIKU = {"entree": 1.00, "ecriture_cache": 1.25, "lecture_cache": 0.10, "sortie": 5.00}
_SONNET = {"entree": 2.00, "ecriture_cache": 2.50, "lecture_cache": 0.20, "sortie": 10.00}
_OPUS = {"entree": 5.00, "ecriture_cache": 6.25, "lecture_cache": 0.50, "sortie": 25.00}

TARIFS = {
    "claude-haiku-4-5-20251001": _HAIKU,
    "claude-sonnet-5": _SONNET,
    "claude-sonnet-5-5": _SONNET,
    "claude-opus-5": _OPUS,
    "claude-opus-5-5": _OPUS,
}

REMISE_BATCH = 0.5  # le batch divise tout par deux, cumulable avec le cache
# Écriture en cache avec TTL d'une heure, en multiple du tarif d'entrée.
# Le cadrage ne donne que le tarif 5 min : valeur à vérifier dans la documentation.
MULTIPLICATEUR_ECRITURE_1H = 2.0


def verifier_modele(modele: str) -> str:
    """Refuse un modèle interdit ou sans tarif connu (on ne veut jamais d'un coût à 0 par erreur)."""
    if any(m in modele.lower() for m in MOTIFS_INTERDITS):
        raise ValueError(f"Modèle interdit par le cadrage : {modele}")
    if modele not in TARIFS:
        raise ValueError(f"Aucun tarif déclaré pour {modele} : l'ajouter dans config.TARIFS.")
    return modele


def exiger_cle() -> None:
    """À appeler juste avant tout appel API. Ne renvoie jamais la clé elle-même."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY absente : vérifier le fichier .env à la racine.")
