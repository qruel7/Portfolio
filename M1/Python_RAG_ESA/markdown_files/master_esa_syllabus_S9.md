# Syllabus détaillés — Master 2 ESA, Semestre 9 (2025-2026)

*Semestre commun à l'option professionnelle et à l'option recherche.*

Source : Syllabus officiels du Master ESA, MàJ 2025

---

## Méthodes de Scoring

- **Enseignant** : Christophe RAULT
- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 24h | **ECTS** : 4
- **Prérequis** : Cours d'économétrie des variables qualitatives (modèle logit, modèle probit, estimation par le maximum de vraisemblance, théorie des tests) ; Analyse discriminante

### Résumé

L'objet de ce cours est de présenter une méthodologie générale (inspirée des travaux de Gourieroux) associée à la construction d'un score, qui est la fonction donnant pour un vecteur de caractéristiques individuelles une note de risque. Cette note définit une relation d'ordre entre les individus, relation qui peut ensuite être utilisée pour sélectionner une partie de la clientèle. Une place importante est accordée à l'application de cette méthodologie sur des données bancaires avec le logiciel SAS.

### Objectifs

Comprendre, maîtriser, et savoir mettre en pratique sur des données réelles les différentes étapes associées à la construction d'un score :

- Le choix du critère à modéliser et le choix des données
- Le retraitement des variables brutes et la construction de variables pertinentes
- L'estimation du modèle par différentes méthodes économétriques
- L'analyse des performances et la mise en place de la règle de décision
- La construction de la grille de score
- L'interprétation des résultats
- La segmentation de la clientèle en classes de risques homogènes

### Plan du cours

1. **Chapitre 1 — Principes du scoring** : Fonction score, exemples, modélisation et choix du seuil, construction d'un score
2. **Chapitre 2 — Les modèles classiques** : L'analyse discriminante, les modèles probabilistes de réponse binaire, l'approche duale
3. **Chapitre 3 — Autres modèles** : Les modèles de durée, les arbres de segmentation, scores polytomiques ordonnés et non ordonnés
4. **Chapitre 4 — Performances d'un score, choix du seuil et suivi** : Courbes de performances, de sélection, de discrimination ; indicateurs de performances ; efficacité de la règle de décision ; suivi d'un score
5. **Chapitre 5 — Choix des données et biais de sélection** : Le choix et la qualité des données, la réintégration des refusés
6. **Chapitre 6 — Traitement, sélection des variables et grille de score** : Constitution de la base, traitement des valeurs manquantes/aberrantes, échantillonnage, sélection des variables, discrétisation, recodage, stabilité temporelle, corrélations, construction du modèle, multicolinéarité, effets non linéaires, contribution des variables, tests de validité, robustesse, gestion de la sous-représentation des défauts
7. **Chapitre 7 — Illustrations sous SAS** : Score d'octroi de crédit ; Score d'appétence pour un produit bancaire, grille de score et interprétation

### Bibliographie

- G. Celeux, *Analyse discriminante sur variables continues*, INRIA, 1990
- Davidson R. et MacKinnon J. G., *Estimation and Inference in Econometrics* (chap 15), 2021
- C. Gourieroux, *Économétrie des variables qualitatives*, Economica, 1989
- C. Gourieroux, *Courbes de performance, de sélection et de discrimination*, Annales d'Économie et de Statistique, 28, pp. 107–142, 1992
- Gourieroux C. et Jasiak J., *The Econometric of Individual Risk* (chap 4), Princeton University Press, 2015
- J.-J. Heckman, *Sample Selection Bias as a Specification Error*, Econometrica, 47(1), 1979
- S. Lollivier, *Modèles univariés et modèles de durée sur données individuelles*, ENSAE, 1990

---

## Modèles de durée

- **Enseignant** : Gilles DE TRUCHIS
- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 24h | **ECTS** : 4
- **Prérequis** : Cours de statistiques (propriétés des estimateurs, théorie des tests) ; Cours d'économétrie (estimation par le maximum de vraisemblance)

### Résumé

Ce cours a pour objet la présentation des techniques de modélisation des temps d'événement les plus utilisées. On expose successivement les estimations non paramétriques (estimateur de Kaplan-Meier), puis les modélisations paramétriques associées à des choix de distribution avec les tests de spécification. Enfin, on traite du modèle de Cox qui constitue la technique semi-paramétrique la plus populaire du risque de survenue d'un événement.

### Objectifs

- Mener et interpréter une estimation des fonctions de survie par Kaplan-Meier ; repérer d'éventuelles hétérogénéités d'individus et réaliser une première sélection de variables
- Savoir choisir une hypothèse de distribution adaptée aux données et réaliser une estimation paramétrique de la survie ; mener des tests de validation
- Être capable d'estimer et d'interpréter les résultats d'un modèle de Cox (ratios de risque, tests de validation, variables dépendantes des durées, études stratifiées)

### Plan du cours

1. **Chapitre 1 — Introduction** : La nature des données de survie ; la description de la distribution des temps de survie
2. **Chapitre 2 — L'approche non paramétrique** : Estimateur de Kaplan-Meier (présentation heuristique et MLE non paramétrique) ; hypothèses principales (censure non informative, homogénéité) ; variance de l'estimateur ; construction d'IC ; estimation de la fonction de risque cumulée ; estimation kernel du risque instantané ; comparaison des courbes de survie (LogRank, Wilcoxon, tests stratifiés) ; tables de survie (méthode actuarielle) ; Procédure LIFETEST
3. **Chapitre 3 — L'approche paramétrique** : Modèles AFT et modèles PH ; principales modélisations AFT (distributions extrêmes) ; estimation sous divers types de censure ; choix d'une distribution et tests de spécification ; estimation de fractiles ; données censurées à gauche, à droite et par intervalle ; Procédure LIFEREG
4. **Chapitre 4 — L'approche semi-paramétrique** : Modèle de Cox et son estimation (vraisemblance partielle, correction de Firth, événements simultanés) ; ratios de risque ; estimation de la survie de base ; analyse stratifiée ; variables explicatives non constantes ; tests de validation (qualité d'ajustement, résidus de martingale, résidus de déviance, DFBETA, résidus de Schoenfeld, tests PH) ; sélection automatique des variables
5. **Chapitre 5 — Quelques compléments** : Statistiques complémentaires aux ratios de risque ; Residual Mean Survival Time ; estimation non paramétrique avec censure par intervalle

### Bibliographie

- John D. Kalbfleisch & Ross L. Prentice, *The Statistical Analysis of Failure Time Data* (2nd edition), 2002, Wiley
- Paul D. Allison, *Survival Analysis using SAS: A practical guide* (2nd edition), 2010, SAS Institute

---

## BDA : Trees & aggregation methods (Bagging, Random Forests & Boosting)

- **Enseignant** : Sessi TOKPAVI
- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 12h | **ECTS** : 2
- **Prérequis** : Connaissances théoriques niveau M1 en statistiques et économétrie (spécification, estimation, prévision en régression et classification) ; Bonne maîtrise de SAS et R

### Résumé

Ce cours porte sur les arbres de décision comme algorithme d'apprentissage supervisé. Le principe consiste à partitionner l'univers des individus en groupes homogènes du point de vue de la variable cible. Les arbres présentent de nombreux atouts (modélisation non-paramétrique de relations non-linéaires, adaptation aux données volumineuses, gestion des données manquantes) mais ont des pouvoirs prédictifs limités. Les méthodes d'agrégation (Random Forest et Boosting) permettent de pallier cette insuffisance en combinant plusieurs arbres.

### Objectifs

- Maîtriser les arbres de décision pour la régression et la classification
- Maîtriser les méthodes d'agrégation (Bagging, Random Forest, Boosting)
- Mise en œuvre sous SAS et R

### Plan du cours

1. Introduction
2. Arbres de décision & l'algorithme CART (division binaire, choix de la variable de césure en classification et régression, élagage, règles de prédiction)
3. Les méthodes d'agrégation (Bagging en régression et classification, forêts aléatoires, Boosting : AdaBoost, Gradient Boosting, généralisation)
4. Applications sous SAS et R

### Bibliographie

- Breiman L. (1996), "Bagging predictors", *Machine Learning*, 26, 123-140
- Breiman L. (2001), "Random Forest", *Machine Learning*, 45, 5-32
- Freund Y. et Schapire R. E. (1996), "Experiments with a new boosting algorithm"
- Hastie T., Tibshirani R. et Friedman J. H. (2009), *The Elements of Statistical Learning*, Springer, 2nd Edition
- James G., Witten D., Hastie T. et Tibshirani R. (2016), *An Introduction to Statistical Learning*, Springer, 6th Edition

---

## BDA : Penalized regressions (Lasso, Adaptive Lasso, Elastic-Net)

- **Enseignant** : Sessi TOKPAVI
- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 12h | **ECTS** : 2
- **Prérequis** : Connaissances théoriques niveau M1 en statistiques et économétrie ; Bonne maîtrise de SAS et R

### Résumé

Ce cours aborde les méthodes de pénalisation pour régression et classification, appropriées lorsqu'on dispose d'un nombre important de variables. L'objectif est d'arbitrer entre biais et variance avec des estimateurs plus stables que ceux issus des MCO. Les méthodes abordées sont le Lasso, l'Elastic-net et l'Adaptive Lasso, ainsi que la régression Ridge.

### Objectifs

- Maîtriser les méthodes modernes de pénalisation (Ridge, Lasso, Elastic Net, Adaptive Lasso)
- Mise en œuvre sous SAS et R

### Plan du cours

1. Introduction (révolution Big Data, cadre global des solutions analytiques, apprentissage supervisé, arbitrage biais-variance)
2. Au-delà des MCO
3. La régression Ridge (estimateur et propriétés, validation croisée, multicolinéarité)
4. La régression Lasso (motivations, algorithmes d'estimation, propriétés)
5. Extensions du Lasso (Elastic-Net, Adaptive Lasso)
6. Cas de la classification
7. Séparateurs à vaste marge (présentation, propriétés théoriques, estimation)
8. Applications SAS et R

### Bibliographie

- Hastie T., Tibshirani R. et Friedman J. H. (2009), *The Elements of Statistical Learning*, Springer, 2nd Edition
- Hoerl A. E. et Kennard R. (1978), "Ridge regression", *Technometrics*, 12, 55-57
- Tibshirani R. (1996), "Regression shrinkage and selection via the lasso", *JRSS-B*, 58(1), 267-288
- Zou H. et Hastie T. (2005), "Regularization and variable selection via the elastic net", *JRSS-B*, 67, 301-320
- Zou H. (2006), "The Adaptive Lasso and Its Oracle Properties", *JASA*, 101, 476, 1418-1429

---

## BDA : Support Vector Machine

- **Enseignant** : Yoann PULL
- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 12h | **ECTS** : 2
- **Prérequis** : Modèles de régression linéaire ; Méthodes d'optimisation

### Résumé

Ce cours présente les principes des machines à vecteurs de support (SVM) pour la classification et la régression. Il couvre l'intuition des SVM dans le cas linéairement séparable, la formalisation sous forme primale et duale, la notion de soft margin et de variables ressorts, et le kernel trick pour les échantillons non séparables. Des applications sont proposées sous R, Python et SAS.

### Objectifs

- Introduire la notion théorique de séparateur à vaste marge et sa formalisation mathématique, notamment l'astuce du kernel
- Présenter les procédures d'implémentation des SVM/SVR sous SAS, R et Python, avec un focus sur l'influence des hyperparamètres

### Plan du cours

1. Introduction
2. Intuition des SVM : le cas linéairement séparable
3. Formalisation du SVM
4. Soft Margin
5. Kernel trick
6. Applications du SVM sous SAS, R, Python et Matlab
7. Extensions du SVM (SVM et scores, SVM multi-classes, SVR, Least Square SVM)
8. Conclusion

### Bibliographie

- Cristianini N. and Shawe-Taylor J. (2000), *An Introduction to Support Vector Machines*, Cambridge University Press
- Hastie T., Tibshirani R. and Friedman J. (2009), *The Elements of Statistical Learning*, Springer, 2nd ed.
- Vapnik V. N. (1998), *Statistical Learning Theory*, John Wiley
- Vapnik V. N. (1995), *The Nature of Statistical Learning Theory*, Springer

---

## BDA : Machine Learning Interprétable

- **Enseignant** : Yoann PULL
- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 12h | **ECTS** : 2
- **Prérequis** : Cours de Big Data Analytics I, II, III et IV ; Introduction à Python ; Machine Learning sous Python

### Résumé

Ce cours présente les notions de base du Machine Learning interprétable et les principales approches techniques permettant de rendre interprétable des modèles de ML qui ne le sont pas nativement. Trois grandes familles de méthodes sont abordées : les méthodes model-agnostic (PDP, ICE, ALE), les modèles d'approximation (LIME), et les valeurs de Shapley (SHAP). Applications sous Python et SAS.

### Objectifs

- Familiariser les étudiants aux enjeux de gouvernance de l'IA et du ML, notamment en finance, avec un focus sur l'interprétabilité et l'explicabilité
- Introduire les principaux outils permettant de rendre interprétable des modèles de ML non nativement interprétables

### Plan du cours

1. Définitions : interprétabilité et explicabilité
2. Principaux enjeux et principales méthodes du ML interprétable
3. PDP et approches similaires (Partial Dependence Plot, Individual Conditional Expectation, Accumulated Local Effects)
4. Local and Global Surrogate Models (Global surrogate, LIME)
5. Shapley Values (Shapley Values, SHAP)

### Bibliographie

- ACPR (2018), *Artificial intelligence: challenges for the financial sector*
- ACPR (2020), *Governance of artificial intelligence in finance*
- Molnar C. (2019), *Interpretable machine learning. A Guide for Making Black Box Models Explainable*
- Lipton Z. C. (2018), *The Mythos of Model Interpretability*, Queue, 16(3)
- Miller T. (2019), *Explanation in artificial intelligence*, Artificial Intelligence, 267

---

## BDA : NLP with Python

- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 12h | **ECTS** : 2

*Syllabus non disponible en ligne au moment du scraping.*

---

## Réglementation prudentielle bancaire

- **Enseignant** : Christophe HURLIN
- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 12h | **ECTS** : 2
- **Prérequis** : Cours de finance (M1)

### Résumé

Ce cours initie les étudiants aux grands enjeux de la régulation bancaire. Un premier chapitre est consacré à un bref survol de la régulation financière. Un second chapitre traite de la régulation bancaire de Bâle I aux accords de Bâle III (méthodes de fixation des montants de capital réglementaire pour le risque de crédit, de marché, opérationnel et systémique). Le troisième chapitre est consacré au risque de crédit : règles du comité de Bâle et du CRR en Europe pour la fixation du capital réglementaire (approches standardisée et IRB), avec démonstration de l'origine des formules à partir du modèle de Merton-Vasicek. Les slides sont en anglais, le cours en français.

### Objectifs

- Connaître l'environnement réglementaire des banques
- Connaître les principaux éléments des réglementations prudentielles (accords de Bâle, CRR)
- Comprendre la structure du bilan d'une banque et la notion de distance au défaut
- Maîtriser les approches standard et IRB pour le capital réglementaire
- Connaître les formules réglementaires pour les RWA
- Comprendre l'origine des formules à partir du modèle de Merton-Vasicek
- Savoir modéliser les paramètres bâlois : PD, LGD et EAD

### Plan du cours

1. **Chapter 1 — General introduction. Financial regulation: a brief overview** : Financial risks ; Financial regulation ; Objectives and outline
2. **Chapter 2 — Banking regulation: from Basel I to Basel III** : Basel I and the Cooke ratio ; Basel II and the three pillars ; Basel III ; Basel IV / Basel III.5
3. **Chapter 3 — Credit risk: capital requirements in Basel II and III** : The standardized approach ; The IRB approaches (Basel risk parameters, normalized required capital, maturity adjustment, correlation functions) ; The credit risk model in Basel II ; Loss Given Default (LGD)

### Bibliographie

- BCBS (2004, 2005), *An explanatory note on the Basel II IRB risk weight functions*
- Freixas X. and Rochet J.-C. (2008), *The microeconomics of banking*, MIT Press, 2nd edition
- Gouriéroux C. and Tiomo A. (2007), *Risque de crédit : une approche avancée*, Economica
- Roncalli T. (2014), *La gestion des risques financiers*, Economica, 2ème édition
- Roncalli T. (2020), *Handbook of Financial Risk Management*, Chapman & Hall/CRC

---

## Finance Durable

- **Enseignant** : Yannick LUCOTTE
- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 12h | **ECTS** : 2
- **Prérequis** : Connaissances économiques et financières ; Connaissance des principaux risques bancaires et de l'environnement macroéconomique et financier actuel

### Résumé

Ce cours présente les notions essentielles de finance durable et de risques ESG, et se focalise sur les risques liés aux changements climatiques pour le secteur bancaire et financier. Il vise à mieux comprendre les canaux de transmission par lesquels les risques climatiques peuvent exacerber les risques bancaires traditionnels et à fournir un aperçu des exigences réglementaires récentes.

### Objectifs

- Avoir une vision d'ensemble des enjeux de la finance durable et des risques ESG
- Comprendre les enjeux du changement climatique pour le secteur bancaire et financier
- Comprendre le lien entre changement climatique et risques bancaires traditionnels
- Comprendre le rôle du régulateur et de la banque centrale face aux risques climatiques
- Appréhender les évolutions futures du cadre prudentiel
- Situer les enjeux et impacts pour les banques

### Plan du cours

1. **Section 1** — Risques climatiques et de biodiversité : typologie (risques physiques, de transition, juridiques), notions d'exposition, vulnérabilité, résilience, risques de biodiversité
2. **Section 2** — Canaux de transmission vers les risques bancaires traditionnels (crédit, liquidité, marché, opérationnel, conformité) ; matrice de matérialité
3. **Section 3** — Risques climatiques et secteur immobilier (risques physiques, risque de transition et DPE, actifs échoués, répercussions bancaires)
4. **Section 4** — Intégration des risques climatiques dans les modèles de crédit (PD/LGD)
5. **Section 5** — Données climatiques utilisées par les banques (typologie, sources, défis)
6. **Section 6** — Exigences réglementaires (taxonomie verte européenne, pilier 3 de Bâle III, Green Asset Ratios, calendrier)
7. **Section 7** — Conclusion (évolutions de la politique monétaire de la BCE, perspectives macroprudentielles)

### Bibliographie

- Banque de France (2020), *Le « Cygne Vert »*, Bulletin 229
- Banque de France (2021), *Developing climate transition scenarios*, Bulletin 237
- Basel Committee on Banking Supervision (2021), *Climate-related risk drivers and their transmission channels*
- ECB (2022), *2022 climate risk stress test*

---

## Financial Fraud Detection

- **Enseignant** : Denisa BANULESCU-RADU
- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 12h | **ECTS** : 2
- **Prérequis** : Notions d'économétrie linéaire et des variables qualitatives ; Bases en statistiques, probabilités et optimisation ; Connaissance des méthodes de machine learning (supervisé & non supervisé)

### Résumé

Ce cours forme aux méthodes économétriques et aux techniques d'apprentissage automatique appliquées à la détection de la fraude financière. Après une introduction aux typologies de fraude, deux grandes catégories de modèles sont étudiées : les modèles de prévention (non supervisés, détection de comportements atypiques) et les modèles de détection (supervisés, classification). Un enjeu central est le caractère rare de la fraude et le déséquilibre des bases de données. Le cours inclut un projet pratique.

### Objectifs

- Comprendre les typologies de fraude financière
- Identifier et appliquer les techniques analytiques pour la détection de la fraude
- Mettre en œuvre des méthodes supervisées et non supervisées
- Évaluer des modèles avec des mesures de performance adaptées
- Utiliser les méthodes de rééchantillonnage (oversampling, undersampling, SMOTE)
- Réaliser une étude de cas pratique

### Plan du cours

1. **Chapter 1 — Introduction**
2. **Chapter 2 — Data** : typologies et sources ; opérations sur les données
3. **Chapter 3 — Descriptive analytics (non supervisé)** : détection d'outliers ; clustering
4. **Chapter 4 — Predictive analytics (supervisé)** : régression linéaire ; régression logistique ; arbres de décision ; méthodes d'ensemble (bagging, boosting, random forest)
5. **Chapter 5 — Predictive models for skewed datasets** : undersampling ; oversampling ; ajustement des probabilités ; cost-sensitive learning
6. **Chapter 6 — Evaluation of predictive models** : data splitting ; mesures de performance ; illustration
7. **Chapter 7 — Cost-sensitive learning** : cost matrix ; cost-sensitive logistic regression ; cost-sensitive evaluation metrics ; illustration

### Bibliographie

- Baesens B., Van Vlasselaer V. and Verbeke W. (2015), *Fraud analytics using descriptive, predictive, and social network techniques*, Wiley
- Hastie T., Tibshirani R. and Friedman J. (2009), *The elements of statistical learning*, Springer
- Fernández A. et al. (2018), *Learning from imbalanced data sets*, Springer
- He H. and Ma Y. (2013), *Imbalanced learning: foundations, algorithms, and applications*, Wiley

---

## Techniques de modélisation pour l'ALM

- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 12h | **ECTS** : 2

*Syllabus non disponible en ligne au moment du scraping.*

---

## Communication orale

- **Enseignant** : Christophe HURLIN
- **Année** : M2 | **Semestre** : 9
- **Nature** : CM | **Volume horaire** : 12h | **ECTS** : 2
- **Prérequis** : Présentation d'un projet individuel ou collectif (M2)

### Résumé

L'atelier est organisé en petits groupes de 5 à 8 étudiants. Chaque étudiant réalise une présentation d'un de ses travaux de M2, quelle que soit la matière. Seule la forme est évaluée. Le présentateur joue le rôle d'un consultant en data science présentant à son client les conclusions d'une étude. Chaque présentation est évaluée par tous les membres du groupe, puis l'enseignant synthétise les avis et donne des conseils d'amélioration.

### Objectifs

Former les étudiants à la réalisation de présentations professionnelles adaptées au milieu de la statistique et de la data science : qualité des slides, maîtrise du vocabulaire technique, qualité de l'intonation, caractère pédagogique, dynamisme, mise en valeur des résultats, interaction avec l'assistance et l'écran de projection.

---

## Projets

- **Année** : M2 | **Semestre** : 9
- **ECTS** : 2

*Projets réalisés au cours du semestre.*

---

## Séminaire partenariat SAS

- **Année** : M2 | **Semestre** : 9
- **Nature** : Séminaire | **Sans ECTS**

*Séminaire en partenariat avec SAS France.*

---

## Séminaire entreprise : Outils de lutte contre la fraude financière

- **Intervenante** : Florence GIULIANO, PhD — EMEA Financial Crimes Analytics Director at SAS
- **Année** : M2 | **Semestre** : 9
- **Nature** : Séminaire (1 journée) | **Sans ECTS**

### Résumé

Ce séminaire destiné à des data scientists de niveau M2 forme aux aspects métiers de la lutte contre la fraude. En comprenant les enjeux sectoriels et les méthodologies, les étudiants pourront créer des modèles plus pertinents et mieux collaborer avec les experts du domaine. Le cours couvre la fraude à l'assurance, la fraude bancaire, le blanchiment d'argent, la fraude dans le secteur public, la fraude interne, et les outils de lutte.

### Plan du cours

1. Introduction à la lutte contre la fraude et les crimes financiers
2. La fraude à l'assurance
3. La fraude bancaire
4. Le blanchiment d'argent
5. La fraude dans le secteur public
6. La fraude interne
7. Les outils pour la lutte contre la fraude

---

## Liste complète des matières du Semestre 9 (M2, premier semestre)

Le Semestre 9 (M2, premier semestre) est **commun à l'option professionnelle et à l'option recherche** : tous les étudiants suivent les mêmes cours. Il comprend 15 matières pour un total de 30 ECTS, 168h CM :

**Outils statistiques et économétrie** :
1. Méthodes de Scoring (4 ECTS, 24h CM)
2. Modèles de durée (4 ECTS, 24h CM)

**Big Data Analytics** :
3. BDA : Trees & aggregation methods (Bagging, Random Forests & Boosting) (2 ECTS, 12h CM)
4. BDA : Penalized regressions (Lasso, Adaptive Lasso, Elastic-Net) (2 ECTS, 12h CM)
5. BDA : Support Vector Machine (2 ECTS, 12h CM)
6. BDA : Machine Learning Interprétable (2 ECTS, 12h CM)
7. BDA : NLP with Python (2 ECTS, 12h CM)

**Professionnalisation** :
8. Réglementation prudentielle bancaire (2 ECTS, 12h CM)
9. Finance Durable (2 ECTS, 12h CM)
10. Financial Fraud Detection (2 ECTS, 12h CM)
11. Techniques de modélisation pour l'ALM (2 ECTS, 12h CM)
12. Communication orale (2 ECTS, 12h CM)
13. Projets (2 ECTS)
14. Séminaire partenariat SAS
15. Séminaire entreprise : Outils de lutte contre la fraude financière

**Total Semestre 9** : 30 ECTS, 168h CM

Pour le détail de chaque matière (enseignant, prérequis, plan de cours, bibliographie), consulter les sections correspondantes du syllabus.
