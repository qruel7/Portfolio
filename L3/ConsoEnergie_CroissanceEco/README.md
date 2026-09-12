# Consommation d'énergie et croissance économique

Projet de macroéconométrie (Université de Tours), réalisé en groupe avec **Zaccharie Ennya, Thomas Barat, Bastien Coureau et Pierre Hardy**.

## Contexte

Ce projet étudie la relation entre consommation d'énergie et croissance économique à l'échelle mondiale, à partir de données macroéconomiques de la Banque Mondiale (1970–2014). L'hypothèse de départ, appuyée sur une revue de littérature (Kraft & Kraft 1978, Apergis & Payne 2009, Giraud & Kahraman 2014, entre autres), est l'existence d'une relation positive et bilatérale entre les deux variables : la consommation d'énergie stimule la croissance, et la croissance stimule en retour la consommation d'énergie.

Le projet se prolonge par une analyse de la viabilité d'une transition énergétique : la baisse de la dépendance aux énergies non-renouvelables pénalise-t-elle la croissance ?

## Méthodologie

- **Revue de littérature** sur la relation énergie/croissance, à partir de la fonction de production de type Cobb-Douglas.
- **Modèle log-linéaire bilatéral** sur données mondiales 1970-2014 :
  - `Ln(PIB) = c + α·Ln(Capital) + Ln(Population) + Ln(Énergie) + µ`
  - `Ln(Énergie) = c + α·Ln(Capital) + Ln(Population) + Ln(PIB) + µ`
- **Analyse historique** : effet des chocs pétroliers de 1973, 1979 et 2008 sur la consommation d'énergie et le PIB mondial par tête.
- **Modèle de transition énergétique** sur un panel de 18 pays représentatifs (un par grande zone géographique/niveau de développement), avec une indicatrice de transition écologique (part d'énergies renouvelables > 40%) et un terme d'interaction avec la consommation d'énergie.

## Résultats principaux

- Une corrélation positive est observée à l'échelle mondiale entre consommation d'énergie et PIB, dans les deux sens (les deux régressions vont dans le même sens).
- Les chocs pétroliers de 1973, 1979 et 2008 coïncident avec des ralentissements simultanés de la consommation d'énergie et de la croissance du PIB par tête, ce qui corrobore le lien entre les deux variables.
- Dans le modèle sur 18 pays, l'indicatrice de transition énergétique n'a pas d'effet statistiquement significatif sur la croissance du PIB, bien que son coefficient soit négatif (~-0,3 point de croissance) — ce qui suggère qu'une transition vers les renouvelables n'est pas nécessairement synonyme de ralentissement économique significatif, bien qu'un effet négatif faible et non significatif soit mesuré.

## Limites identifiées

- Panel restreint à 18 pays pour le modèle de transition énergétique, ce qui limite la puissance statistique du test.
- Variables de contrôle importantes (technologie, taux d'épargne, stabilité politique) non disponibles ou incomplètes, non incluses dans le modèle.
- Les données mondiales et par pays présentent des valeurs manquantes après 2014, réduisant la période d'analyse exploitable.

## Outils et packages utilisés

- **R** avec rendu R Markdown en PDF (mise en page LaTeX personnalisée)
- `readxl` pour l'import des données Excel
- `stargazer` pour les tables de régression
- `ggplot2`, `patchwork`, `ggpubr`, `gridExtra` pour les visualisations

## Reproduire l'analyse

```r
rmarkdown::render("pdf_projet.Rmd")
```

## Fichiers du projet

- `pdf_projet.Rmd` — code source de l'analyse
- `ConsoEnergie_CroissanceEco.pdf` — rapport compilé (rendu final)
- `data_reg1.xlsx` — données PIB/énergie/population/capital, échelle mondiale (Banque Mondiale)
- `data_tqt.xlsx` — données PIB par tête et consommation d'énergie par tête, échelle mondiale (Banque Mondiale)
- `DataExcel3.xlsx` — données par pays sur 18 pays (PIB, énergie, inflation, importations, part d'énergies renouvelables) (Banque Mondiale)
- `utlogo.png` — logo de l'Université de Tours (mise en page du rapport)
- `image2.png` — illustration en page de garde
