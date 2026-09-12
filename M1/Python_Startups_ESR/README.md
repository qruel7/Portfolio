# Start-ups liées à l'enseignement supérieur et à la recherche

Projet de programmation Python avancée (M1 ESA, Université d'Orléans), réalisé en binôme avec **Olivier Baudouin**.

## Contexte

Ce projet analyse la base de données publique des start-ups françaises liées à des structures d'enseignement supérieur et de recherche (ESR), publiée sur [data.gouv.fr](https://www.data.gouv.fr/datasets/les-start-ups-liees-a-lenseignement-superieur-et-a-la-recherche-academique-francaise). L'objectif est double : nettoyer et structurer un jeu de données réel aux colonnes multi-valuées, puis construire un programme interactif permettant d'explorer les partenariats entre une structure ESR donnée et les start-ups qui lui sont liées.

## Méthodologie

- **Import direct depuis l'URL source** (pas de fichier local à télécharger manuellement) et **typage rigoureux** des colonnes (dates en `datetime` avec gestion des erreurs, statut en booléen nullable, identifiants en `Int64`, catégories en `category`).
- **Gestion des cellules multi-valuées** (plusieurs types d'actifs ou structures partenaires séparés par des virgules) via une fonction `ensemble_valeurs()` réutilisée dans tout le programme.
- **Bibliothèque de fonctions génériques et réutilisables** pour répondre aux 4 axes d'analyse demandés :
  - Organisation des partenariats (`startups_liees`, `st_partenaires`)
  - Implantation géographique (`nb_par_lieu`, `impl_partenaires`)
  - Start-ups ayant cessé leur activité, avec calcul de durée de vie (`startups_fermees`, `partenaires_fermees`)
  - Répartition des actifs produits (brevets, logiciels...) (`avec_actif`, `nb_par_categorie`, `tracer_rep_actifs`)
- **Programme interactif en ligne de commande** : l'utilisateur choisit une structure ESR, puis navigue dans un menu (partenariats, répartition géographique, start-ups fermées, actifs, rapport complet) avec possibilité de changer de structure sans redémarrer le programme.
- **Extensions choisies** (au-delà du sujet obligatoire) :
  - **Cartographie avec GeoPandas** : cartes de France (régions et départements) illustrant la répartition géographique des start-ups et leur taux de fermeture, à partir d'un GeoJSON chargé directement depuis GitHub.
  - **Export PDF** des rapports (global et par structure ESR) avec la bibliothèque `reportlab`.

## Résultats principaux

- Mise en évidence des structures ESR les plus connectées à l'écosystème start-up et de leurs partenaires géographiquement.
- Cartographie de la répartition régionale des start-ups liées à l'ESR et de leur taux de fermeture.
- Calcul de la durée de vie moyenne des start-ups fermées, globalement et par région.
- Analyse de la répartition des types d'actifs (brevets, logiciels, marques...) parmi les start-ups en possédant au moins un.

## Note de transparence

Comme indiqué dans notre rapport, les fonctions de génération de rapports PDF (`generer_pdf`, `generer_pdf_structure`, bibliothèque `reportlab`) ont été développées avec l'aide d'une IA générative, dont nous avons vérifié, adapté et commenté le fonctionnement dans le script. Le reste du programme (nettoyage des données, fonctions d'analyse, logique du menu interactif) a été rédigé entièrement par nos soins.

## Outils et packages utilisés

- **Python**, `pandas` pour la manipulation de données
- `matplotlib` pour les histogrammes
- `geopandas` pour la cartographie
- `reportlab` pour l'export PDF

## Reproduire l'analyse

```bash
python script_final_prj1.py
```
Le script télécharge les données directement depuis leur URL source et ne nécessite aucun fichier local préalable (hormis les dépendances Python : `pandas`, `matplotlib`, `geopandas`, `reportlab`).

## Fichiers du projet

- `script_final_prj1.py` — code source complet (nettoyage, fonctions d'analyse, programme interactif)
- `rapport_projet.pdf` — rapport détaillant les choix techniques et méthodologiques
- `sujet.pdf` — sujet du projet
