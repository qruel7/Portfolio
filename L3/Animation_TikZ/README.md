# Voiture animée en TikZ

Petit projet personnel réalisé en L3 (Université de Tours), en dehors de tout cadre obligatoire, à la suite d'un cours introduisant le package TikZ de LaTeX.

## Contexte

Une voiture roule le long d'une route, croise un panneau de limitation de vitesse, une maison, des arbres et des lampadaires éclairés. Chaque élément (carrosserie, roues, phares, décor) est dessiné à la main par des coordonnées et des tracés géométriques TikZ — aucune image externe n'est utilisée, tout le rendu est vectoriel.

## Fonctionnement technique

L'animation est construite avec `\multiframe` (package `animate`), qui génère 360 images successives d'une même scène TikZ en faisant varier une variable `\i` : cette variable décale la position de la voiture et fait tourner ses roues (via `rotate around`).

**Limite connue** : l'animation embarquée ne se lit que dans **Adobe Acrobat / Adobe Reader**, car elle repose sur les actions JavaScript du standard PDF (`animate`, `media9`), que la plupart des autres lecteurs PDF (navigateurs, Aperçu macOS, etc.) n'implémentent pas. Le PDF fourni s'affiche donc correctement dans n'importe quel lecteur, mais seule la première image sera visible hors Adobe.

## Outils utilisés

- **LaTeX**, packages `tikz`, `animate`, `media9`, `xcolor`, `geometry`

## Reproduire l'animation

La compilation nécessite un moteur LaTeX supportant les animations Flash/JavaScript intégrées (compilation avec `pdflatex`, à ouvrir ensuite avec Adobe Acrobat Reader) :

```bash
pdflatex voiture_qui_roule_code.tex
```

## Fichiers du projet

- `voiture_qui_roule_code.tex` — code source TikZ de l'animation
- `voiture_qui_roule_resultat.pdf` — rendu compilé (animation visible dans Adobe Acrobat Reader)
