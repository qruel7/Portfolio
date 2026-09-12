# Application de scoring bancaire (R Shiny)

Projet individuel R Shiny (M1 ESA, Université d'Orléans). Application interactive permettant d'explorer un modèle de scoring de crédit et d'estimer le risque de défaut d'un nouveau client, sans avoir à toucher au code. Utilise le même jeu de données fictif que le [projet R Markdown de modélisation du défaut de crédit].

## Contexte

L'application s'adresse à un utilisateur ne connaissant ni R, ni les modèles économétriques mobilisés. Elle est construite autour de quatre onglets :

1. **Présentation** — objet de l'application, description de la base de données (30 000 clients, taux de défaut observé) et présentation synthétique des modèles Logit/Probit.
2. **Données** — exploration interactive : tableau filtrable selon le statut de défaut, histogramme et statistiques descriptives pour une variable choisie par l'utilisateur, comparaison de cette variable entre défauts et non-défauts.
3. **Modélisation** — paramétrage du modèle par l'utilisateur : sélection des variables explicatives par case à cocher (5 minimum), curseur pour la proportion train/test (60-80%), table de régression, courbe ROC interactive avec AUC, matrice de confusion à seuil réglable, taux d'erreur/sensibilité/spécificité.
4. **Prédiction** — saisie des caractéristiques d'un nouveau client, calcul du score linéaire et de la probabilité de défaut prédite, attribution automatique d'une note de crédit (grille AAA à B) et de la décision associée.

## Fonctionnement technique

- Les modèles Logit et Probit sont **estimés une seule fois par session** selon une logique réactive, puis partagés entre les onglets Modélisation et Prédiction — pas de ré-estimation inutile à chaque interaction.
- **Sélection de variables à deux niveaux** : l'exploration des données (onglet Données) expose l'ensemble des variables disponibles, tandis que la modélisation ne propose que le sous-ensemble jugé pertinent (issu d'une sélection stepwise préalable) — un choix de conception délibéré pour ne pas noyer l'utilisateur dans des variables redondantes lors de l'estimation.
- `set.seed()` fixe la partition aléatoire train/test pour la reproductibilité.
- Tous les graphiques interactifs sont produits avec `plotly` (natif ou via `ggplotly()`).
- Le logo est injecté à l'extrême droite de la barre de navigation via jQuery + CSS (`position: absolute`), une disposition non couverte par les arguments natifs de `navbarPage()`.

## Outils et packages utilisés

- **R Shiny**, `bslib` pour le thème et la mise en page
- `DT` pour le tableau filtrable
- `plotly`, `ggplot2` pour les visualisations interactives
- `pROC` pour la courbe ROC et l'AUC
- `stargazer` pour la table de régression

## Lancer l'application

```r
shiny::runApp()
```
`credit_defaut.csv` doit se trouver dans le même dossier que `app.R` (chargement par chemin relatif). Tous les packages requis sont déclarés en tête de fichier via `library()`.

## Fichiers du projet

- `app.R` — code source complet de l'application (UI + serveur)
- `credit_defaut.csv` — jeu de données fictif (mêmes clients simulés que le projet R Markdown)
