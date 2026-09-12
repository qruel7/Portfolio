# ESA IA — Chatbot RAG pour le Master ESA (Université d'Orléans)

Projet réalisé dans le cadre du Master 1 ESA (Économétrie et Statistique Appliquée) — Université d'Orléans, année universitaire 2025-2026.

> ⚠️ **Ce projet n'est plus opérationnel** : la clé API Groq utilisée pendant le développement a expiré. Le code est mis à disposition à titre de démonstration technique. Pour le faire fonctionner à nouveau, il suffit de générer une nouvelle clé API Groq gratuite (voir section [Relancer le projet](#relancer-le-projet)).

---

## 📌 Présentation

**ESA IA** est un assistant conversationnel intelligent conçu pour répondre aux questions des candidats et étudiants du Master ESA. Il repose sur une architecture **RAG (Retrieval-Augmented Generation)** : plutôt que de s'appuyer sur les seules connaissances d'un LLM, le système interroge une base de connaissances structurée pour formuler des réponses fiables et sourcées.

Le chatbot couvre l'ensemble des informations relatives au master :
- Programme détaillé (S7 à S10, voie professionnelle et voie recherche)
- Conditions d'admission et procédure de candidature
- Statistiques d'insertion professionnelle
- Équipe pédagogique et contacts
- Annuaire des diplômés (accès restreint, mode connecté)

---

## 🛠️ Stack technique

| Composant | Outil |
|---|---|
| Interface conversationnelle | [Chainlit](https://chainlit.io/) |
| Base vectorielle | [ChromaDB](https://www.trychroma.com/) |
| Modèle d'embedding | `intfloat/multilingual-e5-large` (via Hugging Face) |
| Modèle de langage | Llama-4-Scout (via [Groq](https://groq.com/)) |
| Feedback utilisateur | Google Sheets (via `gspread`) |
| Langage | Python 3.12 |

---

## ⚙️ Fonctionnalités clés

- **Pipeline RAG complet** : chunking structuré des fichiers Markdown, embedding multilingue, retrieval sémantique par similarité cosinus
- **Boosts thématiques** : injection ciblée de chunks supplémentaires selon l'intention détectée (candidature, syllabus, insertion, entreprise, recherche), pour garantir l'exhaustivité des réponses
- **Deux modes d'accès** : mode visiteur (informations publiques) et mode connecté (accès à l'annuaire des diplômés)
- **Instructions dynamiques** : détection d'intentions dans la requête (ECTS, entreprise, semestre, convention de promotion) et injection d'instructions contextuelles dans le prompt
- **Post-traitement des réponses** : extraction automatique des sources citées par le LLM, transformation en liens naturels vers le site officiel, affichage dans un menu dépliable
- **Feedback utilisateur** : boutons 👍/👎 après chaque réponse, stockage dans Google Sheets avec anti-double-vote
- **Interface personnalisée** : identité visuelle du Master ESA (logo, avatar, favicon, thèmes clair/sombre)

---

## 📁 Structure du dépôt

```
├── app.py                    # Application principale (logique RAG, interface Chainlit)
├── chunk_all.py              # Pipeline de chunking de la base de connaissances
├── embed_to_chromadb.py      # Indexation vectorielle dans ChromaDB
├── requirements.txt          # Dépendances Python
├── .env.example              # Template de configuration (clés API)
├── rapport_esa_ia.pdf        # Rapport de projet complet
├── .chainlit/
│   └── config.toml           # Configuration Chainlit
├── markdown_files/           # Base de connaissances (fichiers Markdown)
└── public/
    └── custom.css            # Personnalisation visuelle de l'interface
```

---

## 🚀 Relancer le projet

**1. Générer une clé API Groq (gratuite)**

Créer un compte sur [console.groq.com](https://console.groq.com/keys) et générer une clé API.

**2. Configurer l'environnement**

```bash
cp .env.example .env
# Renseigner GROQ_API_KEY et GSHEET_ID dans le fichier .env
```

**3. Installer les dépendances** (Python 3.12 requis)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

**4. Générer la base vectorielle**

```bash
python chunk_all.py
python embed_to_chromadb.py
```

⚠️ Le premier lancement télécharge le modèle d'embedding (~2 Go). Compter 5 à 10 minutes.

**5. Lancer le chatbot**

```bash
chainlit run app.py
```

L'interface est accessible sur `http://localhost:8000`.

---

## 📄 Rapport de projet

Le rapport complet (`rapport_esa_ia.pdf`) détaille l'ensemble du projet : choix d'architecture, construction de la base de connaissances, pipeline RAG, démarche d'évaluation (60+ tests), corrections itératives, système de feedback et perspectives d'évolution.

---

## ⚠️ Limitations connues

- **Mode connecté simulé** : l'authentification est gérée par un simple bouton, sans intégration à un système d'identité réel
- **Base de connaissances statique** : toute mise à jour nécessite une régénération manuelle de la base
- **API Groq plan gratuit** : 30 requêtes/min, 6 000 tokens/min — suffisant pour un usage modéré, limitant pour un déploiement public à forte fréquentation
- **Données des diplômés non incluses** : les fichiers `markdown_files/master_esa_diplomes_*.md` (annuaire des 642 alumni sur 22 promotions) ne sont pas versionnés dans ce dépôt pour des raisons de confidentialité. Leur absence n'empêche pas le lancement du chatbot : les questions relatives aux diplômés retourneront simplement une réponse "information non disponible".
- **Google Sheets non configuré** : le fichier `google_credentials.json` (clé du compte de service Google) n'est pas inclus dans ce dépôt. Là encore, le chatbot fonctionne normalement sans lui : les boutons de feedback 👍/👎 s'affichent mais les votes ne sont pas sauvegardés.

---

*Master ESA — Université d'Orléans — 2025-2026*
