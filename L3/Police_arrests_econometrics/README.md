# Étude économétrique : probabilité d'être arrêté par la police

Projet de Licence (Université de Tours), réalisé en binôme avec **Zaccharie Ennya**.

## Contexte

Ce projet étudie les déterminants du nombre d'arrestations par la police en 1986, à partir du jeu de données `crime1` (Wooldridge), portant sur 2 725 hommes nés en Californie entre 1960 et 1961, ayant tous déjà été arrêtés au moins une fois avant 1986. Les variables disponibles couvrent la proportion d'arrestations passées ayant mené à condamnation, la durée moyenne des peines, le temps passé en prison, le nombre de trimestres en emploi et le revenu disponible en 1986.

## Méthodologie

Quatre régressions successives par MCO (moindres carrés ordinaires), avec une complexité croissante :

1. **Régression 1** — modèle linéaire de base sur les 5 variables explicatives.
2. **Régression 2** — ajout du carré du revenu disponible (`inc86²`) pour capturer une relation non linéaire entre revenu et nombre d'arrestations.
3. **Régression 3** — remplacement de la variable continue `pcnv` par une indicatrice binaire `condamne` (déjà condamné avant 1986 ou non).
4. **Régression 4** — ajout d'un terme d'interaction entre `qemp86` (trimestres en emploi) et `condamne`, pour tester si l'effet de l'emploi sur les arrestations diffère selon le passé judiciaire.

Diagnostics et corrections :
- **Test de Breusch-Pagan** pour détecter l'hétéroscédasticité des résidus.
- **Écarts-types robustes (HC0)** pour corriger les erreurs-types en présence d'hétéroscédasticité.

## Résultats principaux

- Les modèles expliquent peu la variance du nombre d'arrestations (R² ajusté ≈ 5% dans tous les cas) : l'échantillon (hommes déjà arrêtés au moins une fois, nés en Californie sur deux années précises) et les variables disponibles ne suffisent pas à bien capturer le phénomène.
- Le nombre de mois passés en prison, la proportion de condamnations passées et le revenu disponible ont un effet négatif et significatif sur le nombre d'arrestations en 1986.
- La relation entre revenu disponible et arrestations suit une courbe en U : le risque d'arrestation augmente à la fois pour les très faibles et les très hauts revenus.
- L'effet du nombre de trimestres travaillés sur les arrestations diffère significativement selon le passé judiciaire : il est positif pour les personnes jamais condamnées, mais négatif pour celles déjà condamnées.
- Un test de Breusch-Pagan révèle une hétéroscédasticité significative, partiellement mais pas totalement corrigée par les écarts-types robustes.

## Limites identifiées

- Échantillon restreint (2 725 observations) et non représentatif de la population générale (uniquement des hommes déjà interpellés au moins une fois).
- Variables explicatives potentiellement insuffisantes : des facteurs importants (origine géographique, environnement familial, etc.) ne sont pas disponibles dans les données.
- Possible endogénéité entre le temps passé en prison et le nombre de trimestres travaillés, ces deux variables étant mécaniquement liées.

## Outils et packages utilisés

- **R** avec rendu R Markdown en PDF (mise en page LaTeX personnalisée)
- `haven` pour l'import du fichier `.dta`
- `stargazer` pour les tables de régression
- `lmtest`, `sandwich` pour les tests d'hétéroscédasticité et les écarts-types robustes
- `ggplot2`, `patchwork`, `ggpubr` pour les visualisations
- `knitr`, `kableExtra` pour les tableaux mis en forme

## Reproduire l'analyse

```r
rmarkdown::render("Projet.Rmd")
```

## Fichiers du projet

- `Projet.Rmd` — code source de l'analyse
- `EtudeEconometriquePolice.pdf` — rapport compilé (rendu final)
- `crime1_simplified.dta` — jeu de données (dataset `crime1`, Wooldridge)
- `UT-logo.jpg` — logo de l'Université de Tours (mise en page du rapport)
- `arrestation.jpg` — illustration en page de garde
