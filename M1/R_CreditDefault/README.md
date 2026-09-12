# Modélisation de la probabilité de défaut de crédit

Projet individuel R Markdown (M1 ESA, Université d'Orléans). Trois livrables produits à partir d'une même base de données : un rapport dynamique, une présentation, et un tableau de bord interactif.

## Contexte

Ce projet modélise la probabilité de défaut de paiement de clients titulaires d'une carte de crédit, à partir de leurs caractéristiques sociodémographiques (sexe, âge, niveau d'éducation, situation familiale) et de leur historique de remboursement sur six mois. La base compte 30 000 clients et 23 variables explicatives, avec un taux de défaut observé de 22,1%. **Les clients de la base de données sont fictifs.**

## Méthodologie

- **Cadre économétrique** : modélisation de la probabilité de défaut via une variable latente, conduisant aux modèles **Logit** (résidus logistiques) et **Probit** (résidus gaussiens), estimés par maximum de vraisemblance.
- **Sélection de variables** : analyse des corrélations pour repérer la forte multicolinéarité entre les 18 variables temporelles (retards, encours, remboursements sur 6 mois), puis sélection **stepwise** sur critère AIC, réduisant le modèle de 23 à 18 variables.
- **Effets marginaux** (Average Marginal Effects) pour traduire les coefficients en variation de probabilité, les coefficients bruts d'un Logit/Probit n'étant pas directement interprétables.
- **Évaluation des performances** : matrice de confusion, courbe ROC, AUC, seuil optimal de Youden, comparaison par critères d'information (AIC/BIC).
- **Vérification de robustesse** : réplication des estimations sous **Python** (statsmodels) et **SAS** (`PROC LOGISTIC`) en annexe du rapport, pour confirmer que les résultats ne dépendent pas du logiciel utilisé.

## Résultats principaux

- L'historique de retard de paiement est de loin le prédicteur le plus discriminant : le taux de défaut passe de ~15% (sans retard) à plus de 60% au-delà de 2 mois de retard.
- Le modèle Logit retient 18 variables après sélection stepwise, avec un effet marginal du retard de septembre 2023 de +8,6 points de probabilité de défaut par niveau de retard supplémentaire — largement devant les autres facteurs.
- Les variables sociodémographiques (sexe, niveau d'éducation, situation familiale) ont un effet significatif mais nettement plus modeste (entre -1,5 et -2,3 points).
- Logit et Probit produisent des résultats très proches (coefficients Logit ≈ 1,6 × Probit, conformément à la théorie), avec une AUC d'environ 0,72 pour les deux modèles — une capacité de discrimination acceptable mais modérée.
- Le modèle Logit est retenu au final (AIC et BIC légèrement inférieurs à ceux du Probit).
- Les résultats sont confirmés à l'identique sous Python et SAS, validant la robustesse des estimations indépendamment du logiciel.

## Livrables

1. **Rapport** (`Rapport_cred_defaut.Rmd` → PDF) : analyse complète, du cadre théorique à l'annexe de robustesse multi-logiciels.
2. **Slides Beamer** (`slides_beamer_1.Rmd` → PDF) : synthèse de la présentation en 12 slides, avec thème et charte graphique personnalisés (logos Université d'Orléans / Master ESA en pied de page).
3. **Tableau de bord interactif** (`dashboard_2.Rmd` → HTML, `flexdashboard`) : indicateurs clés, graphiques interactifs (`plotly`), courbe ROC et résultats des modèles, navigable directement dans le navigateur.

## Outils et packages utilisés

- **R** / RStudio, rendu R Markdown (pdflatex pour les PDF)
- `stargazer` pour les tables de régression, `margins` pour les effets marginaux
- `pROC` pour les courbes ROC/AUC
- `flexdashboard`, `plotly`, `DT` pour le tableau de bord interactif
- `reticulate` pour l'exécution de code Python directement depuis R (annexe de robustesse)
- Python (`statsmodels`, `scikit-learn`) et SAS (`PROC LOGISTIC`) pour la vérification croisée des résultats

## Reproduire l'analyse

```r
rmarkdown::render("Rapport_cred_defaut.Rmd")
rmarkdown::render("slides_beamer_1.Rmd")
rmarkdown::render("dashboard_2.Rmd")
```

## Fichiers du projet

- `Rapport_cred_defaut.Rmd` / `.pdf` — rapport complet
- `slides_beamer_1.Rmd` / `.pdf` — présentation Beamer
- `dashboard_2.Rmd` / `.html` — tableau de bord interactif
- `bibliographie.bib` — références bibliographiques citées dans le rapport
- `credit_defaut.xlsx` — jeu de données fictif (clients simulés), avec une structure inspirée du dataset public "Default of Credit Card Clients" (UCI Machine Learning Repository)
- `logo univ orleans.png`, `logo esa vertical.jpg`, `logo esa horizontal.jpg` — logos utilisés dans la mise en page des documents
