"""Extraction et nettoyage GÉNÉRIQUES du texte d'un document réglementaire.

Aucune règle propre à un texte :
- l'ordre de lecture suit la position sur la page (les numéros de paragraphe
  placés en marge se retrouvent ainsi devant leur paragraphe) ;
- les en-têtes et pieds de page sont détectés statistiquement : une ligne
  (chiffres neutralisés) située en haut ou en bas de page et qui revient sur
  la plupart des pages est du bruit. Une ligne au milieu de la page n'est
  jamais retirée (sinon « Article 12 », « Article 13 »… disparaîtraient).

Le texte nettoyé est LE texte de référence du projet : c'est lui que lit le
modèle, et c'est dans lui qu'on vérifie les citations.
"""

import hashlib
import re
from collections import Counter
from pathlib import Path

_ESPACES = re.compile(r"[ \t ]+")
_CHIFFRES = re.compile(r"\d+")


def _normaliser_ligne(ligne: str) -> str:
    return _ESPACES.sub(" ", ligne).strip()


def extraire_pages(chemin: Path) -> list[str]:
    """Une chaîne par page. PDF : lecture triée par position. TXT/MD : une seule « page »."""
    chemin = Path(chemin)
    if chemin.suffix.lower() == ".pdf":
        import pymupdf

        with pymupdf.open(chemin) as doc:
            brutes = [page.get_text(sort=True) for page in doc]
    else:
        brutes = [chemin.read_text(encoding="utf-8")]
    return ["\n".join(_normaliser_ligne(l) for l in p.splitlines()) for p in brutes]


MARGE_LIGNES = 3  # un en-tête ou pied de page est dans les 3 premières ou dernières lignes


def _lignes_de_marge(page: str) -> list[str]:
    lignes = [l for l in page.splitlines() if l]
    if len(lignes) <= 2 * MARGE_LIGNES:
        return lignes
    return lignes[:MARGE_LIGNES] + lignes[-MARGE_LIGNES:]


def lignes_repetees(pages: list[str], seuil: float = 0.5) -> set[str]:
    """Formes de lignes (chiffres remplacés par #) présentes sur au moins `seuil` des pages.

    « A395 » et « A396 » ont la même forme « A# » : le numéro de page est attrapé
    même s'il change à chaque page. Inactif sous 4 pages (pas de statistique fiable).
    """
    if len(pages) < 4:
        return set()
    bruit = set()
    # Les documents imprimés en vis-à-vis alternent la mise en page des pages
    # paires et impaires : on compte aussi sur chaque parité séparément.
    for groupe in (pages, pages[0::2], pages[1::2]):
        compte = Counter()
        for p in groupe:
            compte.update({_CHIFFRES.sub("#", l) for l in _lignes_de_marge(p)})
        bruit |= {f for f, n in compte.items() if n / len(groupe) >= seuil}
    return bruit


def nettoyer(pages: list[str], seuil: float = 0.5) -> tuple[str, dict]:
    """Renvoie (texte nettoyé, rapport). Le rapport dit ce qui a été retiré, pour contrôle humain."""
    bruit = lignes_repetees(pages, seuil)
    gardees, retirees = [], Counter()
    for p in pages:
        lignes = [l for l in p.splitlines() if l]
        n = len(lignes)
        for k, l in enumerate(lignes):
            en_marge = k < MARGE_LIGNES or k >= n - MARGE_LIGNES
            forme = _CHIFFRES.sub("#", l)
            if en_marge and forme in bruit:
                retirees[forme] += 1
            else:
                gardees.append(l)
    texte = "\n".join(gardees) + "\n"
    rapport = {
        "nb_pages": len(pages),
        "formes_retirees": dict(retirees.most_common()),
        "nb_lignes_retirees": sum(retirees.values()),
        "nb_lignes_gardees": len(gardees),
        "nb_caracteres": len(texte),
    }
    return texte, rapport


def empreinte(texte: str) -> str:
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


def charger_document(chemin: Path, seuil: float = 0.5) -> dict:
    """Point d'entrée : {texte, sha256_texte, rapport}."""
    texte, rapport = nettoyer(extraire_pages(chemin), seuil)
    return {"texte": texte, "sha256_texte": empreinte(texte), "rapport": rapport}
