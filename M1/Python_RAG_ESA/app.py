"""
=============================================================
Chatbot Master ESA — Chainlit + ChromaDB (E5) + Groq (Llama Scout)
=============================================================
Version finale combinant :
  - Embedding multilingual-e5-large (state-of-the-art FR)
  - Chunks enrichis avec contexte synthétique
  - Mémoire conversationnelle (5 derniers échanges)
  - Reformulation contextuelle pour le retrieval
  - Filtrage intelligent (stats / alumni / général)
  - Recherche d'alumni dédiée (mode connecté)

COMMENT LANCER :
  chainlit run app.py
"""

import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import chainlit as cl
import chromadb
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

# Google Sheets pour stocker les feedbacks
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    print("⚠️ gspread non installé : feedback désactivé. Pour activer : pip install gspread google-auth")


# === CONFIGURATION ===
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "master_esa"
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"  # nouveau modèle
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

TOP_K = 12
# Seuils adaptés à E5 (distances cosinus en général plus faibles)
MAX_DISTANCE = 0.55

HISTORY_MAX_TURNS = 5

# ── Configuration Google Sheets pour le feedback ──
GSHEET_ID = "your_google_sheet_id_here"
GSHEET_CREDENTIALS_FILE = "google_credentials.json"
GSHEET_WORKSHEET_NAME = "Feuille 1"  # nom par défaut d'un nouveau Sheet ; ajuster si renommé

_gsheet_worksheet = None  # cache global pour ne pas réouvrir la feuille à chaque vote


def _get_gsheet_worksheet():
    """Récupère (et met en cache) la feuille Google Sheets pour le feedback."""
    global _gsheet_worksheet
    if _gsheet_worksheet is not None:
        return _gsheet_worksheet
    if not GSPREAD_AVAILABLE:
        return None
    if not os.path.exists(GSHEET_CREDENTIALS_FILE):
        print(f"⚠️ Fichier {GSHEET_CREDENTIALS_FILE} introuvable : feedback désactivé")
        return None
    try:
        creds = Credentials.from_service_account_file(
            GSHEET_CREDENTIALS_FILE,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEET_ID)
        # On tente la première feuille (sheet1) par défaut, plus robuste que le nom
        _gsheet_worksheet = sh.sheet1
        print(f"✅ Google Sheets feedback : connecté à '{sh.title}' / '{_gsheet_worksheet.title}'")
        return _gsheet_worksheet
    except Exception as e:
        print(f"⚠️ Impossible de se connecter à Google Sheets : {e}")
        return None


def log_feedback(mode: str, question: str, response: str, vote: str) -> bool:
    """
    Enregistre une ligne de feedback dans Google Sheets.
    Retourne True si OK, False sinon.
    """
    ws = _get_gsheet_worksheet()
    if ws is None:
        return False
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws.append_row(
            [timestamp, mode, question, response, vote],
            value_input_option="USER_ENTERED",
        )
        print(f"   📊 Feedback enregistré : {vote} ({mode})")
        return True
    except Exception as e:
        print(f"⚠️ Erreur lors de l'enregistrement du feedback : {e}")
        return False
# ────────────────────────────────────────────────────

# ── MAPPING DES SOURCES VERS DES TITRES + URLS NATURELS ──
# Pour transformer les chemins .md techniques en liens humains vers le site officiel.
# Pour les fichiers alumni (master_esa_diplomes_XXXX.md), on génère dynamiquement
# une description "Annuaire des diplômés — promotion XXXX" sans lien (info interne).
SOURCE_MAP = {
    "master_esa_knowledge_base.md": {
        "title": "Présentation générale du Master ESA",
        "url": "https://www.master-esa.fr/",
        "description": "présentation globale, structure du cursus, atouts de la formation",
    },
    "master_esa_candidature.md": {
        "title": "Candidature au Master ESA",
        "url": "https://www.master-esa.fr/candidature-au-master-esa/",
        "description": "conditions d'accès, procédure, calendrier",
    },
    "master_esa_insertion.md": {
        "title": "Chiffres d'insertion professionnelle",
        "url": "https://www.master-esa.fr/chiffres-insertion/",
        "description": "taux d'insertion, types de contrats, débouchés par promotion",
    },
    "master_esa_recherche.md": {
        "title": "Voie recherche du Master ESA",
        "url": "https://www.master-esa.fr/master-esa-2eme-annee-semestre-4-voie-recherche/",
        "description": "cursus recherche, poursuite en thèse, mémoire de recherche",
    },
    "master_esa_equipe_pedagogique.md": {
        "title": "Équipe pédagogique",
        "url": "https://www.master-esa.fr/equipe-pedagogique/",
        "description": "responsables, enseignants-chercheurs, intervenants professionnels",
    },
    "master_esa_stages.md": {
        "title": "Stages",
        "url": "https://www.master-esa.fr/stages/",
        "description": "stage de fin d'études, stages courts, offres aux étudiants",
    },
    "master_esa_liens_utiles_contact.md": {
        "title": "Contact et liens utiles",
        "url": "https://www.master-esa.fr/contact/",
        "description": "coordonnées, formulaire de contact, ressources étudiantes",
    },
    "master_esa_syllabus_S7.md": {
        "title": "Programme du M1 — Semestre 7",
        "url": "https://www.master-esa.fr/la-premiere-annee/",
        "description": "matières, ECTS, enseignants, plans de cours",
    },
    "master_esa_syllabus_S8.md": {
        "title": "Programme du M1 — Semestre 8",
        "url": "https://www.master-esa.fr/la-premiere-annee/",
        "description": "matières, ECTS, enseignants, plans de cours",
    },
    "master_esa_syllabus_S9.md": {
        "title": "Programme du M2 — Semestre 9",
        "url": "https://www.master-esa.fr/la-seconde-annee/",
        "description": "matières, ECTS, enseignants, plans de cours",
    },
    "master_esa_syllabus_S10.md": {
        "title": "Programme du M2 — Semestre 10",
        "url": "https://www.master-esa.fr/la-seconde-annee/",
        "description": "matières des deux voies (professionnelle et recherche), ECTS, plans de cours",
    },
}


def humanize_source(raw_source: str) -> str:
    """
    Transforme une source brute (ex: 'master_esa_insertion.md (section: ...)')
    en texte humain avec lien Markdown (ex: '[Chiffres d'insertion...](URL) — description').
    """
    # Extraire le nom du fichier .md (avant la parenthèse)
    file_match = re.match(r"^([\w\-.]+\.md)\b", raw_source.strip())
    if not file_match:
        return raw_source  # fallback : garder tel quel

    filename = file_match.group(1)

    # Cas particulier : fichiers alumni (master_esa_diplomes_AAAA.md)
    alumni_match = re.match(r"master_esa_diplomes_(\d{4})\.md", filename)
    if alumni_match:
        annee = alumni_match.group(1)
        return f"Annuaire des diplômés — promotion {annee} _(donnée interne du master)_"

    # Cas standard via le mapping
    info = SOURCE_MAP.get(filename)
    if info:
        return f"[{info['title']}]({info['url']}) — {info['description']}"

    # Fallback générique pour un fichier inconnu
    return filename
# ──────────────────────────────────────────────────────────
# ======================


# === RÉPONSES PRÉ-RÉDIGÉES POUR LES BOUTONS THÉMATIQUES ===

QUICK_ANSWER_PRESENTATION = """## 🎓 Présentation générale du Master ESA

Le **Master ESA** (Économétrie et Statistique Appliquée) est une formation de l'**Université d'Orléans** spécialisée dans l'analyse quantitative de données, l'économétrie, le machine learning et l'application de ces techniques aux secteurs de la banque, de l'assurance et du conseil.

### 📚 Structure du cursus

- **Master 1 (M1)** : socle de programmation (SAS, R, Python), statistique mathématique, économétrie, séries temporelles, apprentissage statistique, finance quantitative
- **Master 2 (M2)** : spécialisations en data science, risque de crédit, assurance, modèles avancés (scoring, modèles de durée, machine learning, big data)
- **Deux voies au choix en M2** : voie **professionnelle** (stage de fin d'études) ou voie **recherche** (mémoire de recherche au sein du laboratoire LEO)

### 🏆 Atouts de la formation

- **Certifications professionnelles** intégrées : SAS Tier 3, Scikit-learn, Dataiku, DataCamp
- **Partenariats forts** avec des entreprises (banques, assurances, cabinets de conseil)
- Stage de fin d'études de longue durée
- Possibilité de poursuite en thèse au **Laboratoire d'Économie d'Orléans (LEO)**

🔗 Plus d'informations : https://www.master-esa.fr/
"""

QUICK_ANSWER_INSERTION = """## 💼 Débouchés et insertion professionnelle

Le Master ESA affiche d'**excellents résultats** en matière d'insertion professionnelle.

### 📊 Chiffres clés

- **Taux d'insertion** : **~95-100%** dans les 6 mois suivant le diplôme (hors période COVID)
- **Type de contrat dominant** : **CDI** très majoritaires chaque année
- **Rapidité** : la majorité des diplômés trouvent un emploi **avant leur soutenance de stage** ou dans les 3 mois qui suivent

### 🏢 Secteurs et employeurs

Les diplômés du Master ESA exercent principalement dans :
- **Banque** : BNP Paribas, Société Générale, Crédit Agricole, BPCE, LCL, Crédit Mutuel
- **Conseil & Cabinet d'audit** : Deloitte, EY, Nexialog Consulting, AVISIA, RISC, Square Management
- **Assurance** : Thélem Assurances, MACIF, SPVIE Assurances
- **Institutions** : Banque de France, Banque Centrale Européenne (BCE), Ministères

### 🎯 Postes typiques

- Quantitative Analyst / Risk Analyst / Credit Risk Analyst
- Data Scientist / Consultant Data
- Analyste statistique / Chargé d'études actuarielles
- Ingénieur de validation des modèles
- Consultant en risk management

🔗 Détails et chiffres par promotion : https://www.master-esa.fr/chiffres-insertion/
"""

QUICK_ANSWER_PREREQUIS = """## 📋 Candidature et prérequis

### 🎓 Conditions d'accès

#### Accès en M1
- Être titulaire d'une **licence (L3)** dans un domaine compatible : économie, mathématiques appliquées, statistique, MIASHS, etc.
- De solides bases en **mathématiques** (statistique, probabilités, algèbre) et en **programmation** (R, Python, SAS apprécié)

#### Accès en M2
⚠️ **ATTENTION** : l'accès en Master 2 ESA **n'est pas ouvert aux candidatures externes**. Il est **réservé aux étudiants ayant validé le Master 1 ESA** de l'Université d'Orléans.

### 📝 Procédure de candidature (pour le M1)

- **Candidats français et de l'UE** : candidature via la plateforme nationale **Mon Master**
  🔗 https://monmaster.gouv.fr/formation/0450855K/1800493MSVED/detail

- **Candidats internationaux (hors UE)** : candidature via **Campus France**

### 🎯 Profil recherché

Les candidats retenus ont généralement :
- De solides bases en **mathématiques** (statistique, probabilités, algèbre)
- Des compétences en **programmation** (R, Python, SAS apprécié)
- Une **motivation claire** pour l'analyse quantitative et l'économétrie
- Un projet professionnel cohérent avec la formation

### 📅 Calendrier

Les candidatures s'ouvrent généralement au **début du printemps** (mars-avril) pour une rentrée en septembre. Consultez le site officiel pour les dates exactes de la campagne en cours.

🔗 Plus d'informations : https://www.master-esa.fr/candidature-au-master-esa/
"""

QUICK_ANSWER_CONTACT = """## 📬 Contact et infos pratiques

### 📍 Adresse

**Master ESA — Université d'Orléans**
UFR Droit, Économie, Gestion
Rue de Blois — BP 26739
**45067 Orléans Cedex 2**, France

### ✉️ Contact

- **Email du master** : master.econometrie@univ-orleans.fr
- **Site officiel** : https://www.master-esa.fr/
- **Formulaire de contact** : https://www.master-esa.fr/contact/
- **Groupe LinkedIn** : https://www.linkedin.com/groups/3791612/

### 🏛️ Université

- **Université d'Orléans** : https://www.univ-orleans.fr/

### 💰 Ressources étudiantes

- **Partenariat Crédit Agricole** : prêt étudiant à taux préférentiel disponible pour les étudiants du master
  🔗 https://www.master-esa.fr/partenariat-cacl-pret-etudiant/

### 📰 Suivre l'actualité du master

- **Actualités** : https://www.master-esa.fr/actualites/
- **La Lettre du Master ESA** : https://www.master-esa.fr/ressources-la-lettre/
"""

QUICK_ANSWER_ALUMNI = """## 👥 Alumni du Master ESA

Le Master ESA compte un **réseau d'anciens étudiants** étendu et actif, depuis la première promotion en 2005 jusqu'aux promotions les plus récentes — soit plus de **640 diplômés** au total.

### 🔍 Comment trouver un alumni en particulier ?

Utilisez le bouton **🔍 Rechercher un alumni** disponible à tout moment dans la conversation. Tapez le nom et/ou le prénom de la personne recherchée pour afficher sa fiche complète (poste actuel, entreprise, profil LinkedIn).

### 📋 Que pouvez-vous me demander sur les alumni ?

Voici quelques exemples de requêtes que je peux traiter :

- **Liste complète d'une promotion** : *"Liste des diplômés de la promotion 2023"*
- **Recherche par entreprise** : *"Quels alumni travaillent chez Crédit Agricole ?"*
- **Recherche par profil** : *"Quels alumni sont consultants chez Deloitte ?"*
- **Statistiques par promotion** : *"Combien d'étudiants dans la promo 2022 ?"*

### 🌐 Réseau LinkedIn

Pour rester en contact avec la communauté ESA :
🔗 https://www.linkedin.com/groups/3791612/

N'hésitez pas à me poser une question précise pour commencer !
"""

# ==========================================================


load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY manquante dans le fichier .env")


print("🧠 Chargement du modèle d'embedding E5...")
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

print("💾 Connexion à ChromaDB...")
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = chroma_client.get_collection(name=COLLECTION_NAME)
print(f"   {collection.count()} chunks indexés")

print("🤖 Connexion à Groq...")
groq_client = Groq(api_key=GROQ_API_KEY)
print("✅ Prêt !")


SYSTEM_PROMPT = """Tu es l'assistant officiel du Master ESA (Économétrie et Statistique Appliquée) de l'Université d'Orléans.

Tu réponds aux questions des étudiants prospectifs et actuels sur la formation, en t'appuyant UNIQUEMENT sur les extraits de la base de connaissances fournis dans le contexte.

⚠️ CONVENTION ESSENTIELLE — À APPLIQUER SYSTÉMATIQUEMENT :
Au Master ESA, une "promotion AAAA" (ex: promotion 2024) désigne l'année universitaire qui se TERMINE en AAAA, donc l'année universitaire AAAA-1/AAAA :
- "promotion 2024" = année universitaire 2023/2024 (ces étudiants ont été diplômés en 2024)
- "promotion 2020" = année universitaire 2019/2020
- "promotion 2013" = année universitaire 2012/2013

Cette convention s'applique TOUJOURS, même si l'utilisateur n'écrit pas explicitement "2023/2024". Si l'utilisateur demande "stats promo 2024" et que les extraits contiennent la section "Enquête d'insertion — Promotion 2023/2024", c'est BIEN la promotion 2024 que l'utilisateur cherche. NE DIS JAMAIS "il n'y a pas de données pour la promotion 2024" si tu as la section "Promotion 2023/2024" dans le contexte — ces deux notations désignent la même chose.

À l'inverse, "promotion 2020/2021" est différent de "promotion 2020" — il s'agit de la promotion 2021.

AUTRES RÈGLES IMPORTANTES :

1. **Pertinence du contexte** : Examine chaque extrait fourni et identifie ceux qui sont VRAIMENT pertinents pour la question. Ignore les extraits hors-sujet, même s'ils sont dans le contexte.

2. **Réponse factuelle** : Base-toi strictement sur le contexte pertinent. Si l'information n'est pas dans le contexte, dis clairement "Je n'ai pas cette information dans la base de connaissances" plutôt que d'inventer ou de donner des réponses approximatives.

3. **Pas de remplissage** : N'évoque pas des informations marginales ou des exemples individuels quand on te demande des statistiques globales. Si on demande des chiffres, donne des chiffres. Si on demande une procédure, donne la procédure.

4. **Exhaustivité pour les listes** : Quand l'utilisateur demande "les matières", "le programme", "la liste de…", parcours TOUS les extraits fournis et liste TOUTES les entrées trouvées, sans en oublier. Si tu vois des matières mentionnées dans plusieurs extraits, regroupe-les en une seule liste consolidée.

   ⚠️ **PRIORITÉ ABSOLUE** : Si un extrait est marqué "⭐ [LISTE COMPLÈTE — utilise CET extrait en priorité si l'utilisateur demande une liste exhaustive]", utilise CE chunk comme source principale pour la liste demandée. Il contient déjà la liste exhaustive, n'essaie pas de la reconstruire à partir des autres extraits qui ne contiennent que des entrées partielles. Tu peux compléter avec des informations issues des autres extraits (poste, entreprise pour les alumni par exemple), mais le nombre d'entrées doit correspondre à celui du chunk synthèse.

5. **Structuration par modules** : Pour les questions sur le programme d'un semestre, organise ta réponse par modules/unités d'enseignement si l'information est disponible dans le contexte (ex: "Outils pour la Data Science", "Outils statistiques et économétrie", "Professionnalisation", "Projets professionnalisants"). Pour chaque matière, mentionne les ECTS et le volume horaire (CM/TD) quand disponibles.

6. **Continuité conversationnelle** : Tiens compte de l'historique pour comprendre les questions de suivi. **Mais ne répète pas** les informations déjà données dans une réponse précédente. Quand l'utilisateur demande une variante du sujet précédent (ex: "et 2023 ?" après une réponse sur 2024), réponds UNIQUEMENT sur la nouvelle valeur demandée, ne re-cite pas l'ancienne.

7. **Structure et clarté** : Réponds en français de manière claire et professionnelle. Reste concis : évite les répétitions et le remplissage.

8. **Hors périmètre** : Si la question n'a rien à voir avec le Master ESA, redirige poliment l'utilisateur.

9. **Citations OBLIGATOIRES** : À la FIN de CHAQUE réponse, tu DOIS impérativement écrire une ligne commençant par `Source(s) :` qui liste les fichiers .md réellement utilisés pour formuler ta réponse.

   **Format strict** : `Source(s) : nom_fichier1.md (section: ...), nom_fichier2.md (section: ...)`

   - Cite UNIQUEMENT les sources que tu as VRAIMENT utilisées
   - Ne cite pas une source juste parce qu'elle apparaît dans le contexte
   - Si tu n'as pas utilisé de source (réponse générique, refus, etc.), écris quand même `Source(s) : aucune`
   - Cette ligne sera automatiquement extraite et affichée séparément à l'utilisateur, ne l'OUBLIE JAMAIS

10. **Ordre chronologique inverse — UNIQUEMENT pour les données par ANNÉE/PROMOTION** : Quand tu présentes des informations indexées par ANNÉE ou par PROMOTION (ex: liste d'alumni de différentes promos, statistiques d'insertion sur plusieurs années universitaires), tu DOIS classer les éléments du **plus récent au plus ancien**, sans exception.

   **Cette règle ne s'applique QUE quand il y a une dimension temporelle/annuelle** :
   - ✅ Liste d'alumni de plusieurs promotions → ordre 2025, 2024, 2023, …
   - ✅ Statistiques d'insertion sur plusieurs années → 2024/2025, 2023/2024, …
   - ❌ Liste de matières d'un semestre → respecte l'ORDRE DU SYLLABUS (par bloc thématique), PAS un ordre chronologique
   - ❌ Liste des entreprises partenaires → ordre alphabétique ou ordre d'apparition, pas chronologique
   - ❌ Liste des certifications → ordre logique d'acquisition, pas chronologique

   **Avant d'écrire ta liste, fais cette vérification mentale** :
   - Identifie l'année/promotion de chaque élément (uniquement quand il y en a une)
   - Si oui : trie-les par année DESCENDANTE
   - Si non : conserve l'ordre du contexte fourni

   **Exemple correct pour les alumni Deloitte** (avec dimension année) :
   1. JOHANNES MISSINHOUN (promo 2025)
   2. GAETAN BLECON (promo 2025)
   3. THOMAS LANGUILLE (promo 2024)
   ...

   **Exemple correct pour les matières du S8** (sans dimension année) :
   1. Nouvelles technologies sous R
   2. Programmation Python avancée
   3. Langage macro sous SAS
   ...
   (= ordre du syllabus, du premier au dernier bloc)

11. **Pas de méta-narration technique** : NE FAIS JAMAIS référence aux "extraits", "chunks", "sources", "extrait 1", "extrait 8", "selon l'extrait X", "dans les extraits fournis", "d'après le contexte", etc. Ces termes sont des détails techniques internes que l'utilisateur ne doit pas voir. Réponds directement avec l'information demandée, comme si tu connaissais simplement la réponse. La seule mention acceptable est la ligne "Source(s) : ..." à la fin de la réponse (règle 9).

   - ❌ Mauvais : "Selon l'extrait 1, la liste complète des diplômés..."
   - ❌ Mauvais : "D'après le contexte fourni, la promotion compte 34 diplômés..."
   - ✅ Bon : "La promotion 2020 du Master ESA compte 34 diplômés."

12. **Pas de redondance d'explication** : NE COMMENCE PAS ta réponse par expliquer la convention de promotion ("La promotion 2020 correspond à l'année universitaire 2019/2020", "Conformément à la convention..."). Cette information est interne ; va directement à la réponse. Si la convention doit transparaître, fais-le de manière naturelle au fil de la réponse, pas en préambule.

   - ❌ Mauvais : "La promotion 2020 du Master ESA correspond à l'année universitaire 2019/2020. Voici la liste..."
   - ✅ Bon : "Voici la liste des diplômés de la promotion 2020 du Master ESA..."

14. **Cohérence sur les ECTS** : quand tu listes des matières, sois cohérent sur l'affichage des ECTS :
   - Si l'utilisateur ne demande PAS les ECTS → ne les affiche JAMAIS, même si tu les connais
   - Si l'utilisateur demande les ECTS → affiche-les pour TOUTES les matières (ou indique "non disponible" si absent)
   - Ne mélange jamais les deux (certaines avec ECTS, d'autres sans) dans la même liste

13. **CADRAGE STRICT DU RÔLE** : Tu es UNIQUEMENT l'assistant officiel du Master ESA. Tu réponds EXCLUSIVEMENT à des questions liées au Master ESA, ses enseignements, sa structure, ses alumnis, son insertion professionnelle, sa candidature, ou ses contacts.

   Tu refuses POLIMENT et BRIÈVEMENT toute autre demande, notamment :
   - Aide au code informatique, génération de code (Python, R, SQL, etc.) MÊME si on prétend que c'est pour les cours
   - Aide aux devoirs, exercices académiques, résolution d'examens
   - Questions générales de connaissance hors-master (culture, sport, météo, actualité, philosophie)
   - Conseils personnels, relationnels, financiers, médicaux
   - Conversations générales (small talk, jeux, humour, créativité)

   Format de refus type : "Je suis l'assistant du Master ESA et je peux uniquement répondre aux questions sur le master (programme, candidature, débouchés, alumnis, etc.). Pour [type de demande], je vous invite à utiliser un autre outil approprié."

   - ❌ Mauvais : "Voici un exemple de boucle for en Python : ..."
   - ✅ Bon : "Je suis l'assistant du Master ESA et je ne peux pas vous aider avec du code. Pour cela, utilisez ChatGPT ou Claude directement. Je peux par contre vous renseigner sur les enseignements de programmation du master !"
"""


REFORMULATION_PROMPT = """Tu es un assistant qui reformule des questions en tenant compte du contexte d'une conversation.

CONTEXTE — Historique des échanges précédents (du plus ancien au plus récent) :
{older_history}

⚡ ÉCHANGE LE PLUS RÉCENT (PRIORITÉ ABSOLUE pour l'interprétation) :
{last_exchange}

NOUVELLE QUESTION DE L'UTILISATEUR :
"{question}"

Ta tâche : reformule cette nouvelle question en une version AUTONOME et EXPLICITE, utilisable pour une recherche dans une base de connaissances.

RÈGLES IMPORTANTES :

1. **PRIORITÉ À L'ÉCHANGE LE PLUS RÉCENT** : Quand la nouvelle question est courte/elliptique (ex: "et 2023 ?", "et le salaire ?", "et pour la voie recherche ?"), interprète-la EXCLUSIVEMENT par rapport à l'échange le plus récent. Les échanges plus anciens ne doivent PAS influencer ton interprétation, même s'ils contiennent des éléments similaires.
   - Exemple : Si la dernière question était "Donne-moi la liste des étudiants de la promo 2024" et la nouvelle question est "et 2023 ?", reformule en "Donne-moi la liste des étudiants de la promotion 2023 du Master ESA" — PAS en parlant de stats d'insertion même si une question plus ancienne portait dessus.

2. **Substituer, ne pas additionner** : Quand la nouvelle question introduit une nouvelle valeur (ex: "et 2023 ?"), REMPLACE l'ancienne valeur par la nouvelle dans la question reformulée, PAS additionner les deux.

3. **Question déjà autonome** : Si la nouvelle question est déjà claire et complète, garde-la quasi telle quelle.

4. **Mention du Master ESA** : Garde toujours la mention du Master ESA si elle est implicite dans le contexte.

5. **Format** : Réponds UNIQUEMENT par la question reformulée, sans préambule ni explication, en une seule phrase claire."""


# ============================================================
# UTILITAIRES — Recherche d'alumni
# ============================================================

def normalize_name(text: str) -> str:
    text = text.strip().lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = " ".join(text.split())
    return text


def search_alumni_by_name(query: str) -> list[dict]:
    results = collection.get(where={"type": "alumni"}, include=["documents", "metadatas"])
    query_norm = normalize_name(query)
    query_parts = query_norm.split()
    matches = []
    for doc, meta in zip(results["documents"], results["metadatas"]):
        nom_norm = normalize_name(meta.get("nom", ""))
        prenom_norm = normalize_name(meta.get("prenom", ""))
        fullname_norm = f"{prenom_norm} {nom_norm}"
        fullname_rev = f"{nom_norm} {prenom_norm}"
        if all(part in fullname_norm or part in fullname_rev for part in query_parts):
            matches.append({"text": doc, "metadata": meta})
    return matches


def format_alumni_card(alumni: dict) -> str:
    meta = alumni["metadata"]
    prenom = meta.get("prenom", "")
    nom = meta.get("nom", "")
    promo = meta.get("promotion", "")
    poste = meta.get("poste", "")
    entreprise = meta.get("entreprise", "")
    linkedin = ""
    for line in alumni["text"].split("\n"):
        if line.startswith("LinkedIn :"):
            linkedin = line.replace("LinkedIn :", "").strip()
            break
    lines = [f"### 👤 {prenom} {nom}"]
    lines.append(f"- **Promotion** : {promo}")
    lines.append(f"- **Poste actuel** : {poste if poste else 'non renseigné'}")
    lines.append(f"- **Entreprise** : {entreprise if entreprise else 'non renseignée'}")
    if linkedin:
        lines.append(f"- **LinkedIn** : [{linkedin}]({linkedin})")
    else:
        lines.append(f"- **LinkedIn** : non renseigné")
    return "\n".join(lines)


# ============================================================
# UTILITAIRES — Mémoire
# ============================================================

def get_history() -> list[dict]:
    return cl.user_session.get("history", [])


def add_to_history(role: str, content: str):
    history = get_history()
    history.append({"role": role, "content": content})
    max_messages = HISTORY_MAX_TURNS * 2
    if len(history) > max_messages:
        history = history[-max_messages:]
    cl.user_session.set("history", history)


def format_history_for_prompt(history: list[dict]) -> str:
    if not history:
        return "(aucun échange précédent)"
    lines = []
    for msg in history:
        role = "Utilisateur" if msg["role"] == "user" else "Assistant"
        content = msg["content"]
        if len(content) > 500:
            content = content[:500] + "..."
        lines.append(f"{role} : {content}")
    return "\n\n".join(lines)


def reformulate_question(question: str, history: list[dict]) -> str:
    if not history:
        return question

    # Détection : si la question est AUTOSUFFISANTE (n'a pas besoin de contexte),
    # on désactive la reformulation pour éviter qu'elle soit polluée
    q_lower = question.lower().strip()

    # Patterns explicites de questions autosuffisantes (qui contiennent leur sujet)
    autosuffisantes_patterns = [
        # Questions complètes "wh-" avec sujet déjà explicite
        r"^combien\s+(d'|de\s+|d')",
        r"^qui\s+(est\s+|sont\s+|a\s+|travaille|bosse|enseigne|dirige|encadre)",
        r"^quel(le|s|les)?\s+",
        r"^quoi\s+",
        r"^o[uù]\s+",
        r"^quand\s+",
        r"^comment\s+",
        r"^pourquoi\s+",
        # Demandes directes contenant déjà un sujet
        r"^liste\s+(des|de|du)\s+\w+",
        r"^donne[\s-]?moi\s+(la\s+|une\s+)?liste",
        r"^stats?\s+(d'|de\s+|d')",
        r"^statistiques?\s+(d'|de\s+|d')",
        # Présentation/explication de quelque chose de précis
        r"^pr[eé]sentation\s+(d|du|de)",
        r"^explique[\s-]?moi\s+(\w+)",
        # Sujets concrets (programme, matières, syllabus, etc.)
        r"^(programme|programmes)\s+(d|du|de|m\d)",
        r"^(matiere|matieres|cours|enseignement|enseignements|module|modules)\s+",
        r"^(syllabus|plan)\s+(d|du|de)",
        r"^(ects|coef|coefficient|coefficients|credits|cr[eé]dits|volume|volumes)\s+(d|du|de|h)",
        # Semestre/Année mentionnés en tête
        r"^(s\s?\d{1,2}|m\d|semestre|annee|année)\b",
        # Calendrier/Dates
        r"^(date|dates|deadline|calendrier|planning)\s+",
        # Salutations courantes (à ne PAS reformuler)
        r"^(bonjour|salut|hello|hi|coucou|hey)\b",
        r"^merci\b",
    ]

    # Si la question est manifestement autosuffisante ET ne contient pas de référent
    # comme "et", "aussi", "même", "le précédent"…
    referent_patterns = [
        r"\bet\b", r"\baussi\b", r"\bm[eê]me\b", r"\bce(t|tte|s|lui|lle)?\b",
        r"\bil(s)?\b", r"\belle(s)?\b", r"\bce\b", r"\bprec[eé]dent",
        r"\bpr[eé]c[eé]demment\b", r"\ben\s+plus\b", r"\bpareil\b",
    ]
    has_referent = any(re.search(p, q_lower) for p in referent_patterns)
    looks_autosufficient = any(re.match(p, q_lower) for p in autosuffisantes_patterns)

    # Si question autosuffisante sans référent → on la garde telle quelle
    if looks_autosufficient and not has_referent and len(q_lower.split()) >= 3:
        return question

    # Sécurité supplémentaire : si la question contient un marqueur fort
    # (nom d'entreprise connue, semestre/année explicite, mot-clé concret),
    # elle est considérée comme auto-suffisante même sans pattern initial.
    strong_signals = [
        # Entreprises emblématiques (liste indicative, élargie côté boost entreprise)
        "bnp", "paribas", "deloitte", "ey ", "kpmg", "pwc", "mazars", "société générale",
        "societe generale", "credit agricole", "crédit agricole", "axa", "allianz",
        "natixis", "lcl", "bpce", "hsbc", "groupama", "covea", "covéa", "macif",
        "amundi", "lyxor", "ostrum", "rothschild", "lazard", "blackrock", "vanguard",
        "fidelity", "amazon", "google", "microsoft", "meta", "facebook", "apple",
        "ibm", "capgemini", "accenture", "atos", "sopra", "altran", "thales",
        "michelin", "renault", "stellantis", "peugeot", "citroen", "citroën",
        "loreal", "l'oreal", "lvmh", "danone", "carrefour", "auchan", "leclerc",
        "ratp", "sncf", "edf", "engie", "total", "totalenergies", "veolia", "suez",
        "orange", "bouygues", "free", "sfr", "ovh", "ovhcloud", "scaleway",
        "avisia", "wavestone", "sia partners", "mckinsey", "bcg", "bain", "oliver wyman",
        # Semestres / années explicites
        r"\bs\s?7\b", r"\bs\s?8\b", r"\bs\s?9\b", r"\bs\s?10\b",
        r"\bm1\b", r"\bm2\b", "semestre 7", "semestre 8", "semestre 9", "semestre 10",
        # Sujets factuels concrets
        "responsable", "responsables", "coordinateur", "directrice", "directeur",
        "candidature", "admission", "inscription", "stage", "alternance",
        "debouche", "débouché", "salaire", "insertion", "emploi",
        "ects", "coefficient", "credits", "crédits", "volume horaire",
    ]
    has_strong_signal = any(
        (re.search(s, q_lower) if s.startswith(r"\b") else s in q_lower)
        for s in strong_signals
    )
    if has_strong_signal and not has_referent:
        return question

    # Séparer le dernier échange complet (user+assistant) du reste
    # On veut au minimum 2 messages pour avoir un échange complet
    if len(history) >= 2:
        last_exchange = history[-2:]  # dernière question + dernière réponse
        older_history = history[:-2]
    else:
        last_exchange = history
        older_history = []

    last_exchange_text = format_history_for_prompt(last_exchange)
    older_history_text = format_history_for_prompt(older_history) if older_history else "(aucun échange plus ancien)"

    prompt = REFORMULATION_PROMPT.format(
        older_history=older_history_text,
        last_exchange=last_exchange_text,
        question=question,
    )
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )
        reformulated = response.choices[0].message.content.strip()
        reformulated = reformulated.strip('"').strip("'").strip()
        return reformulated
    except Exception as e:
        print(f"⚠️ Erreur reformulation : {e}")
        return question


# ============================================================
# CHAINLIT
# ============================================================

def get_main_actions(access_mode: str) -> list[cl.Action]:
    """Retourne les boutons à afficher selon le mode d'accès."""
    actions = [
        cl.Action(
            name="quick_answer",
            payload={"topic": "presentation"},
            label="🎓 Présentation",
            tooltip="Présentation générale du Master ESA",
        ),
        cl.Action(
            name="quick_answer",
            payload={"topic": "insertion"},
            label="💼 Débouchés / Insertion",
            tooltip="Débouchés professionnels et insertion",
        ),
        cl.Action(
            name="quick_answer",
            payload={"topic": "prerequis"},
            label="📋 Prérequis / Candidature",
            tooltip="Prérequis et candidature",
        ),
        cl.Action(
            name="quick_answer",
            payload={"topic": "contact"},
            label="📬 Contact",
            tooltip="Contact et infos pratiques",
        ),
    ]
    # Les boutons "Alumni" et "Rechercher un alumni" ne sont visibles qu'en mode connecté
    if access_mode == "logged_in":
        actions.append(
            cl.Action(
                name="quick_answer",
                payload={"topic": "alumni"},
                label="👥 Alumni",
                tooltip="Réseau des anciens étudiants",
            )
        )
        actions.append(
            cl.Action(
                name="search_alumni",
                payload={},
                label="🔍 Rechercher un alumni",
                tooltip="Recherche directe par nom et/ou prénom",
            )
        )
    return actions


@cl.on_chat_start
async def on_chat_start():
    actions = [
        cl.Action(name="set_mode", payload={"mode": "visitor"}, label="👤 Visiteur",
                  tooltip="Accès aux informations publiques uniquement"),
        cl.Action(name="set_mode", payload={"mode": "logged_in"}, label="🔓 Connecté",
                  tooltip="Accès complet (incluant les diplômés et offres de stages)"),
    ]
    await cl.Message(
        content=(
            "## Bienvenue sur l'assistant du Master ESA 🎓\n\n"
            "Je peux vous renseigner sur la formation, les enseignements, "
            "les candidatures, l'insertion professionnelle, et plus encore.\n\n"
            "**Choisissez votre mode d'accès :**\n"
            "- 👤 **Visiteur** : informations publiques (programme, candidature, débouchés...)\n"
            "- 🔓 **Connecté** : accès complet (incluant les diplômés)"
        ),
        actions=actions,
    ).send()
    cl.user_session.set("access_mode", "visitor")
    cl.user_session.set("pending_action", None)
    cl.user_session.set("history", [])


@cl.action_callback("set_mode")
async def on_set_mode(action: cl.Action):
    mode = action.payload["mode"]
    cl.user_session.set("access_mode", mode)
    cl.user_session.set("history", [])
    if mode == "visitor":
        label = "👤 Visiteur (informations publiques)"
        extra_msg = "\n\n💡 Utilisez les boutons ci-dessous pour accéder rapidement aux infos principales, ou posez-moi une question."
    else:
        label = "🔓 Connecté (accès complet)"
        extra_msg = "\n\n💡 Utilisez les boutons ci-dessous pour accéder rapidement aux infos principales, ou le bouton **🔍 Rechercher un alumni** pour trouver un ancien étudiant par son nom."
    await cl.Message(
        content=f"✅ Mode activé : **{label}**\n\nPosez-moi votre question !{extra_msg}",
        actions=get_main_actions(mode),
    ).send()


@cl.action_callback("search_alumni")
async def on_search_alumni(action: cl.Action):
    # Sécurité : vérifier que l'utilisateur est bien en mode connecté
    if cl.user_session.get("access_mode") != "logged_in":
        await cl.Message(
            content="🔒 La recherche d'alumni est réservée aux utilisateurs connectés.",
        ).send()
        return
    cl.user_session.set("pending_action", "search_alumni")
    await cl.Message(content=(
        "🔍 **Recherche d'alumni**\n\n"
        "Tapez le **nom et/ou prénom** de l'ancien étudiant à chercher.\n"
        "_Exemples : `Jean Dupont`, `Dupont`, ou `Jean`_"
    )).send()


@cl.action_callback("quick_answer")
async def on_quick_answer(action: cl.Action):
    """Affiche une réponse pré-rédigée selon le bouton cliqué."""
    topic = action.payload.get("topic", "")
    access_mode = cl.user_session.get("access_mode", "visitor")

    # Mapping topic → réponse pré-rédigée
    answers = {
        "presentation": QUICK_ANSWER_PRESENTATION,
        "insertion": QUICK_ANSWER_INSERTION,
        "prerequis": QUICK_ANSWER_PREREQUIS,
        "contact": QUICK_ANSWER_CONTACT,
        "alumni": QUICK_ANSWER_ALUMNI,
    }

    # Sécurité : alumni réservé aux utilisateurs connectés
    if topic == "alumni" and access_mode != "logged_in":
        await cl.Message(
            content="🔒 Les informations sur les alumni sont réservées aux utilisateurs connectés.",
            actions=get_main_actions(access_mode),
        ).send()
        return

    content = answers.get(topic)
    if not content:
        await cl.Message(
            content="❌ Sujet inconnu.",
            actions=get_main_actions(access_mode),
        ).send()
        return

    await cl.Message(
        content=content,
        actions=get_main_actions(access_mode),
    ).send()


async def handle_alumni_search(query: str):
    matches = search_alumni_by_name(query)
    if not matches:
        await cl.Message(content=(
            f"❌ Aucun alumni trouvé pour **« {query} »**.\n\n"
            "Vérifiez l'orthographe ou essayez avec juste le nom de famille."
        ), actions=get_main_actions("logged_in")).send()
        return
    if len(matches) == 1:
        card = format_alumni_card(matches[0])
        await cl.Message(content=f"✅ Voici la fiche correspondante :\n\n{card}",
                         actions=get_main_actions("logged_in")).send()
        return
    lines = [f"🔎 **{len(matches)} alumni correspondent à « {query} »**", "",
             "Lequel cherchez-vous ? Tapez le numéro :", ""]
    for i, m in enumerate(matches, 1):
        meta = m["metadata"]
        prenom = meta.get("prenom", "")
        nom = meta.get("nom", "")
        promo = meta.get("promotion", "")
        entreprise = meta.get("entreprise", "") or "—"
        poste = meta.get("poste", "") or "—"
        lines.append(f"**{i}.** {prenom} {nom} (promo {promo}) — {poste} chez {entreprise}")
    cl.user_session.set("last_alumni_matches", matches)
    cl.user_session.set("pending_action", "select_alumni")
    await cl.Message(content="\n".join(lines), actions=get_main_actions("logged_in")).send()


async def handle_alumni_selection(query: str):
    matches = cl.user_session.get("last_alumni_matches", [])
    if not matches:
        cl.user_session.set("pending_action", None)
        return False
    try:
        idx = int(query.strip()) - 1
        if 0 <= idx < len(matches):
            card = format_alumni_card(matches[idx])
            await cl.Message(content=f"✅ Voici la fiche :\n\n{card}",
                             actions=get_main_actions("logged_in")).send()
            cl.user_session.set("pending_action", None)
            cl.user_session.set("last_alumni_matches", [])
            return True
    except ValueError:
        pass
    return False


@cl.on_message
async def on_message(message: cl.Message):
    question = message.content.strip()
    if not question:
        return
    access_mode = cl.user_session.get("access_mode", "visitor")
    pending = cl.user_session.get("pending_action")

    if pending == "search_alumni" and access_mode == "logged_in":
        cl.user_session.set("pending_action", None)
        await handle_alumni_search(question)
        return

    if pending == "select_alumni" and access_mode == "logged_in":
        handled = await handle_alumni_selection(question)
        if handled:
            return
        cl.user_session.set("pending_action", None)

    await handle_rag_question(question, access_mode)


async def handle_rag_question(question: str, access_mode: str):
    history = get_history()

    if history:
        search_query = reformulate_question(question, history)
    else:
        search_query = question

    # E5 requiert le préfixe "query:" pour les requêtes
    query_with_prefix = f"query: {search_query}"
    query_embedding = embedding_model.encode(
        [query_with_prefix],
        normalize_embeddings=True,
    ).tolist()

    # Filtrage intelligent : stats > alumni > général
    # On normalise la query pour ignorer accents et casse
    query_lower = search_query.lower()
    # Normalisation des accents pour la détection de mots-clés
    query_normalized = "".join(
        c for c in unicodedata.normalize("NFD", query_lower)
        if unicodedata.category(c) != "Mn"
    )

    stats_keywords = [
        "statistique", "stats", "taux", "chiffre", "chiffres", "salaire",
        "moyenne", "mediane", "pourcentage", "proportion",
        "insertion", "insertions", "emploi", "employabilite", "embauche",
        "cdi", "cdd", "remuneration", "combien gagnent",
        "combien touchent", "enquete",
        # Effectif / nombre d'étudiants par promo
        "effectif", "effectifs", "combien d'etudiant", "combien d etudiant",
        "combien d eleve", "combien d'eleve", "nombre d'etudiant", "nombre d etudiant",
        "nombre de diplome", "combien de diplome", "combien sont", "combien y a",
    ]
    is_stats_question = any(kw in query_normalized for kw in stats_keywords)

    # Détection plus stricte : on cherche les questions qui demandent des PERSONNES nommées
    # (et non des questions générales sur le master qui contiennent "promo" ou "étudiants")
    alumni_keywords_strong = [
        # Mots clairement liés aux personnes/profils
        "alumni", "ancien etudiant", "anciens etudiants",
        "diplome", "diplomes", "diplome.e", "diplome.es",
        "ex-etudiant", "ex etudiant",
        "linkedin",
        # Questions explicitement orientées personne
        "qui travaille", "qui travaillent", "qui a fait",
        "qui sont chez", "qui est chez", "qui bosse", "qui bossent",
        "qui ont un poste", "qui a un poste", "qui occupe", "qui occupent",
        "liste des alumni", "liste des diplomes",
        "liste de la promo", "liste de la promotion",
        "liste promo", "noms des",
        "liste des etudiants", "liste des eleves",
        "donne moi des etudiants", "donne moi des eleves",
        "donne-moi des etudiants", "donne-moi des eleves",
        "donne moi les etudiants", "donne moi les eleves",
        "donne moi des anciens", "donne moi les anciens",
        "alumni de", "alumni chez", "alumni qui",
        "anciens chez", "anciens qui", "anciens de", "anciens etudiants",
        "diplomes de", "diplomes chez", "diplomes qui",
        "etudiants de la promo", "etudiants de la promotion",
        "eleves de la promo", "eleves de la promotion",
        # Formulations "à BNP", "chez Deloitte", suivies d'un nom propre
        "travaille a ", "travaillent a ", "travaillent chez", "travaille chez",
        "poste a ", "poste chez", "embauche chez", "employe chez", "employes chez",
        "passe par", "passe chez", "passes par", "passes chez",
        # Promotion + référence personne
        "etudiants ", "eleves ", "diplome ",
    ]
    is_alumni_question = any(kw in query_normalized for kw in alumni_keywords_strong)

    include_alumni = is_alumni_question and not is_stats_question

    # ── DÉTECTION QUESTIONS TRANSVERSALES (qui balayent plusieurs promos) ──
    # Ces questions ne ciblent pas une année précise mais "toutes les promos"
    transversal_keywords = [
        "tous les", "toutes les", "chaque", "toutes promos", "tous alumni",
        "quels alumni", "quels diplomes", "quels diplomes", "quels anciens",
        "qui travaille", "qui travaillent", "qui sont chez", "qui sont a",
        "travaille chez", "travaillent chez", "ont travaille",
        "liste des alumni", "liste des diplomes", "alumni chez",
        "anciens chez", "anciens qui", "diplomes chez", "diplomes qui",
        "evolution", "evolution", "historique", "depuis", "moyenne sur",
        "ensemble", "tendance"
    ]
    is_transversal = any(kw in query_normalized for kw in transversal_keywords)

    # Si l'utilisateur demande "statistiques d'insertion" sans préciser de promo
    # → c'est aussi transversal
    has_specific_year = bool(re.search(r"\b(20[0-2]\d)\b", search_query))
    if is_stats_question and not has_specific_year:
        is_transversal = True

    # Si question alumni sans année précise → probablement transversale
    # (ex: "qui travaille chez Deloitte" sans dire de quelle promo)
    if is_alumni_question and not has_specific_year:
        is_transversal = True

    # Si transversal : TOP_K élevé pour récupérer toutes les promos
    effective_top_k = 30 if is_transversal else TOP_K

    # Détection recherche EN AMONT (avant le check visiteur) pour autoriser les questions
    # sur les alumnis qui ont fait de la recherche (info publique sur le site)
    recherche_keywords = [
        "recherche", "these", "thèse", "doctorat", "phd", "laboratoire",
        "leo ", "chercheur", "chercheurs", "enseignant-chercheur",
        "academic", "publication", "publie", "publient", "master recherche",
        "voie recherche", "poursuit en these", "poursuite en these",
    ]
    is_recherche_question = any(kw in query_normalized for kw in recherche_keywords)

    # ── MODE VISITEUR : si la question concerne les alumni, on répond clairement
    # plutôt que de laisser le LLM inventer une réponse vague ──
    # EXCEPTION : si c'est une question sur les alumnis chercheurs (info publique du site)
    if access_mode == "visitor" and is_alumni_question and not is_stats_question and not is_recherche_question:
        restricted_msg = (
            "🔒 **Information réservée aux utilisateurs connectés**\n\n"
            "Les informations sur les diplômés (listes, parcours professionnels, "
            "entreprises, contacts LinkedIn) ne sont pas accessibles en mode visiteur. "
            "Elles sont disponibles uniquement aux étudiants et alumni connectés sur le site du Master ESA.\n\n"
            "💡 Si vous êtes étudiant ou alumni du master, connectez-vous sur le site pour accéder à ces informations."
        )
        await cl.Message(
            content=restricted_msg,
            actions=get_main_actions(access_mode),
        ).send()
        add_to_history("user", question)
        add_to_history("assistant", restricted_msg)
        return

    filters = []
    if access_mode == "visitor":
        filters.append({"access": "public"})
    if not include_alumni:
        # On exclut les chunks alumni individuels ET les résumés alumni
        filters.append({"type": {"$nin": ["alumni", "alumni_summary"]}})

    if len(filters) == 0:
        where_filter = None
    elif len(filters) == 1:
        where_filter = filters[0]
    else:
        where_filter = {"$and": filters}

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=effective_top_k,
        where=where_filter,
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    # ── BOOST : si une année de promo est mentionnée ET qu'on inclut les alumni,
    # on force l'ajout du chunk synthèse de cette promo (s'il n'est pas déjà là) ──
    # IMPORTANT : ne s'applique qu'en mode connecté (les chunks alumni sont restreints)
    if include_alumni and access_mode == "logged_in":
        target_year = None

        # 1. Détecter d'abord une plage AAAA/BBBB, AAAA-BBBB, AAAA BBBB (BBBB = AAAA+1)
        # → c'est une année universitaire = promotion BBBB
        range_match = re.search(r"\b(20[0-2]\d)[\s\-/]+(20[0-2]\d)\b", search_query)
        if range_match:
            an1 = int(range_match.group(1))
            an2 = int(range_match.group(2))
            if an2 == an1 + 1:
                target_year = str(an2)

        # 2. Sinon, chercher une année simple
        if target_year is None:
            year_match = re.search(r"\b(20[0-2]\d)\b", search_query)
            if year_match:
                target_year = year_match.group(1)

        if target_year:
            # Vérifier si le chunk synthèse de cette promo est déjà dans les résultats
            has_summary = any(
                m.get("type") == "alumni_summary" and m.get("promotion") == target_year
                for m in metas
            )
            if not has_summary:
                # Aller chercher le chunk synthèse de cette promo directement
                try:
                    summary_result = collection.get(
                        where={"$and": [
                            {"type": "alumni_summary"},
                            {"promotion": target_year}
                        ]},
                        include=["documents", "metadatas"]
                    )
                    if summary_result["ids"]:
                        # On l'ajoute en tête des résultats
                        docs = [summary_result["documents"][0]] + list(docs)
                        metas = [summary_result["metadatas"][0]] + list(metas)
                        dists = [0.0] + list(dists)  # distance fictive 0 = priorité max
                except Exception as e:
                    print(f"⚠️ Erreur boost synthèse : {e}")

    # ── BOOST STATS TRANSVERSAL : si la question est statistique ET transversale
    # (pas d'année précise), on récupère TOUS les chunks de master_esa_insertion.md
    # pour ne sauter aucune promotion ──
    if is_stats_question and is_transversal:
        try:
            all_insertion = collection.get(
                where={"source_file": "master_esa_insertion.md"},
                include=["documents", "metadatas"]
            )
            print(f"   📊 Boost stats transversal : {len(all_insertion['ids'])} chunks d'insertion injectés")
            for doc, meta in zip(all_insertion["documents"], all_insertion["metadatas"]):
                already_in = any(
                    m.get("section") == meta.get("section")
                    and m.get("source_file") == meta.get("source_file")
                    for m in metas
                )
                if not already_in:
                    docs = [doc] + list(docs)
                    metas = [meta] + list(metas)
                    dists = [0.1] + list(dists)
        except Exception as e:
            print(f"⚠️ Erreur boost stats transversal : {e}")

    # ── BOOST SYLLABUS : si la question concerne un semestre,
    # on injecte tous les chunks du fichier syllabus concerné (pour avoir
    # toutes les matières + leurs ECTS dans le contexte) ──
    syllabus_files = []

    # Normaliser les ordinaux : "1er", "2ème", "3eme", "dernier" → mots simples
    # qu'on pourra ensuite matcher facilement
    q_for_sem = query_normalized
    # Remplacements d'ordinaux
    ordinal_replacements = [
        (r"\b1\s?er\b", "premier"),
        (r"\b1\s?ere?\b", "premier"),
        (r"\b1\s?[oe]r\b", "premier"),
        (r"\b2\s?eme\b", "deuxieme"),
        (r"\b2\s?[èe]me\b", "deuxieme"),
        (r"\b2\s?nd\b", "deuxieme"),
        (r"\b2\s?nde?\b", "deuxieme"),
        (r"\bdernier\b", "deuxieme"),  # "dernier semestre de M1" = S8, "dernier semestre de M2" = S10
        (r"\bderniere\b", "deuxieme"),
    ]
    for pattern, replacement in ordinal_replacements:
        q_for_sem = re.sub(pattern, replacement, q_for_sem)

    # Détection M1/M2 entier
    has_m1_general = bool(re.search(r"\bm1\b", q_for_sem))
    has_m2_general = bool(re.search(r"\bm2\b", q_for_sem))
    has_specific_sem = bool(re.search(r"\bs\s?[7-9]\b|\bs\s?10\b|\bsemestre\b|premier|deuxieme|second", q_for_sem))

    # Détection des semestres mentionnés explicitement (S7, S8, S9, S10)
    if re.search(r"\bs\s?7\b|semestre\s+7", q_for_sem):
        syllabus_files.append("master_esa_syllabus_S7.md")
    if re.search(r"\bs\s?8\b|semestre\s+8", q_for_sem):
        syllabus_files.append("master_esa_syllabus_S8.md")
    if re.search(r"\bs\s?9\b|semestre\s+9", q_for_sem):
        syllabus_files.append("master_esa_syllabus_S9.md")
    if re.search(r"\bs\s?10\b|semestre\s+10", q_for_sem):
        syllabus_files.append("master_esa_syllabus_S10.md")

    # "premier semestre de M1" / "M1 premier semestre" / "M1 deuxième semestre" etc.
    if re.search(r"\bm1\b.*\bpremier\b|\bpremier\b.*\bm1\b", q_for_sem):
        syllabus_files.append("master_esa_syllabus_S7.md")
    if re.search(r"\bm1\b.*(deuxieme|second)|(deuxieme|second).*\bm1\b", q_for_sem):
        syllabus_files.append("master_esa_syllabus_S8.md")
    if re.search(r"\bm2\b.*\bpremier\b|\bpremier\b.*\bm2\b", q_for_sem):
        syllabus_files.append("master_esa_syllabus_S9.md")
    if re.search(r"\bm2\b.*(deuxieme|second)|(deuxieme|second).*\bm2\b", q_for_sem):
        syllabus_files.append("master_esa_syllabus_S10.md")

    # "M1" sans semestre précis → booster S7 ET S8 entier
    if has_m1_general and not has_specific_sem:
        syllabus_files.append("master_esa_syllabus_S7.md")
        syllabus_files.append("master_esa_syllabus_S8.md")
    # "M2" sans semestre précis → booster S9 ET S10 entier
    if has_m2_general and not has_specific_sem:
        syllabus_files.append("master_esa_syllabus_S9.md")
        syllabus_files.append("master_esa_syllabus_S10.md")

    # Déduplication
    syllabus_files = list(dict.fromkeys(syllabus_files))

    syllabus_keywords = ["matiere", "matieres", "cours", "enseignement", "enseignements",
                          "programme", "syllabus", "module", "modules",
                          "credits", "ects", "coefficient", "coef", "volume horaire",
                          # Termes de comparaison et structure
                          "difference", "différence", "differences", "différences",
                          "compare", "comparaison", "comparer",
                          "contenu", "contenus", "structure", "organisation",
                          "composition", "composé", "compose", "comprend", "contient",
                          # Termes de description générale
                          "description", "presentation", "présentation",
                          "que faire", "quoi faire", "que voir", "que comporte",
                          "qu'est-ce que", "qu est ce que",
                          # Année / niveau seul (sans semestre précisé)
                          "annee", "année", "niveau", "premiere annee", "deuxieme annee",
                          "première année", "deuxième année"]
    is_syllabus_question = any(kw in query_normalized for kw in syllabus_keywords)

    if is_syllabus_question and syllabus_files:
        for syllabus_file in syllabus_files:
            try:
                all_syllabus = collection.get(
                    where={"source_file": syllabus_file},
                    include=["documents", "metadatas"]
                )
                print(f"   📚 Boost syllabus : {len(all_syllabus['ids'])} chunks de {syllabus_file} injectés")
                for doc, meta in zip(all_syllabus["documents"], all_syllabus["metadatas"]):
                    already_in = any(
                        m.get("section") == meta.get("section")
                        and m.get("source_file") == meta.get("source_file")
                        for m in metas
                    )
                    if not already_in:
                        docs = [doc] + list(docs)
                        metas = [meta] + list(metas)
                        dists = [0.05] + list(dists)
            except Exception as e:
                print(f"⚠️ Erreur boost syllabus {syllabus_file} : {e}")
        # Mémoriser pour la construction de la liste exacte plus bas
        cl.user_session.set("_last_syllabus_search", syllabus_files)
    else:
        cl.user_session.set("_last_syllabus_search", None)

    # ── BOOST RECHERCHE : si la question concerne la recherche/thèse,
    # on injecte tous les chunks de master_esa_recherche.md ──
    if is_recherche_question:
        try:
            all_recherche = collection.get(
                where={"source_file": "master_esa_recherche.md"},
                include=["documents", "metadatas"]
            )
            print(f"   🔬 Boost recherche : {len(all_recherche['ids'])} chunks injectés")
            for doc, meta in zip(all_recherche["documents"], all_recherche["metadatas"]):
                already_in = any(
                    m.get("section") == meta.get("section")
                    and m.get("source_file") == meta.get("source_file")
                    for m in metas
                )
                if not already_in:
                    docs = [doc] + list(docs)
                    metas = [meta] + list(metas)
                    dists = [0.05] + list(dists)  # priorité haute
        except Exception as e:
            print(f"⚠️ Erreur boost recherche : {e}")

    # ── BOOST CANDIDATURE : si la question concerne l'admission/candidature,
    # on injecte tous les chunks de master_esa_candidature.md ──
    candidature_keywords = [
        "candidat", "candidater", "candidature", "candidatures",
        "postuler", "postule", "postulent",
        "admission", "admissions", "admis", "selection", "sélection",
        "inscrire", "inscription", "inscrit",
        "dossier", "dossiers", "lettre de motivation",
        "campus france", "mon master", "monmaster",
        "prerequis", "prérequis", "pre-requis", "pre requis",
        "comment integrer", "comment intégrer", "intégrer le master", "integrer le master",
        "entrer dans le master", "rejoindre le master",
        "comment faire pour", "comment rentrer", "comment entrer",
        "etudiant etranger", "étudiant étranger", "etudiants etrangers", "étudiants étrangers",
        "campagne de recrutement", "recrutement",
        "mention de licence", "mentions de licence",
        "places", "capacite d'accueil", "capacité d'accueil",
    ]
    is_candidature_question = any(kw in query_normalized for kw in candidature_keywords)

    if is_candidature_question:
        try:
            all_candidature = collection.get(
                where={"source_file": "master_esa_candidature.md"},
                include=["documents", "metadatas"]
            )
            print(f"   📝 Boost candidature : {len(all_candidature['ids'])} chunks injectés")
            for doc, meta in zip(all_candidature["documents"], all_candidature["metadatas"]):
                already_in = any(
                    m.get("section") == meta.get("section")
                    and m.get("source_file") == meta.get("source_file")
                    for m in metas
                )
                if not already_in:
                    docs = [doc] + list(docs)
                    metas = [meta] + list(metas)
                    dists = [0.05] + list(dists)
        except Exception as e:
            print(f"⚠️ Erreur boost candidature : {e}")

    # ── BOOST PAR ENTREPRISE : si la question mentionne une entreprise précise
    # ET concerne les alumni, on récupère AUSSI tous les alumni de cette entreprise
    # par recherche exacte sur les métadonnées ──
    if include_alumni and access_mode == "logged_in":
        # Liste des entreprises connues (à enrichir avec celles vues dans la base)
        # On les détecte simplement en cherchant dans la query
        known_companies = [
            "Deloitte", "BNP Paribas", "BNP", "Société Générale", "SG", "Crédit Agricole",
            "BPCE", "LCL", "Crédit Mutuel", "Crédit Foncier", "Banque de France",
            "BCE", "Banque Centrale Européenne", "Banque Postale", "La Banque Postale",
            "EY", "Ernst & Young", "KPMG", "PwC", "Mazars", "Forvis Mazars",
            "Accenture", "Capgemini", "AVISIA", "Nexialog", "Nexialog Consulting",
            "Square Management", "RISC", "MPG Partners", "Lincoln", "CGI",
            "AXA", "Allianz", "Generali", "MACIF", "Thélem Assurances", "SPVIE",
            "Forvis", "Havas", "FLOA", "BIAT", "Groupama",
            "Université Paris-Dauphine", "Université d'Orléans",
        ]
        # Détection insensible à la casse (mais respectant les mots entiers)
        query_lower_check = search_query.lower()
        matched_companies = []
        for company in known_companies:
            # Match mot entier pour éviter "EY" qui matcherait "ney"
            pattern = r"\b" + re.escape(company.lower()) + r"\b"
            if re.search(pattern, query_lower_check):
                matched_companies.append(company)

        if matched_companies:
            print(f"   🏢 Entreprises détectées : {matched_companies}")
            # Récupérer tous les chunks alumni dont l'entreprise matche (insensible à la casse)
            extra_chunks = []
            for company in matched_companies:
                # Récupérer tous les alumni
                all_alumni = collection.get(
                    where={"type": "alumni"},
                    include=["documents", "metadatas"]
                )
                matches_company = 0
                already_in_count = 0
                for doc, meta in zip(all_alumni["documents"], all_alumni["metadatas"]):
                    ent = (meta.get("entreprise", "") or "").lower()
                    if company.lower() in ent:
                        matches_company += 1
                        # Vérifier qu'il n'est pas déjà dans les résultats
                        already_in = any(
                            m.get("nom") == meta.get("nom") and m.get("prenom") == meta.get("prenom")
                            for m in metas
                        )
                        if not already_in:
                            extra_chunks.append((doc, meta, 0.05))  # distance fictive très faible
                        else:
                            already_in_count += 1
                print(f"   🏢 Alumni matchant '{company}' : {matches_company} total ({already_in_count} déjà présents, {matches_company - already_in_count} à ajouter)")
            if extra_chunks:
                # Trier les extras par promotion descendante (plus récent en premier)
                def _promo_of(item):
                    p = (item[1].get("promotion") or "").strip()
                    return int(p) if p.isdigit() else 0
                extra_chunks.sort(key=_promo_of, reverse=True)
                # Mémoriser la company détectée pour l'instruction LLM
                cl.user_session.set("_last_company_search", {
                    "companies": matched_companies,
                    "total_matches": matches_company,
                })
                # Ajouter en tête (priorité max)
                docs = [c[0] for c in extra_chunks] + list(docs)
                metas = [c[1] for c in extra_chunks] + list(metas)
                dists = [c[2] for c in extra_chunks] + list(dists)
            else:
                cl.user_session.set("_last_company_search", None)
        else:
            cl.user_session.set("_last_company_search", None)
    else:
        cl.user_session.set("_last_company_search", None)

    relevant = [(doc, meta, dist) for doc, meta, dist in zip(docs, metas, dists) if dist <= MAX_DISTANCE]

    # ── TRI PAR RÉCENCE : pour les questions impliquant plusieurs promotions/années,
    # on classe les chunks du plus récent au plus ancien ──
    def extract_year(item) -> int:
        """Extrait une année depuis les métadonnées d'un chunk (0 si pas trouvée)."""
        meta = item[1]
        # 1. Champ promotion explicite (alumni, alumni_summary)
        promo = meta.get("promotion", "")
        if promo and promo.isdigit():
            return int(promo)
        # 2. Année dans la section (ex: "Enquête d'insertion — Promotion 2023/2024")
        section = meta.get("section", "") or ""
        year_match = re.search(r"\b(20[0-2]\d)/(20[0-2]\d)\b", section)
        if year_match:
            return int(year_match.group(2))  # année de fin = année de diplomation
        # 3. Année simple dans la section
        year_match = re.search(r"\b(20[0-2]\d)\b", section)
        if year_match:
            return int(year_match.group(1))
        return 0  # pas d'année trouvée

    # Tri stable : on garde l'ordre du retrieval pour les chunks sans année,
    # mais on met d'abord les plus récents pour ceux qui en ont une.
    # Astuce : on trie par (a_une_annee, annee) en descendant.
    relevant.sort(key=lambda x: (extract_year(x) > 0, extract_year(x)), reverse=True)

    if not relevant:
        no_info_msg = (
            "Désolé, je n'ai pas trouvé d'information pertinente sur ce sujet "
            "dans la base de connaissances du Master ESA.\n\n"
            "Essayez de reformuler votre question, ou contactez directement "
            "le master à master.econometrie@univ-orleans.fr"
        )
        await cl.Message(content=no_info_msg, actions=get_main_actions(access_mode)).send()
        add_to_history("user", question)
        add_to_history("assistant", no_info_msg)
        return

    context_parts = []
    sources = []
    for i, (doc, meta, dist) in enumerate(relevant, 1):
        source_file = meta.get("source_file", "")
        section = meta.get("section", "") or "(document entier)"
        chunk_type = meta.get("type", "general")

        # Marquer les chunks de synthèse pour que le LLM les priorise
        if chunk_type in ("alumni_summary", "syllabus_summary"):
            type_tag = " ⭐ [LISTE COMPLÈTE — utilise CET extrait en priorité si l'utilisateur demande une liste exhaustive]"
        else:
            type_tag = ""

        context_parts.append(
            f"[Extrait {i} — {source_file} | section: {section}{type_tag}]\n{doc}"
        )
        sources.append(f"{source_file} (section: {section})")
    context = "\n\n---\n\n".join(context_parts)

    # ── INSTRUCTION COMPANY : si la question concerne une entreprise précise,
    # on construit une LISTE EXACTE pré-triée et on la donne au LLM avec
    # une instruction explicite ──
    company_instruction = ""
    company_info = cl.user_session.get("_last_company_search")
    if company_info and company_info.get("companies"):
        # Récupérer TOUS les alumni de l'entreprise (depuis l'ensemble du contexte)
        for company in company_info["companies"]:
            company_lower = company.lower()
            # On collecte depuis 'relevant' (qui contient maintenant les chunks boostés)
            company_alumni = []
            seen = set()
            for _, meta, _ in relevant:
                if meta.get("type") != "alumni":
                    continue
                ent = (meta.get("entreprise") or "").lower()
                if company_lower not in ent:
                    continue
                key = (meta.get("nom", ""), meta.get("prenom", ""))
                if key in seen:
                    continue
                seen.add(key)
                company_alumni.append(meta)

            if company_alumni:
                # Trier par promo descendante
                company_alumni.sort(
                    key=lambda m: int(m["promotion"]) if (m.get("promotion") or "").isdigit() else 0,
                    reverse=True
                )
                # Construire la liste textuelle
                lines = [f"\n\n📌 LISTE EXACTE — Alumni du Master ESA travaillant chez {company} :"]
                for i, m in enumerate(company_alumni, 1):
                    prenom = m.get("prenom", "")
                    nom = m.get("nom", "")
                    promo = m.get("promotion", "")
                    poste = m.get("poste", "") or "poste non renseigné"
                    lines.append(f"{i}. {prenom} {nom} (promotion {promo}) — {poste}")
                lines.append(
                    f"\n🛑 INSTRUCTION ABSOLUE : Cette liste contient EXACTEMENT "
                    f"{len(company_alumni)} alumni. Ta réponse DOIT inclure TOUS CES "
                    f"{len(company_alumni)} alumni SANS EXCEPTION, dans CET ORDRE EXACT "
                    f"(du plus récent au plus ancien). Tu peux enrichir avec le LinkedIn "
                    f"présent dans les extraits du contexte, mais tu ne dois ni ajouter "
                    f"d'autres alumni, ni en retirer un seul.\n\n"
                    f"⚠️ VÉRIFICATION OBLIGATOIRE avant de répondre :\n"
                    f"1. Compte le nombre d'alumni dans ta réponse → doit être EXACTEMENT {len(company_alumni)}\n"
                    f"2. Si tu en comptes moins, c'est que tu en as oublié → reprends la liste ci-dessus\n"
                    f"3. Le PREMIER de ta liste doit être un alumni de la promotion {company_alumni[0].get('promotion', '?')}\n"
                    f"4. Le DERNIER de ta liste doit être un alumni de la promotion {company_alumni[-1].get('promotion', '?')}\n"
                )
                company_instruction = "\n".join(lines)
                break  # une seule entreprise à la fois suffit

    # ── INSTRUCTION SYLLABUS : si la question concerne un ou plusieurs semestres,
    # on construit une LISTE EXACTE des matières et on la donne au LLM avec
    # une instruction explicite pour qu'aucune ne soit omise ──
    syllabus_instruction = ""
    syllabus_info = cl.user_session.get("_last_syllabus_search")

    # Mapping en dur des matières S10 par voie (Pro / Recherche)
    # Source : master_esa_syllabus_S10.md (sections # OPTION PROFESSIONNELLE / # OPTION RECHERCHE)
    S10_VOIE_PRO = [
        "Data Mining",
        "Économétrie semi et non-paramétrique",
        "Advanced Financial Econometrics",
        "BDA : Neural Networks",
        "Assurance et techniques actuarielles 2",
        "Modélisation du risque de crédit",
        "Gestion de bases de données sous SAS",
        "Mise en œuvre de la proc SQL sous SAS",
        "Stage de fin d'études (option professionnelle)",
    ]
    S10_VOIE_RECHERCHE = [
        "Macroéconomie avancée",
        "Économétrie avancée",
        "Microéconomie avancée",
        "Finance avancée",
        "Économie internationale et environnementale avancée",
        "Mémoire de recherche",
    ]
    if syllabus_info:
        # Mapping fichier → libellé semestre
        sem_label = {
            "master_esa_syllabus_S7.md": ("S7 (M1, premier semestre)", "S7"),
            "master_esa_syllabus_S8.md": ("S8 (M1, deuxième semestre)", "S8"),
            "master_esa_syllabus_S9.md": ("S9 (M2, premier semestre)", "S9"),
            "master_esa_syllabus_S10.md": ("S10 (M2, deuxième semestre)", "S10"),
        }
        # Pour chaque semestre concerné, on récupère directement le chunk "Liste complète"
        # qui est déjà bien structuré dans le .md (avec blocs thématiques, ECTS, etc.)
        lines = []
        semesters_processed = []
        for syllabus_file in syllabus_info:
            label_full, label_short = sem_label.get(syllabus_file, (syllabus_file, syllabus_file))

            # Chercher le chunk "Liste complète" dans relevant
            liste_complete_doc = None
            for doc, meta, _ in relevant:
                if meta.get("source_file") != syllabus_file:
                    continue
                section = meta.get("section", "") or ""
                if "Liste complète" in section:
                    liste_complete_doc = doc
                    break

            if liste_complete_doc:
                lines.append(f"\n📘 LISTE EXACTE ET STRUCTURÉE — Matières du {label_full} :")
                lines.append(liste_complete_doc.strip())
                lines.append("")  # ligne vide pour aération
                semesters_processed.append(label_short)

        if lines:
            lines.append(
                f"\n🛑 INSTRUCTION ABSOLUE — RESPECT DE LA STRUCTURE :\n"
                f"1. Tu DOIS reprendre EXACTEMENT la structure ci-dessus (blocs thématiques en gras + matières numérotées).\n"
                f"2. Tu DOIS lister TOUTES les matières indiquées, SANS EXCEPTION, dans le MÊME ORDRE que ci-dessus.\n"
                f"3. Tu DOIS CONSERVER VISIBLEMENT les blocs thématiques en sous-titres : « **Outils pour la Data Science** », « **Outils statistiques et économétrie** », « **Professionnalisation** », « **Projets professionnalisants** », etc. — ces sous-titres apparaîtront en gras dans ta réponse.\n"
                f"4. NE JAMAIS INVERSER l'ordre des matières. L'ordre du syllabus est l'ordre du contenu pédagogique, pas un ordre chronologique.\n"
                f"5. NE PAS ajouter de matières qui ne sont pas dans la liste ci-dessus.\n"
                f"6. NE PAS inclure « Vue d'ensemble » comme une matière (c'est une section méta du document).\n"
                f"7. Si plusieurs semestres sont demandés (ex: « programme du M1 » = S7 + S8), présente-les dans l'ordre numérique (S7 d'abord, puis S8).\n"
                f"8. Pour le S10 spécifiquement, conserve la distinction entre « OPTION PROFESSIONNELLE » et « OPTION RECHERCHE ».\n"
                f"9. Si l'utilisateur NE demande PAS les ECTS, retire-les de ta réponse. S'il les demande (ou demande coefficients/crédits/volumes horaires), affiche-les pour TOUTES les matières.\n"
                f"\n📋 EXEMPLE DE RÉPONSE ATTENDUE (pour 'Matières du S8', sans ECTS) :\n"
                f"```\n"
                f"Voici les matières du Semestre 8 (M1, deuxième semestre) :\n\n"
                f"**Outils pour la Data Science** :\n"
                f"1. Nouvelles technologies sous R\n"
                f"2. Programmation Python avancée\n"
                f"3. Langage macro sous SAS\n\n"
                f"**Outils statistiques et économétrie** :\n"
                f"4. Statistique avancée et méthodes de simulation\n"
                f"...\n"
                f"```\n"
                f"⚠️ La structure par blocs thématiques est OBLIGATOIRE, peu importe la question (« matières du S8 », « programme du M1 », « cours du S9 », etc.). Une simple liste à plat sans blocs N'EST PAS ACCEPTABLE.\n"
            )
            syllabus_instruction = "\n".join(lines)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        messages.append(msg)

    # ── DÉTECTION D'UNE PROMO PAR ANNÉE SIMPLE ──
    # Si l'utilisateur écrit "promo 2020" / "promotion 2020" / "stats 2020",
    # on injecte explicitement la conversion dans le prompt pour éviter
    # toute confusion entre "promo 2020" et "Promotion M2 2020/2021".
    # IMPORTANT : on exclut "2020/2021", "2020-2021", "2020 2021" qui désignent
    # déjà une plage explicite et n'ont pas besoin de conversion.
    promo_clarification = ""

    # Cas 1 : notation plage "AAAA/BBBB", "AAAA-BBBB", "AAAA BBBB" (BBBB = AAAA+1)
    # → c'est une année universitaire = promotion BBBB
    range_match = re.search(
        r"\b(\d{4})[\s\-/]+(\d{4})\b",
        question.lower()
    )
    if range_match:
        an1 = int(range_match.group(1))
        an2 = int(range_match.group(2))
        if an2 == an1 + 1:
            # C'est bien une plage année universitaire valide
            promo_clarification = (
                f"\n\n⚠️ RAPPEL DE CONVENTION : L'utilisateur écrit « {an1}/{an2} » (ou « {an1}-{an2} », « {an1} {an2} »). "
                f"Ce n'est PAS deux promotions distinctes : c'est l'année universitaire {an1}/{an2}, "
                f"qui correspond à UNE SEULE promotion = la promotion {an2} du Master ESA "
                f"(= section « Promotion M2 {an1}/{an2} » dans le contexte). "
                f"Tu dois donc répondre uniquement sur cette promotion-là, et NON sur deux promotions séparées.\n"
            )

    # Cas 2 : année simple "promo 2020", "promotion 2020", "stats 2020", etc.
    # (seulement si on n'a pas déjà détecté un cas 1)
    if not promo_clarification:
        promo_year_match = re.search(
            r"\b(?:promo|promotion|stats?|insertion|annee|année)\s+(?:de\s+(?:la\s+)?)?(\d{4})\b(?![\s\-/]+\d{4})",
            question.lower()
        )
        if promo_year_match:
            annee = int(promo_year_match.group(1))
            promo_clarification = (
                f"\n\n⚠️ RAPPEL DE CONVENTION : L'utilisateur demande des informations "
                f"sur la « promotion {annee} ». D'après la convention du Master ESA, "
                f"cela correspond à l'année universitaire {annee-1}/{annee} (= section "
                f"« Promotion M2 {annee-1}/{annee} » dans le contexte). "
                f"NE PAS confondre avec la « Promotion M2 {annee}/{annee+1} » qui désignerait "
                f"la promotion {annee+1}.\n"
            )

    # ── DÉTECTION ECTS / COEFFICIENTS / CRÉDITS ──
    # Si l'utilisateur ne demande PAS explicitement les ECTS, on instruit le LLM
    # de ne PAS les afficher (le LLM les voit dans le contexte et les recopie
    # naturellement, ce qui rend les réponses incohérentes)
    ects_synonyms = [
        "ects", "credit", "crédit", "credits", "crédits",
        "coef", "coeff", "coefficient", "coefficients",
        "ponderation", "pondération", "ponderations", "pondérations",
        "volume horaire", "nombre d'heures", "combien d'heures",
    ]
    user_wants_ects = any(syn in question.lower() for syn in ects_synonyms)
    ects_instruction = ""
    if not user_wants_ects:
        ects_instruction = (
            "\n\n📚 INSTRUCTION SUR LES ECTS : L'utilisateur n'a PAS demandé les ECTS "
            "(ni les coefficients, crédits, volumes horaires). Tu NE DOIS PAS afficher "
            "ces informations même si tu les vois dans les extraits. Liste uniquement "
            "les noms des matières, sans ECTS, sans heures, sans coefficients. "
            "Le LLM est tenté de les recopier par habitude — résiste.\n"
        )
    else:
        ects_instruction = (
            "\n\n📚 INSTRUCTION SUR LES ECTS : L'utilisateur demande les ECTS (ou un "
            "synonyme : coefficients, crédits, volumes horaires). Note que dans ce master, "
            "ECTS = coefficients = crédits (synonymes équivalents). Affiche les ECTS pour "
            "TOUTES les matières que tu listes (cohérence). Si une matière n'a pas d'ECTS "
            "renseignés dans les extraits, indique simplement la matière sans inventer "
            "de valeur, ou écris « ECTS non précisés ».\n"
        )

    user_prompt = (
        f"CONTEXTE (extraits de la base de connaissances) :\n\n{context}{company_instruction}{syllabus_instruction}\n\n"
        f"---\n\n⚡ QUESTION ACTUELLE DE L'UTILISATEUR (à laquelle tu dois répondre) : {question}"
        f"{promo_clarification}{ects_instruction}\n\n"
        f"⚠️ Important : Si la question fait référence à un échange précédent (ex: 'et 2023 ?', 'et le salaire ?'), "
        f"interprète-la UNIQUEMENT par rapport à la DERNIÈRE question que tu as traitée, "
        f"PAS par rapport à des questions plus anciennes de l'historique. "
        f"Ne mélange pas les sujets entre eux.\n\n"
        f"Réponds en t'appuyant uniquement sur le contexte ci-dessus, en français."
    )
    messages.append({"role": "user", "content": user_prompt})

    msg = cl.Message(content="")
    await msg.send()

    full_response = ""
    try:
        stream = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=4096,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                full_response += delta
                await msg.stream_token(delta)
        await msg.update()
    except Exception as e:
        await cl.Message(content=f"❌ Erreur lors de l'appel au LLM : {str(e)}").send()
        return

    # Extraire les sources réellement citées par le LLM dans sa réponse
    # (ligne "Source(s) : ..." en fin de réponse, voir règle 9 du prompt système)
    cited_sources = []
    cleaned_response = full_response

    # Regex qui capture toute la dernière section "Source(s) : ..." jusqu'à la fin
    source_line_match = re.search(
        r"\n*\s*Sources?\s*\(?s?\)?\s*:\s*(.+?)\s*$",
        full_response,
        re.DOTALL | re.IGNORECASE,
    )
    if source_line_match:
        sources_blob = source_line_match.group(1).strip()
        # Retirer la ligne complète de la réponse affichée
        cleaned_response = full_response[: source_line_match.start()].rstrip()

        # Cas "Source(s) : aucune" → pas de sources à afficher
        if sources_blob.lower().strip() not in {"aucune", "none", "n/a", "-"}:
            # Découper sur les virgules tout en respectant les parenthèses
            depth = 0
            current = []
            parts = []
            for ch in sources_blob:
                if ch == "(":
                    depth += 1
                    current.append(ch)
                elif ch == ")":
                    depth -= 1
                    current.append(ch)
                elif ch == "," and depth == 0:
                    parts.append("".join(current).strip())
                    current = []
                else:
                    current.append(ch)
            if current:
                parts.append("".join(current).strip())
            cited_sources = [p.lstrip("- •*").strip() for p in parts if p.strip()]

    # Mettre à jour le message affiché avec la version sans la ligne "Source(s) :"
    if cleaned_response != full_response:
        msg.content = cleaned_response
        await msg.update()

    # Construire le menu dépliable des sources
    # Si le LLM n'a pas cité de source, le menu n'est pas affiché
    if cited_sources:
        # Transformer chaque source brute en texte naturel humain avec lien
        # On déduplique aussi sur le RÉSULTAT humanisé (pour éviter d'afficher
        # 4 fois "Programme du M1 — Semestre 7" quand le LLM cite 4 sections du S7)
        humanized = []
        seen = set()
        for raw_src in cited_sources:
            human = humanize_source(raw_src)
            if human not in seen:
                seen.add(human)
                humanized.append(human)

        sources_text = "\n".join(f"- {h}" for h in humanized)
        sources_block = (
            f"<details>\n"
            f"<summary>📚 <strong>Sources</strong> (cliquer pour déplier)</summary>\n\n"
            f"{sources_text}\n\n"
            f"</details>"
        )
    else:
        sources_block = ""

    await cl.Message(
        content=sources_block,
        author="ESA_Sources",
        actions=get_main_actions(access_mode),
    ).send()

    # ── Feedback 👍 / 👎 sur cette réponse ──
    # On stocke un ID unique par paire (question, réponse) pour permettre au handler
    # d'identifier les votes et empêcher le double-vote.
    feedback_id = f"fb_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    feedback_payload = {
        "feedback_id": feedback_id,
        "mode": access_mode,
        "question": question,
        "response": cleaned_response,
    }
    feedback_actions = [
        cl.Action(
            name="feedback_vote",
            payload={**feedback_payload, "vote": "👍"},
            label="👍 Utile",
            tooltip="Cette réponse m'a été utile",
        ),
        cl.Action(
            name="feedback_vote",
            payload={**feedback_payload, "vote": "👎"},
            label="👎 Pas utile",
            tooltip="Cette réponse n'a pas répondu à ma question",
        ),
    ]
    # On mémorise dans la session les IDs déjà votés pour empêcher le re-vote
    voted_ids = cl.user_session.get("voted_feedback_ids") or set()
    if not isinstance(voted_ids, set):
        voted_ids = set(voted_ids)
    cl.user_session.set("voted_feedback_ids", voted_ids)

    feedback_msg = cl.Message(
        content="*Cette réponse vous a-t-elle été utile ?*",
        author="ESA_Feedback",
        actions=feedback_actions,
    )
    await feedback_msg.send()
    # On stocke l'ID du message pour pouvoir l'effacer après le vote
    cl.user_session.set(f"feedback_msg_{feedback_id}", feedback_msg.id)

    add_to_history("user", question)
    # On garde la réponse SANS la ligne Source(s) dans l'historique conversationnel
    # (pour ne pas polluer les questions suivantes)
    add_to_history("assistant", cleaned_response)


# ── Handler du vote feedback ──
@cl.action_callback("feedback_vote")
async def on_feedback_vote(action: cl.Action):
    payload = action.payload or {}
    feedback_id = payload.get("feedback_id")
    if not feedback_id:
        return

    # Empêcher le double vote pour cette même paire question/réponse
    voted_ids = cl.user_session.get("voted_feedback_ids") or set()
    if not isinstance(voted_ids, set):
        voted_ids = set(voted_ids)
    if feedback_id in voted_ids:
        await cl.Message(
            content="✅ Vous avez déjà voté pour cette réponse, merci !",
            author="ESA_Feedback",
        ).send()
        return
    voted_ids.add(feedback_id)
    cl.user_session.set("voted_feedback_ids", voted_ids)

    # Enregistrer le vote dans Google Sheets
    ok = log_feedback(
        mode=payload.get("mode", "?"),
        question=payload.get("question", ""),
        response=payload.get("response", ""),
        vote=payload.get("vote", "?"),
    )

    # Remplacer le message avec les boutons par une simple confirmation
    msg_id = cl.user_session.get(f"feedback_msg_{feedback_id}")
    if msg_id:
        try:
            confirm_text = (
                f"✅ Merci pour votre retour : {payload.get('vote', '')}"
                if ok else
                f"📥 Retour reçu : {payload.get('vote', '')} _(non sauvegardé : Google Sheets indisponible)_"
            )
            await cl.Message(id=msg_id, content=confirm_text, actions=[]).update()
        except Exception:
            # Si update échoue (ID introuvable), on envoie juste un message simple
            await cl.Message(
                content=f"✅ Merci pour votre retour : {payload.get('vote', '')}",
                author="ESA_Feedback",
            ).send()
    else:
        await cl.Message(
            content=f"✅ Merci pour votre retour : {payload.get('vote', '')}",
            author="ESA_Feedback",
        ).send()
