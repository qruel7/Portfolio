# Construction de l'environnement et commandes usuelles du projet.
#   make setup   crée .venv et installe les dépendances (requirements.txt, versions figées)
#   make test    lance les tests (aucun appel API)
#   make demo    prépare demo/ à partir de resultats/ (gratuit, aucun appel API)
#   make run     lance l'application en mode démonstration (relit demo/, aucune clé nécessaire)
#   make run-local  lance l'application en mode complet (clé API dans .env, onglet Pilotage actif)

PYTHON ?= python3
VENV := .venv
ifeq ($(OS),Windows_NT)
	BIN := $(VENV)/Scripts
else
	BIN := $(VENV)/bin
endif
PY := $(BIN)/python

.PHONY: help setup venv install test demo run run-local clean

help:
	@echo "make setup      créer l'environnement virtuel et installer les dépendances"
	@echo "make test       lancer les tests (aucun appel API)"
	@echo "make demo       préparer le dossier demo/ (résultats figés relus par l'application)"
	@echo "make run        lancer l'application en mode démonstration"
	@echo "make run-local  lancer l'application en mode complet (clé API dans .env)"
	@echo "make clean      supprimer l'environnement virtuel"

setup: venv install

venv:
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip

install:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q

demo:
	$(PY) scripts/preparer_demo.py

run:
	MODE_DEMO=1 $(PY) -m streamlit run app_streamlit.py

run-local:
	$(PY) -m streamlit run app_streamlit.py

clean:
	rm -rf $(VENV)
