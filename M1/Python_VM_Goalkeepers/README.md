# Prédiction de la valeur marchande des gardiens de but

Projet de programmation Python avancée (M1 ESA, Université d'Orléans), réalisé en binôme avec **Olivier Baudouin**. Sujet libre : choix d'un jeu de données personnel, ici autour du football.

## Contexte

Ce projet construit un modèle de machine learning pour prédire la valeur marchande des gardiens de but des cinq grands championnats européens (Premier League, Liga, Serie A, Bundesliga, Ligue 1) sur la période 2018-2023, à partir de leurs statistiques de performance et de caractéristiques personnelles.

## Sources de données

- **Statistiques de performance des gardiens** : [FBref](https://fbref.com), via le repository GitHub [hadjdeh/football-data-analysis](https://github.com/hadjdeh/football-data-analysis)
- **Valeurs marchandes et informations joueurs** : [Transfermarkt](https://www.transfermarkt.com), via le projet [transfermarkt-datasets de dcaribou](https://github.com/dcaribou/transfermarkt-datasets)

Les deux sources sont chargées **directement par URL** dans le script (téléchargement CSV brut pour FBref, téléchargement + décompression en mémoire des `.csv.gz` pour Transfermarkt) : aucun fichier de données local n'est nécessaire pour exécuter le projet.

## Méthodologie

### Préparation des données
- Jointure des statistiques FBref avec les valeurs marchandes Transfermarkt via le nom du joueur et la saison, après filtrage des gardiens des 5 grands championnats.
- Conversion de l'âge du format `années-jours` en décimal, du contrat en mois restants à la fin de la saison, regroupement des nationalités peu représentées.
- Création de variables dérivées : pourcentage de victoires, arrêts par 90 minutes, et surtout la valeur marchande de la saison précédente (`market_value_prev`), décisive pour la performance du modèle final.
- Découpage Train (saisons 2018-2019 à 2021-2022) / Test (saison 2022-2023) — la saison 2023-2024, disponible mais incomplète (arrêtée en mars), a été écartée pour ne pas biaiser l'évaluation.

### Analyse et visualisation
Trois analyses statistiques, chacune avec une fonction de calcul et une fonction d'affichage dédiées :
1. Évolution de la valeur marchande moyenne par championnat au fil des saisons.
2. Matrice de corrélation entre statistiques de performance et valeur marchande (heatmap).
3. Comparaison des profils entre le top 20% et le bottom 20% des gardiens les mieux valorisés.

### Prédiction
- **Sélection de variables forward** : ajout itératif de la variable qui maximise le R² moyen en validation croisée, arrêt quand le gain devient inférieur à 0,005.
- **Modèle** : `GradientBoostingRegressor` (scikit-learn), avec la cible passée en log pour gérer l'asymétrie de la distribution des valeurs marchandes.
- Deux versions comparées : sans puis avec la variable `market_value_prev`.

### Programme et extension
Menu interactif en ligne de commande (8 actions : les 3 analyses, les 2 modèles de prédiction, leur comparaison visuelle, une fiche individuelle de gardien, et la sortie). L'extension "fiche gardien" permet de consulter les informations d'un gardien choisi (club, sélections, pied fort...), sa valeur marchande réelle et prédite, et son évolution saison par saison sur un graphique.

## Résultats principaux

| Modèle | Variables retenues | R² validation croisée | R² test | Erreur moyenne |
|---|---|---|---|---|
| Sans `market_value_prev` | 7 (dont sélections internationales, % victoires, âge) | ~0,76 | 0,37 | > 4 M€ |
| Avec `market_value_prev` | 4 (`market_value_prev`, % clean sheets, âge, matchs débutés) | ~0,89 | **0,81** | ~2,7 M€ |

- La valeur marchande précédente concentre plus de 86% de l'importance du modèle final : la valorisation d'un gardien est très inertielle d'une saison à l'autre.
- Les statistiques de performance seules expliquent moins d'un tiers de la variance de la valeur marchande — insuffisantes pour un modèle prédictif fiable sans historique.
- La Premier League valorise nettement le plus ses gardiens (~14 M€ en moyenne), la Bundesliga le moins (~4 M€).
- Les sélections internationales sont la statistique la plus corrélée à la valeur marchande (0,56), suivies du pourcentage de victoires (0,37) et de clean sheets (0,33).

## Outils et packages utilisés

- **Python**, `pandas`, `numpy` pour la manipulation de données
- `requests`, `gzip`, `io` pour le chargement des fichiers compressés à distance
- `matplotlib`, `seaborn` pour les visualisations
- `scikit-learn` (`GradientBoostingRegressor`, `OneHotEncoder`, `cross_val_score`) pour la modélisation

## Reproduire l'analyse

```bash
python script_p3_clean.py
```
Le script télécharge toutes les données nécessaires directement depuis leurs sources (GitHub, Cloudflare R2) au lancement — aucun fichier local requis, hormis les dépendances Python (`pandas`, `numpy`, `requests`, `matplotlib`, `seaborn`, `scikit-learn`).

## Fichiers du projet

- `script_p3_clean.py` — code source complet (préparation, analyse, modélisation, programme interactif)
- `rapport_projet3.pdf` — rapport détaillant les choix techniques et méthodologiques
- `sujet.pdf` — sujet du projet
