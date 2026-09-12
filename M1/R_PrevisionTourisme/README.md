# Prévision des arrivées de touristes par méthodes de décomposition

Projet de méthodes de prévision (M1 ESA, Université d'Orléans), réalisé en binôme avec **Olivier Baudouin**.

## Contexte

Ce projet prévoit les arrivées mensuelles de touristes dans un pays sur l'horizon 06/2025 à 06/2027, à partir d'un historique de 112 observations (02/2016 à 05/2025). La principale difficulté méthodologique est la rupture structurelle liée au COVID-19, qui a provoqué un effondrement quasi-total des arrivées entre mars 2020 et fin 2022 : appliquer une décomposition classique sans précaution produirait des prévisions fortement biaisées.

## Méthodologie

- **Diagnostic du schéma de décomposition** : trois indicateurs convergents (méthode de la bande, méthode du profil, corrélation amplitude/niveau = 0,918) confirment un schéma **multiplicatif**.
- **Décomposition manuelle en 5 étapes**, codée sans la fonction `decompose()` de R (moyenne mobile centrée d'ordre 12, série des quotients, coefficients saisonniers bruts puis centrés, série corrigée des variations saisonnières), détaillée pédagogiquement sur la période pré-COVID.
- **Trois stratégies comparées pour traiter la rupture COVID**, chacune évaluée par backtesting sur 12 mois (RMSE, MAPE) :
  - **Approche A (naïve)** : décomposition sur la série complète sans traitement particulier — sert de baseline pour quantifier le biais introduit par la rupture.
  - **Approche B (pré-COVID)** : décomposition restreinte à la période antérieure à la pandémie (02/2016-02/2020).
  - **Approche C (imputation contrefactuelle)** : remplacement des observations COVID (03/2020-12/2022) par une projection contrefactuelle basée sur la dynamique pré-COVID (tendance + saisonnalité), afin d'exploiter l'intégralité de l'historique sans les biais de la période pandémique.
- **Prévisions finales** produites par le modèle retenu, avec un intervalle de confiance approximatif à 80% basé sur l'écart-type des résidus de la décomposition.

## Résultats principaux

| Approche | Période de test | Obs. train | RMSE | MAPE |
|---|---|---|---|---|
| A — Naïve (série complète) | 06/2024-05/2025 | 100 | 1,049 M | **57,2%** |
| B — Pré-COVID uniquement | 03/2019-02/2020 | 37 | 0,114 M | 4,77% |
| C — Imputation contrefactuelle | 06/2024-05/2025 | 100 | 0,112 M | 5,51% |

- L'approche naïve (A) est totalement inutilisable (MAPE de 57%), ce qui valide empiriquement la nécessité d'un traitement spécifique de la rupture structurelle.
- Les approches B et C donnent des performances quasi-équivalentes (MAPE ~5%), ce qui constitue en soi un résultat notable : les prévisions construites sur la dynamique pré-COVID se sont effectivement réalisées en post-COVID — le secteur du tourisme a bien « rattrapé » sa trajectoire structurelle antérieure.
- **L'approche C est retenue** pour les prévisions finales : elle exploite l'intégralité des 112 observations (contre 49 pour B), ce qui rend les estimations plus robustes sur un horizon de projection long, et sa période de backtesting est immédiatement adjacente à la période de prévision.

## Outils et packages utilisés

- **R**, rendu R Markdown en PDF (mise en page LaTeX avec en-tête/pied de page personnalisés)
- `readxl` pour l'import des données
- Fonctions de décomposition codées manuellement (moyenne mobile centrée, calcul des coefficients saisonniers), encapsulées dans une fonction réutilisable `mm_centree()`
- Régression linéaire (`lm()`) pour l'extrapolation de la tendance et la construction du contrefactuel

## Reproduire l'analyse

```r
rmarkdown::render("rapport_projet.Rmd")
```

## Fichiers du projet

- `rapport_projet.Rmd` / `.pdf` — rapport complet
- `data_mdp.xlsx` — série mensuelle des arrivées touristiques (données génériques, aucune information sensible)
- `logo univ orleans.png`, `logo esa vertical.jpg`, `logo esa horizontal.jpg` — logos utilisés dans la mise en page des documents
