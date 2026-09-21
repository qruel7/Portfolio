# Dynamiques des alternances en Centre-Val de Loire

Atelier "Introduction à SAS" (M1 ESA, Université d'Orléans), réalisé en binôme avec **Njiva Rakoto**.

## Contexte

Ce projet exploite les données de contrats d'apprentissage du CFA des universités, portant sur les étudiants de l'Université d'Orléans de 2017-18 à 2023-24 (composante de formation, intitulé du diplôme, code postal et ville de l'entreprise d'accueil). L'objectif est d'étudier la dynamique de l'apprentissage sur cette période, avec deux angles principaux :

- La répartition géographique des lieux d'alternance, et son évolution dans le temps selon le type de diplôme (DCG/DSCG, DUT, BUT, LP, Master).
- La distance entre le lieu de formation et le lieu d'alternance, en particulier pour les masters — une question posée par les responsables du Master ESA, qui s'interrogent sur la faisabilité d'une mise en apprentissage du M2.

## Méthodologie

- **Import et consolidation** de 7 feuilles Excel annuelles (2017-2018 à 2023-2024) en bibliothèque SAS.
- **Calcul de distances géographiques** entre villes de formation (Orléans, Bourges, Châteauroux, Chartres) et villes d'alternance avec la fonction `GEODIST`.
- **Cartographie** des lieux d'alternance par région et par année avec `PROC GMAP` / `PROC GPROJECT`.
- **Statistiques descriptives et tris à plat** (`PROC FREQ`, `PROC SORT`, `PROC TRANSPOSE`) pour suivre l'évolution des effectifs par type de diplôme.
- **Visualisations** avec `PROC SGPLOT` et `PROC GCHART` (répartition des distances, évolution temporelle).
- Classification des formations de Master en 5 grands domaines (Data Sciences, Droit, Gestion/Commerce, Physique/Chimie, Activité Physique et Sportive) pour affiner l'analyse par spécialité.

## Résultats principaux

- Le nombre d'alternants a presque doublé entre 2017 et 2023, porté notamment par le succès des BUT dès leur création.
- Les lieux d'alternance restent très concentrés en Centre-Val de Loire et en Île-de-France, avec une part croissante de l'Île-de-France pour les Masters.
- Les Masters ont des lieux d'alternance nettement plus éloignés que les BUT/DUT/LP.
- Pour la classe Data Sciences (proxy pertinent pour le Master ESA), la part d'alternances en Île-de-France est passée d'environ 2% en 2018 à près de 30% en 2023 — la plus forte progression parmi les spécialités de Master étudiées, ce qui appuie la faisabilité d'une mise en apprentissage du M2 ESA.

## Données

**Les données ne sont pas incluses dans ce dépôt.** Elles ont été transmises par le CFA des universités, avec son autorisation, pour un usage strictement pédagogique dans le cadre de cet atelier, et ne peuvent pas être diffusées publiquement. Le script est donc fourni pour illustrer la démarche et le code, mais ne peut pas être exécuté tel quel.

## Outils utilisés

- **SAS** (SAS Studio recommandé)
- Procédures : `PROC IMPORT`, `PROC SORT`, `PROC FREQ`, `PROC TRANSPOSE`, `PROC GMAP`, `PROC GPROJECT`, `PROC GCHART`, `PROC SGPLOT`
- Fonction `GEODIST` pour le calcul de distances géographiques

## Consulter le code

**Ouvrir de préférence le script avec SAS Studio** plutôt qu'un éditeur de texte classique : l'encodage des caractères accentués (libellés et commentaires en français) peut être mal interprété autrement, produisant des symboles corrompus ou des erreurs à l'exécution.

Le script utilise des chemins de fichiers absolus (`libname` et `PROC IMPORT` en tête de script), propres à l'environnement local d'origine.

## Fichiers du projet

- `ScriptDynamiquesAlternancesSAS.sas` — code source de l'analyse
- `DynamiquesAlternancesSAS.pptx` — présentation des résultats
