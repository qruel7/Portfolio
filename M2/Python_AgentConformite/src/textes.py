"""Textes d'aide et commentaires des résultats affichés par l'application (Markdown).

Regroupés ici pour garder app_streamlit.py lisible. Les chiffres cités sont ceux des runs figés
dans demo/ (octobre 2026) ; les métriques calculées à l'affichage restent la référence.
"""

ACCUEIL = """
**Ce que fait le projet.** L'**Agent 1** lit un texte réglementaire entier (CAG : le document complet est
placé dans le contexte du modèle, sans moteur de recherche) et produit un référentiel d'obligations, de
contrôles et de tests. L'**Agent 2** compare ce référentiel à celui fourni par Deloitte. Le projet mesure
aussi l'**essoufflement** : un modèle à qui l'on donne un long document restitue moins bien la fin que le début.

**Parcours conseillé**
1. **Agent 1 — référentiel** : le référentiel produit sur IFRS 9 (574 lignes), chaque ligne citant le texte mot pour mot.
2. **Agent 2 — couverture** : la couverture du référentiel Deloitte, ligne par ligne, avec la gap analysis téléchargeable ; en bas, la **fiche d'une ligne** permet de vérifier comment l'agent couvre une exigence précise.
3. **Essoufflement** : le résultat principal, le rappel selon la position dans le texte, en passage unique et section par section.
4. **Expériences complémentaires** : l'effet de la longueur du document, le second texte (Sapin 2) et les contrôles de « surcouverture ».
5. **Coûts** : la maîtrise des coûts (cache de prompt, batch, journal comptable).
"""

GLOSSAIRE = """
- **Passage unique** : tout le document, une seule consigne, une seule réponse (le témoin).
- **Mode section** : le document entier reste en cache, mais chaque appel ne traite qu'une section de 4 000 à 8 000 tokens (le traitement).
- **R\\*** (pseudo-référence) : le référentiel du mode section (IFRS 9 v3 du 22/10, rattrapage compris), réduit aux lignes dont la citation est retrouvée dans le texte. Il sert de référence localisée pour mesurer le rappel section par section.
- **Rappel large / strict** : une ligne de R\\* est retrouvée au sens strict si une citation du run la chevauche, au sens large si une citation tombe dans le même paragraphe numéroté.
- **Couverture (Agent 2)** : une ligne Deloitte est couverte *totalement* si tous ses éléments sont jugés équivalents, *partiellement* si au moins un élément est couvert ; couverture stricte = totale, couverture large = totale ou partielle.
- **Qualité moyenne** : chaque élément vaut 2 points (équivalent), 1 point (principe) ou 0 (absent) ; score d'une ligne = points / (2 × éléments), puis moyenne sur les lignes.
- **Hallucination factuelle** : citation introuvable dans le texte source, ou référence incohérente. Contrôle déterministe, sans LLM.
- **J̄ (reproductibilité)** : indice de Jaccard moyen entre les répétitions d'une même configuration (1 = résultats identiques).
- **Versions du prompt** : **v3** = référence sans biais ; **v4b** = version livrée (grille de contrôle réglée après avoir vu la v3 : ses gains sont une tendance).
- **Noms de fichiers** : `section-5b820c13-v4b-…` = mode, empreinte du texte (5b820c13 = IFRS 9, ce42aa5e = Sapin 2), version du prompt, horodatage.
"""

AIDE_COUTS = """
Chaque appel à l'API est journalisé dans `logs/couts.jsonl` (ajout seul, jamais modifié) avec ses tokens
et son coût calculé aux tarifs du support de cadrage. L'**étiquette** indique l'étape (`agent1-section-extraction`,
`agent2-appariement`…). Le ratio **lectures / écritures de cache** mesure l'efficacité du cache de prompt :
chaque token du document écrit en cache a été relu plusieurs fois à un dixième du prix. Les lots **batch**
(répétitions, expériences) coûtent deux fois moins cher.
"""

AIDE_AGENT1 = """
Une ligne = une obligation imposée à l'entité. **ref** : paragraphe ou article ; **cit** : citation exacte du
texte qui fonde la ligne ; **obl** : l'obligation en une phrase ; **typ** : mesure, contrôle ou documentation ;
**crit** : criticité ; **ctrl** : contrôle clé attendu ; **test** : test de conformité ; **statut_citation** :
résultat de la vérification déterministe (*valide* = retrouvée mot pour mot). Passer la souris sur une cellule
affiche son texte complet ; cliquer sur un en-tête trie le tableau. Le menu s'ouvre sur le référentiel livré
(IFRS 9, v4b, dédoublonné) ; les fichiers `controle-*` sont des sous-ensembles construits pour les expériences.
"""

AIDE_AGENT2 = """
Chaque ligne du référentiel Deloitte est découpée en éléments (actions ou vérifications distinctes) ; le juge
note chaque élément (*équivalent*, *principe*, *absent*) en citant les lignes de l'Agent 1 qui le couvrent, et
**c'est le code qui en déduit la couverture** : 🟩 totale, 🟨 partielle, 🟥 absente, ⬜ hors périmètre (ligne
étrangère au texte, avec justification). La colonne *justification* explique chaque verdict.
**Repères** : IFRS 9 v4b : couverture large 100 % (17/17, L18 hors périmètre), stricte 0 %, qualité 36,8 % ;
Sapin 2 v4b : 96,1 % large, 13,7 % stricte, un contrôle hors périmètre. La couverture stricte est faible
par construction : les référentiels Deloitte décrivent le cadre interne d'une organisation, absent du texte.
Les runs de contrôle (placebo, sous-échantillons) sont en fin de liste : voir l'onglet *Expériences complémentaires*.
En bas de l'onglet, la **fiche d'une ligne** montre le verdict détaillé et les lignes de l'Agent 1 qui la couvrent, avec leur citation de la norme.
"""

AIDE_ESSOUFFLEMENT = """
Chaque courbe donne le rappel **r(c)** de la section *c* contre R\\*, en moyenne sur les répétitions
(bande : ± un écart-type). **unique:complet** : passage unique sur IFRS 9 entier ; **section:complet** : mode
section ; **unique:S11-S27** : passage unique sur l'annexe B seule ; **unique:S01-S10** : sur le corps du texte
seul. Les mini-documents sont placés sur les numéros de section du document complet, ce qui compare le même
contenu traité seul ou en fin de document.
"""

RETENIR_ESSOUFFLEMENT = """
**Ce qu'il faut retenir**
- **L'essoufflement est massif en passage unique.** Le rappel est proche de 100 % sur les premières sections,
  puis tombe entre 0 et 47 % sur toute la fin de la norme : 50,2 % en moyenne (k = 6), pente de −0,89 du début
  à la fin du texte (p = 2×10⁻⁷).
- **C'est la position qui en est la cause, pas la difficulté du contenu.** L'annexe B traitée seule est retrouvée
  à 72,5 %, contre 23,9 % quand elle se trouve à la fin du document complet (+48,6 points, p = 3×10⁻⁸). Le corps
  du texte, qui est en tête dans les deux cas, ne bouge pas (≈ 77 %, p = 0,82). Ce contrôle compare deux runs
  contre la même référence : il ne dépend pas de la qualité de R\\*.
- **Le mode section supprime presque l'effet** : rappel au-dessus de 87 % dans toutes les sections, pente réduite
  de 92 % (−0,072), reproductibilité J̄ de 0,72 à 0,90, et aucun token de réflexion (contre 4 000 à 31 000).

**Limites.** R\\* est construite à partir du mode section : le rappel de ce mode (≈ 95 %) est en partie mécanique,
ce sont sa pente plate et sa stabilité qui comptent. La régression par ligne traite les lignes d'une même
section comme indépendantes : son intervalle de confiance est optimiste (le test sur les k répétitions ne
dépend pas de cette hypothèse). Une annotation humaine de 2 ou 3 sections reste à faire pour valider R\\*.
"""

RETENIR_LONGUEUR = """
**Ce qu'il faut retenir**
- **Un seuil autour de 50 000 tokens.** Jusque-là, le rappel reste au-dessus de 90 % ; il chute entre 50 000 et
  100 000 tokens, puis se stabilise autour de 48 %. La droite (≈ −3,75 points par 10 000 tokens, t ≈ −13,8,
  R² ≈ 0,82 sur 45 observations) résume la tendance, mais la forme réelle est « plateau, chute, plancher ».
- **Le modèle ne lit pas moins bien la fin : il arrête de produire.** Le nombre de lignes plafonne à 200 – 300,
  quelle que soit la longueur, alors que la limite de sortie (128 000 tokens) n'est jamais atteinte. Tout ce qui
  dépasse ce « budget » de réponse est perdu, et c'est la fin du texte qui en paie le prix : la dernière section
  ajoutée est retrouvée à plus de 86 % jusqu'à ≈ 42 000 tokens, puis entre 6 et 52 % ensuite.
- **La longueur dégrade aussi un peu le début** (sections S01–S03 : ≈ −0,9 point par 10 000 tokens), quatre fois
  moins que l'ensemble du document.
- **Conséquence pratique** : au-delà de ≈ 50 000 tokens, ne pas extraire un texte en un seul appel. Le mode section
  (appels de 4 000 à 8 000 tokens à traiter, document entier en cache) reste toujours sous ce seuil.
"""

RETENIR_SAPIN = """
**Ce qu'il faut retenir.** Sur un second texte, plus court (≈ 60 000 tokens), dans une autre langue et un autre
domaine, le même mécanisme apparaît : le passage unique produit environ **deux fois moins de lignes** que le mode
section (21 contre 46, soit −54 % ; −56 % sur IFRS 9) et retrouve **87 %** de ce que retrouve le mode section
(62,3 % contre 71,7 %), exactement le rapport observé sur IFRS 9 tronqué à une longueur comparable (S01–S10,
≈ 62 000 tokens). **Limite** : R\\* de Sapin 2 ne compte que 46 lignes, concentrées sur les articles 8 à 17 ; la
pente de position y est peu interprétable, la comparaison globale des deux modes l'est.
"""

RETENIR_CONTROLES = """
**Ce qu'il faut retenir.** Question posée lors de l'audition : avec 574 lignes pour 18 lignes Deloitte, la
couverture de 100 % ne vient-elle pas du seul volume ?
- **Le juge ne récompense pas le volume en soi** : 157 lignes hors sujet (comptabilité de couverture) donnent **0 %**.
- **La couverture large croît avec le nombre de lignes pertinentes** (≈ 57 % avec 10 % des lignes, 71 % avec 25 %,
  82 % avec 50 %, 100 % avec tout le référentiel) et **varie beaucoup d'un tirage à l'autre** (de 23,5 à 82,4 % pour
  trois tirages de 57 lignes) : il faut le référentiel complet pour couvrir de façon fiable les 17 exigences.
- **La qualité progresse avec la couverture** (≈ 19 %, 20 %, 28 %, puis 37 %) : les lignes supplémentaires couvrent
  mieux, pas seulement plus. La qualité est la métrique la plus discriminante ; la couverture large est un seuil minimal.

**Limite.** Le classement « hors périmètre » du juge varie selon les lignes qu'on lui montre (de 0 à 5 lignes
selon les runs). Les couvertures ci-dessus sont donc recalculées sur un **dénominateur fixe** (17 lignes) ; une
amélioration consisterait à décider du périmètre une seule fois, sans montrer au juge les lignes de l'Agent 1.
"""

EQUIPE = "Quentin RUEL · Olivier BAUDOUIN · Sidi Abdellah MOHAMED ABDERRAHMANE"
SOUS_TITRE = ("Master 2 ESA, Université d'Orléans · projet réalisé en partenariat avec Deloitte · "
              "IFRS 9 et loi Sapin 2 · 2026")

# Chiffres clés de la synthèse : (titre, valeur, détail). Runs figés d'octobre 2026.
CHIFFRES_CLES = [
    ("Couverture large IFRS 9", "100 %", "17 lignes Deloitte sur 17 (v4b), qualité 36,8 %"),
    ("Couverture large Sapin 2", "96,1 %", "49 contrôles sur 51 (v4b), un contrôle hors périmètre"),
    ("Hallucination factuelle", "0,7 %", "citations introuvables, IFRS 9 v4b, contrôle sans LLM"),
    ("Rappel IFRS 9", "50 % → 95 %", "passage unique → mode section, contre la pseudo-référence R*"),
    ("Pente de position", "−92 %", "−0,888 → −0,072 du début à la fin du texte"),
    ("Seuil d'essoufflement", "≈ 50 k tokens", "au-delà de ≈ 50 000 tokens, le passage unique perd la fin du texte"),
    ("Reproductibilité J̄", "0,72 → 0,90", "passage unique → mode section"),
    ("Coût d'une chaîne IFRS 9", "6,51 $", "Agent 1 → export, cache et batch compris"),
]

MESSAGES_CLES = """
- **L'essoufflement existe et c'est la position qui le cause** : à contenu égal, l'annexe B d'IFRS 9 est retrouvée à
  72,5 % seule contre 23,9 % en fin de document. Au-delà d'environ 50 000 tokens, le passage unique plafonne sa sortie
  et perd la fin du texte.
- **L'architecture section par section le contourne en restant en CAG** : le document entier reste en cache, seule la
  consigne change ; le rappel passe de 50 % à 95 % et les résultats deviennent plus stables.
- **L'agent se généralise** : mêmes code et prompts sur IFRS 9 (anglais, ≈ 163 000 tokens) et Sapin 2 (français,
  ≈ 60 000 tokens) ; il couvre 96 à 100 % des référentiels Deloitte au sens large, avec moins de 2,5 % d'hallucination.
"""

AIDE_VERSIONS = """
Moyennes des runs de l'Agent 2 par texte et par version du prompt de l'Agent 1 (runs de contrôle et expérience de
la grille exclus). **v3** est la référence sans biais ; **v4a** ajoute deux règles d'extraction (obligations de
l'entité seule, subdivision la plus fine) ; **v4** et **v4b** ajoutent une grille de contrôle, dans les consignes (v4)
ou dans la seule étape d'enrichissement (v4b, version livrée). La grille a été conçue après avoir vu les résultats
de la v3 : ses gains sont une tendance, pas une preuve (p = 0,075 à extraction figée).
"""

ARCHITECTURE_DOT = """
digraph {
  bgcolor="transparent"; rankdir=LR;
  node [shape=box, style="rounded,filled", fillcolor="#DCE7F7", color="#5B9BF3", fontname="Helvetica", fontcolor="#0F1724", fontsize=16];
  edge [color="#8FA3BF"];
  debut [label="PDF\\n(empreinte SHA-256)", fillcolor="#E6EAF0", color="#8FA3BF"];
  decoupage [label="Découpage\\n(règle)", fillcolor="#E6EAF0", color="#8FA3BF"];
  agent1 [label="Agent 1\\nextraction + enrichissement\\n(LLM, document en cache)"];
  rattrapage [label="Vérification des citations\\n+ rattrapage (règle + LLM)"];
  dedoublonnage [label="Dédoublonnage\\n(LLM + règle)"];
  agent2 [label="Agent 2\\ncouverture (LLM + règle)"];
  export [label="Export au format\\ndu référentiel (règle)", fillcolor="#E6EAF0", color="#8FA3BF"];
  debut -> decoupage -> agent1 -> rattrapage -> dedoublonnage -> agent2 -> export;
}
"""

REPRODUIRE = """
Cette application relit des runs **déjà effectués** (dossier `demo/`) : les clés API ont été révoquées le 31/10/2026
et aucune clé ne figure dans le dépôt. Pour tout reproduire à partir du code :

```bash
make setup      # environnement virtuel + dépendances (versions figées de requirements.txt)
make test       # tests unitaires, aucun appel API
make run        # cette application, en mode démonstration
```

Avec une clé API dans un fichier `.env` (modèle : `.env.example`) et les textes dans `data/corpus/`, `make run-local`
ouvre l'application en mode complet : l'onglet **Pilotage** y lance la chaîne (simulation gratuite d'abord, budget
vérifié avant le premier appel). En ligne de commande :

```bash
python scripts/lancer_pipeline.py data/corpus/<texte>.pdf --nom "<intitulé>" \\
    --referentiel data/referentiels/<referentiel>.xlsx --version v4b --simulation
# puis la même commande avec --confirmer à la place de --simulation
python scripts/preparer_demo.py   # reconstruit demo/ à partir de resultats/
```
"""
