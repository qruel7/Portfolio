# Règle d'appariement — version 1 (24/10/2026)

Cette règle dit **quand une ligne du référentiel produit par l'IA (Agent 1) couvre une ligne
du référentiel de référence** (Deloitte). Toutes les métriques de l'Agent 2 en dépendent.
Elle est appliquée par un juge LLM (prompt `src/prompts/agent2_systeme_v1.txt`), mais les
**chiffres sont calculés par le code** à partir des verdicts élément par élément.

Rédigée par l'assistant faute de version du groupe ; **à relire et amender par le groupe**.
Toute modification impose un nouveau numéro de version (v2…) et une relance de l'Agent 2.

## 1. Ce qu'on compare

- **Ligne de référence** : une ligne du fichier Deloitte, avec toutes ses colonnes (par ex.
  constat + recommandation + criticité, ou contrôle clé + test de conformité).
- **Ligne IA** : une ligne du référentiel de l'Agent 1 (référence, obligation, contrôle, test).

Les deux référentiels ne sont pas au même niveau. Une ligne de référence peut être très
spécifique (un défaut précis dans le cadre interne d'une entité) quand la ligne IA énonce
l'exigence générale tirée du texte. **Plusieurs lignes IA peuvent couvrir ensemble une ligne
de référence, et une même ligne IA peut contribuer à plusieurs lignes de référence.**

## 2. Décomposer la ligne de référence en éléments

Une ligne de référence contient souvent plusieurs demandes distinctes (A-1, A-2, B…, ou un
contrôle et ses modalités). Le juge la découpe en **éléments** : un élément = une action ou
une vérification distincte attendue de l'entité. Le constat (« finding ») sert de contexte :
on évalue ce qui est **demandé**, pas la description du défaut.

## 3. Le critère, élément par élément

> **Un auditeur qui appliquerait le contrôle et le test de la ligne IA aurait-il été conduit
> à examiner ce point précis, et donc à pouvoir formuler ce constat ou exiger cette action ?**

Trois niveaux :

| Niveau | Score | Définition |
|---|---|---|
| `equivalent` | 2 | La ligne IA demande la même action ou la même vérification, avec une précision égale ou supérieure. L'auditeur aurait nécessairement examiné ce point. |
| `principe` | 1 | La ligne IA énonce l'exigence dont l'élément découle, ou un contrôle sur le même objet, mais pas l'action spécifique. L'auditeur aurait regardé le sujet, sans être sûr de tomber sur ce point. |
| `absent` | 0 | Aucune ligne IA ne conduit à examiner ce point. |

Règles de prudence :
- une ligne **trop générale** (« documenter la méthodologie », « faire valider le modèle »)
  ne vaut `principe` que si l'élément porte sur ce même objet ; elle ne vaut jamais `equivalent`
  pour un élément technique précis ;
- le **thème commun ne suffit pas** : deux lignes sur « la dépréciation » ne s'apparient pas
  si l'une porte sur les données et l'autre sur la gouvernance ;
- on juge le **fond**, pas les mots : aucune correspondance de vocabulaire n'est exigée
  (les référents l'ont rappelé : le référentiel de référence est une interprétation de la norme) ;
- chaque niveau `equivalent` ou `principe` cite **les identifiants des lignes IA** qui le
  justifient ; un identifiant inexistant est supprimé par le code et compté.

## 4. De l'élément à la ligne (calcul fait par le code, pas par le juge)

| Couverture de la ligne | Condition |
|---|---|
| `totale` | tous ses éléments sont `equivalent` |
| `partielle` | au moins un élément `equivalent` ou `principe`, sans que tous soient `equivalent` |
| `absente` | tous ses éléments sont `absent` |

**Score de qualité** de la ligne = moyenne des scores de ses éléments / 2 (entre 0 et 1).

## 5. Hors périmètre

Une ligne de référence est **hors périmètre** si elle porte sur une réglementation ou un sujet
**étranger au texte analysé** (par exemple une ligne portant sur une autre réglementation). Elle est signalée avec une justification et **exclue du dénominateur**.

Attention : une ligne très spécifique au cadre interne d'une entité (formule, segmentation,
méthode de calcul propre) n'est **pas** hors périmètre si son sujet relève du texte. Elle est
évaluée normalement, et vaudra le plus souvent `principe` : c'est un résultat à documenter
(l'écart entre ce que dit le texte et ce qu'exige un référentiel opérationnel), pas une exclusion.

## 6. Métriques produites

- **Couverture stricte** = nb `totale` / nb lignes évaluées (hors périmètre exclu).
- **Couverture large** = nb (`totale` + `partielle`) / nb lignes évaluées.
- **Qualité moyenne** = moyenne des scores de qualité des lignes évaluées.
- Rapporter les deux couvertures, comme l'analyse de sensibilité au seuil de LongDA.

## 7. Lignes IA supplémentaires

Les lignes IA citées par aucun élément sont jugées une à une :

| Verdict | Définition |
|---|---|
| `pertinente` | exigence réelle du texte pour l'entité, contrôle et test actionnables |
| `faible` | exacte mais de faible valeur (descriptive, triviale, redondante avec une autre ligne) |
| `non_pertinente` | n'impose rien à l'entité, hors sujet ou erronée |

## 8. Exemples (INVENTÉS, sans rapport avec les référentiels du projet)

Ligne de référence fictive : *« Constat : la procédure de conservation des registres ne précise
pas qui contrôle leur complétude. Recommandation : A) désigner un responsable du contrôle
mensuel ; B) conserver les preuves du contrôle cinq ans. »*

- Éléments : (A) responsable désigné du contrôle mensuel ; (B) preuves conservées cinq ans.
- Ligne IA « Archivage quotidien, contrôle mensuel de complétude par le responsable qualité,
  conservation cinq ans » → A `equivalent`, B `equivalent` → **totale**.
- Ligne IA « Conserver les registres cinq ans » seule → A `absent`, B `principe` (porte sur la
  conservation, pas sur les preuves du contrôle) → **partielle**, qualité (0 + 1) / 2 / 2 = 0,25.
- Ligne IA « Former le personnel à l'hygiène » → thème voisin, objet différent → A et B
  `absent` → **absente**.
