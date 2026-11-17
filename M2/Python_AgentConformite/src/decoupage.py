"""Découpage GÉNÉRIQUE d'un document en sections, sans structure codée en dur.

Principe en trois temps :
1. repérer les débuts d'unités grâce à la numérotation (paragraphes « 4.3.1 »,
   « B5.5.17 », articles « Article 17 », romains « II. – ») et aux titres
   occupant toute une ligne (« Appendix A », « Annexe II », « Titre III ») ;
2. regrouper les unités par parent (« 4.3.1 » → « 4.3 ») en blocs consécutifs ;
3. fusionner les blocs trop petits et scinder les trop gros pour obtenir des
   sections de taille bornée en tokens.
Repli : si la numérotation est trop pauvre, fenêtres de taille fixe.

Chaque section garde ses positions (début, fin) dans le texte nettoyé : c'est
ce qui permet ensuite de situer une citation dans le document (essoufflement).
"""

import re
from collections import Counter
from dataclasses import asdict, dataclass

# Caractères par token mesurés sur IFRS 9 (texte brut) : 509 429 / 167 807 = 3,04
# pour Sonnet/Opus 5 et 5.5. Estimation seulement : count_tokens fait foi.
CARACTERES_PAR_TOKEN = 3.04

# « 4.3.1 », « B5.5.17 », « 5.5.20A », « BC4.12 » suivis d'un espace.
# Au moins un point : on exclut ainsi les années et les nombres isolés.
_NUMERO = re.compile(r"^([A-Z]{0,3}\d+(?:\.\d+){1,4}[A-Z]?)\s+\S")
# « Article 17 », « Art. L. 225-102-4 », « Article premier »
_ARTICLE = re.compile(r"^(Article|Art\.)\s+((?:[LRD]\.?\s*)?[\w-]+)", re.IGNORECASE)
# « I. – », « II.- » en début de ligne (structure des lois françaises). Le tiret est
# OBLIGATOIRE : sans lui, « L. 225-57 du code de commerce » (article de code coupé en début
# de ligne) serait lu comme le romain L.
_ROMAIN = re.compile(r"^([IVXL]{1,6})\.\s*[-–—]\s*[^\s\d]")
# Titre de niveau supérieur occupant toute la ligne : mot-clé avec majuscule,
# identifiant en majuscules ou chiffres, suivi au plus d'un intitulé qui commence
# par une majuscule et ne contient pas de ponctuation de phrase.
_MOTS_TITRE = (
    "Chapter|Chapitre|Part|Partie|Title|Titre|Book|Livre|Section|Appendix|Annex|Annexe"
)
_TITRE = re.compile(
    rf"^((?:{_MOTS_TITRE})|(?:{_MOTS_TITRE.upper()}))\s+([A-Z0-9]{{1,6}})"
    r"(?:\s*[-–—:]?\s*([A-ZÀ-Ý][^.,;)]{0,70}))?$"
)


@dataclass
class Section:
    id: str
    titre: str
    debut: int  # position (caractère) dans le texte nettoyé, incluse
    fin: int  # exclue
    tokens_estimes: int
    cles: list

    def texte(self, document: str) -> str:
        return document[self.debut : self.fin]


def _tokens(nb_caracteres: int) -> int:
    return round(nb_caracteres / CARACTERES_PAR_TOKEN)


_ROMAINS = {"I": 1, "V": 5, "X": 10, "L": 50}


def _entier(s: str) -> int:
    """« 17 » → 17 ; « premier » → 1 ; romain « IV » → 4 ; sinon 0."""
    if s.isdigit():
        return int(s)
    if s.lower() in ("premier", "first", "1er"):
        return 1
    if s and all(c in _ROMAINS for c in s.upper()):
        total = 0
        for a, b in zip(s.upper(), s.upper()[1:] + " "):
            v = _ROMAINS[a]
            total += -v if b in _ROMAINS and _ROMAINS[b] > v else v
        return total
    if len(s) == 1 and s.isalpha():
        return ord(s.upper()) - 64  # Appendix A → 1, B → 2
    return 0


def _ordre_numero(numero: str) -> tuple:
    """« B5.5.17 » → ("B", 5, 5, 17, "") ; l'ordre des tuples suit l'ordre du document."""
    m = re.match(r"^([A-Z]*)([\d.]+?)([A-Z]?)$", numero)
    prefixe, chiffres, suffixe = m.groups()
    nombres = [int(x) for x in chiffres.split(".")]
    nombres += [-1] * (6 - len(nombres))  # « 4.3 » passe avant « 4.3.1 »
    return (prefixe, *nombres, ord(suffixe) if suffixe else 0)


def _plus_longue_croissante(ordres: list[tuple]) -> set[int]:
    """Indices de la plus longue sous-suite strictement croissante (O(n log n))."""
    from bisect import bisect_left

    queues, idx_queues, parent = [], [], [None] * len(ordres)
    for i, o in enumerate(ordres):
        j = bisect_left(queues, o)
        if j == len(queues):
            queues.append(o)
            idx_queues.append(i)
        else:
            queues[j] = o
            idx_queues[j] = i
        parent[i] = idx_queues[j - 1] if j else None
    garde, i = set(), idx_queues[-1] if idx_queues else None
    while i is not None:
        garde.add(i)
        i = parent[i]
    return garde


def _candidats(lignes: list[str], complet: bool = False) -> list[tuple[int, str]]:
    """(indice de ligne, clé) des débuts d'unités retenus après contrôle de cohérence.

    complet=True : numéro entier (« 4.3.1 ») au lieu de la clé de regroupement (« 4.3 »).
    """
    numeros, articles, titres, romains = [], [], {}, []
    for i, brute in enumerate(lignes):
        l = brute.strip()
        if (m := _TITRE.match(l)) and len(l) <= 90:
            mot = m.group(1).capitalize()
            # on garde la DERNIÈRE occurrence d'un titre (le sommaire vient avant le corps)
            titres[(mot, m.group(2))] = i
        elif m := _NUMERO.match(l):
            numeros.append((i, m.group(1)))
        elif m := _ARTICLE.match(l):
            articles.append((i, m.group(2)))
        elif m := _ROMAIN.match(l):
            romains.append((i, m.group(1)))

    retenus = []
    # paragraphes numérotés : la vraie numérotation est la plus longue chaîne croissante
    garde = _plus_longue_croissante([_ordre_numero(n) for _, n in numeros])
    numeros = [x for k, x in enumerate(numeros) if k in garde]
    # regroupement à la profondeur dominante moins un : si la plupart des numéros
    # ont 3 niveaux (« 4.3.1 »), « 4.3 » et « 4.3.1 » partagent la clé « 4.3 »
    if numeros:
        profondeurs = Counter(n.count(".") + 1 for _, n in numeros)
        k = max(1, profondeurs.most_common(1)[0][0] - 1)
        if complet:
            retenus += numeros
        else:
            retenus += [(i, ".".join(n.split(".")[:k])) for i, n in numeros]
    # articles : même principe, sur leur numéro
    garde = _plus_longue_croissante([(_entier(re.sub(r"\D", "", a) or a),) for _, a in articles])
    retenus += [(i, f"Article {a}") for k, (i, a) in enumerate(articles) if k in garde]
    # titres : par famille de mot-clé, ordre croissant de l'identifiant
    par_mot = {}
    for (mot, ident), i in titres.items():
        par_mot.setdefault(mot, []).append((i, ident))
    for mot, occ in par_mot.items():
        occ.sort()
        garde = _plus_longue_croissante([(_entier(ident),) for _, ident in occ])
        retenus += [(i, f"{mot} {ident}") for k, (i, ident) in enumerate(occ) if k in garde]
    # romains : ils repartent à I dans chaque article ; rattachés à l'article courant
    articles_retenus = sorted((i, c) for i, c in retenus if c.startswith("Article "))
    for i, r in romains:
        parents = [c for j, c in articles_retenus if j < i]
        retenus.append((i, f"{parents[-1]} {r}" if parents else r))
    return sorted(retenus)


def reperes(texte: str) -> list[tuple[int, str]]:
    """(position dans le texte, numéro complet) de chaque unité retenue, dans l'ordre.

    Sert à retrouver le paragraphe qui contient une position donnée (citations).
    """
    lignes = texte.splitlines(keepends=True)
    positions, pos = [], 0
    for l in lignes:
        positions.append(pos)
        pos += len(l)
    return [(positions[i], label) for i, label in _candidats(lignes, complet=True)]


def _blocs(texte: str) -> tuple[list[dict], list[int]]:
    """Blocs consécutifs de même clé, et positions de tous les débuts d'unités."""
    lignes = texte.splitlines(keepends=True)
    positions, pos = [], 0
    for l in lignes:
        positions.append(pos)
        pos += len(l)
    blocs, courant = [], {"cle": "(début)", "debut": 0}
    candidats = _candidats(lignes)
    coupures = [positions[i] for i, _ in candidats]
    for i, cle in candidats:
        if cle == courant["cle"]:
            continue
        if positions[i] > courant["debut"]:
            blocs.append({**courant, "fin": positions[i]})
            courant = {"cle": cle, "debut": positions[i]}
        else:
            courant["cle"] = cle
    blocs.append({**courant, "fin": pos})
    return blocs, coupures


def _scinder(
    debut: int, fin: int, texte: str, max_tokens: int, coupures: list[int] = ()
) -> list[tuple[int, int]]:
    """Scinde [debut, fin) en morceaux ≤ max_tokens.

    On coupe de préférence au début d'une unité numérotée (`coupures`), au plus
    loin possible dans la fenêtre ; à défaut, à une fin de ligne.
    """
    from bisect import bisect_right

    morceaux, d = [], debut
    max_car = int(max_tokens * CARACTERES_PAR_TOKEN)
    while fin - d > max_car:
        j = bisect_right(coupures, d + max_car) - 1
        if j >= 0 and coupures[j] > d + max_car // 3:
            coupe = coupures[j]
        else:
            coupe = texte.rfind("\n", d, d + max_car)
            coupe = coupe + 1 if coupe > d else d + max_car
        morceaux.append((d, coupe))
        d = coupe
    morceaux.append((d, fin))
    return morceaux


def _absorber_petites(groupes: list, seuil: float, max_tokens: int) -> list:
    """Rattache chaque section sous `seuil` tokens à sa voisine la plus petite,
    tant que le résultat reste ≤ max_tokens."""
    taille = lambda g: _tokens(g[0][1] - g[0][0])
    change = True
    while change and len(groupes) > 1:
        change = False
        for i, g in enumerate(groupes):
            if taille(g) >= seuil:
                continue
            voisins = [j for j in (i - 1, i + 1) if 0 <= j < len(groupes)]
            voisins = [j for j in voisins if taille(g) + taille(groupes[j]) <= max_tokens]
            if not voisins:
                continue
            j = min(voisins, key=lambda j: taille(groupes[j]))
            a, b = sorted((i, j))
            (d, _), ca = groupes[a]
            (_, f), cb = groupes[b]
            groupes[a : b + 1] = [((d, f), ca + [c for c in cb if c not in ca])]
            change = True
            break
    return groupes


def decouper(
    texte: str,
    min_tokens: int = 4_000,
    max_tokens: int = 12_000,
    min_unites: int = 5,
) -> list[Section]:
    """Découpe le texte en sections couvrant TOUT le texte, sans recouvrement."""
    blocs, coupures = _blocs(texte)
    structure = len(blocs) >= min_unites

    if not structure:  # repli : fenêtres fixes
        groupes = [((d, f), ["(fenêtre)"]) for d, f in _scinder(0, len(texte), texte, max_tokens)]
    else:
        groupes, en_cours = [], None
        for b in blocs:
            for d, f in _scinder(b["debut"], b["fin"], texte, max_tokens, coupures):
                if en_cours is None:
                    en_cours = [d, f, [b["cle"]]]
                    continue
                taille = _tokens(en_cours[1] - en_cours[0])
                ajout = _tokens(f - d)
                tient = taille + ajout <= max_tokens
                if tient and (taille < min_tokens or taille + ajout <= max_tokens * 0.75):
                    en_cours[1] = f
                    if b["cle"] not in en_cours[2]:
                        en_cours[2].append(b["cle"])
                else:
                    groupes.append(((en_cours[0], en_cours[1]), en_cours[2]))
                    en_cours = [d, f, [b["cle"]]]
        groupes.append(((en_cours[0], en_cours[1]), en_cours[2]))
        groupes = _absorber_petites(groupes, min_tokens / 2, max_tokens)

    sections = []
    for i, ((d, f), cles) in enumerate(groupes, 1):
        titre = cles[0] if len(cles) == 1 else f"{cles[0]} → {cles[-1]}"
        sections.append(Section(f"S{i:02d}", titre, d, f, _tokens(f - d), cles))
    return sections


def section_de_position(sections: list[Section], position: int) -> Section | None:
    """Section qui contient la position donnée (ex. position d'une citation retrouvée)."""
    for s in sections:
        if s.debut <= position < s.fin:
            return s
    return None


def resume(sections: list[Section]) -> list[dict]:
    return [{k: v for k, v in asdict(s).items() if k != "cles"} | {"nb_cles": len(s.cles)} for s in sections]
