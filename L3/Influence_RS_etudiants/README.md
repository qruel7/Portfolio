# L'influence des réseaux sociaux dans le quotidien des étudiants

Projet de statistiques descriptives réalisé en L3 Économie (Université de Tours), en binôme avec **Ennya Zaccharie**.

## Contexte

Ce projet cherche à mesurer la place qu'occupent les réseaux sociaux dans le quotidien des étudiants, à partir d'un sondage mené par notre professeure auprès de 208 étudiants de l'Université de Tours (205 conservés après exclusion de deux répondants aux réponses incohérentes). L'échantillon est majoritairement composé d'étudiants en filière Économie.

Quatre hypothèses de départ guident l'analyse :
- Plus un étudiant passe de temps sur les réseaux sociaux, moins il consacre de temps à son travail personnel.
- Les étudiants se dirigent davantage vers des applications de divertissement comme TikTok.
- Le genre n'influence pas le temps passé sur les réseaux sociaux.
- Plus un étudiant est jeune, plus il passe de temps sur les réseaux sociaux.

## Méthodologie

- **Statistique descriptive** : diagrammes en boîte, tableaux croisés, histogrammes en fonction du genre et de l'âge.
- **Tests d'indépendance du χ²** pour évaluer le lien entre genre/âge et préférence de réseau social.
- **Test de corrélation de Pearson** entre l'âge et le temps passé sur les réseaux sociaux.
- **Test de Student** pour comparer les moyennes de temps de travail personnel selon le niveau d'utilisation des réseaux sociaux.

## Résultats principaux

- Le genre n'a pas d'effet significatif sur les préférences de réseau social (test du χ²), mais les femmes de l'échantillon passent en moyenne 45 minutes de plus par jour sur les réseaux sociaux que les hommes.
- Une corrélation négative (~-0,1) est observée entre l'âge et le temps passé sur les réseaux sociaux : les étudiants les plus jeunes s'avèrent légèrement plus utilisateurs.
- Instagram domine très largement les préférences, quel que soit l'âge ; Facebook et Twitter n'apparaissent que chez les étudiants les plus âgés du panel (22 ans et plus).
- Un temps d'utilisation des réseaux sociaux plus élevé est associé à un temps de travail personnel plus faible, confirmant l'hypothèse initiale sur ce point.

## Données

Le fichier `sondage_version_finale.csv` est une version nettoyée d'un sondage réalisé par notre professeure auprès des étudiants de l'Université de Tours. Les données ne contiennent aucun identifiant nominatif (pas de nom, email ou numéro étudiant).

## Outils et packages utilisés

- **R** avec RStudio, rendu R Markdown en HTML (thème `journal`, sommaire flottant)
- `dplyr`, `forcats` pour la manipulation des données
- `ggplot2`, `ggridges` pour les visualisations
- `knitr`, `kableExtra` pour les tableaux mis en forme

## Reproduire l'analyse

Le rapport se génère avec RStudio en ouvrant `vfinal_projet.Rmd` et en cliquant sur "Knit", ou en ligne de commande :

```r
rmarkdown::render("vfinal_projet.Rmd")
```

## Fichiers du projet

- `vfinal_projet.Rmd` — code source de l'analyse
- `Etudiants_RS.html` — rapport compilé (rendu final)
- `sondage_version_finale.csv` — jeu de données du sondage
