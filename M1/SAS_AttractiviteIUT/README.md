# Attractivité des IUT sur Parcoursup

Projet personnel réalisé en M1 ESA (Université d'Orléans), en dehors de tout cadre obligatoire, pour s'entraîner à la programmation SAS sur un jeu de données réel et volumineux (118 variables).

## Contexte

À partir des données ouvertes Parcoursup 2024 (14 000+ formations, publiées par le ministère de l'Enseignement supérieur et de la Recherche), ce projet mesure l'attractivité de l'IUT d'Orléans par rapport aux autres IUT de France, indépendamment des spécialités de BUT proposées : reçoit-il beaucoup ou peu de candidatures au regard de ses capacités d'accueil ? Comment se positionne-t-il par rapport aux autres IUT de l'académie Orléans-Tours et du reste de la France ?

## Méthodologie

1. **Répartition des BUT** en France et dans l'académie Orléans-Tours, avec cartographie du ratio candidatures/place disponible par IUT (`PROC GMAP`, `PROC GPROJECT`).
2. **Score d'attractivité** construit par IUT, avec classement de l'ensemble des IUT de France et analyse de sa relation avec la population de la ville d'implantation (`PROC SQL`, `PROC MEANS`, `PROC SGPLOT`).
3. **Score de qualité des étudiants admis**, mis en relation avec le score d'attractivité pour vérifier une éventuelle corrélation entre les deux indicateurs.
4. **Respect de la proportion réglementaire de bacheliers technologiques** (minimum légal de 50% en moyenne) par formation et par IUT, avec segmentation des BUT en classes de spécialité (`PROC STANDARD`, `PROC PRINCOMP`) pour comparer la demande selon le domaine.

## Résultats principaux

- L'IUT d'Orléans se classe **57ème sur 189** IUT français, avec un score d'attractivité de 34,334 — un positionnement dans la moyenne haute.
- Une corrélation positive nette apparaît entre le score d'attractivité d'un IUT et la population de sa ville d'implantation : les candidats BUT privilégient les villes plus dynamiques, offrant davantage d'activités et de vie étudiante.
- L'analyse par domaine de spécialité met en évidence des écarts marqués dans la demande (diagrammes en boîte comparatifs).
- Une piste bonus explore le calcul de z-scores par IUT à partir des différents indicateurs pour affiner le classement.

## Outils utilisés

- **SAS** (SAS Studio recommandé)
- Procédures : `PROC IMPORT`, `PROC SQL`, `PROC MEANS`, `PROC STANDARD`, `PROC PRINCOMP`, `PROC GMAP`, `PROC GPROJECT`, `PROC GCHART`, `PROC SGPLOT`, `PROC FREQ`
- Macro-variables et macro-fonctions SAS pour automatiser la manipulation des groupes de variables (118 colonnes)

## Reproduire l'analyse

**Ouvrir de préférence le script avec SAS Studio** plutôt qu'un éditeur de texte classique : l'encodage des caractères accentués (variables et libellés en français) peut être mal interprété autrement, produisant des symboles corrompus ou des erreurs à l'exécution.

Le script utilise des chemins de fichiers absolus (`libname` en tête de script) qu'il faut adapter à l'emplacement local des fichiers Excel avant exécution.

## Fichiers du projet

- `ScriptIUTAttractivity.sas` — code source de l'analyse
- `donnees_good.xlsx` — données Parcoursup 2024 nettoyées (source : [data.enseignementsup-recherche.gouv.fr](https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-parcoursup/information/))
- `all_villes_pop.xlsx` — référentiel de population des villes françaises, utilisé pour l'analyse de corrélation attractivité/population
