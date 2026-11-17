"""Couverture des paragraphes par un run : diagnostic DÉTERMINISTE, sans référentiel.

Repère les paragraphes numérotés qui n'ont reçu aucune ligne, et compte leurs
tournures prescriptives. Sert au diagnostic (scripts/couverture_paragraphes.py)
et à la passe de rattrapage (scripts/rattraper.py) : la règle décide quels
paragraphes revoir, le LLM extrait.
"""

import re

from src.decoupage import reperes

PRESCRIPTIF = re.compile(
    r"\b(shall|must|required|requires|should|doit|doivent|est tenue?s? de|sont tenue?s de|veillent? à"
    # rédaction juridique française : le présent de l'indicatif vaut obligation
    r"|met en œuvre|mettent en œuvre|s'assurent? que|est interdite?|sont interdite?s|ne peut|ne peuvent)\b", re.I)
FACULTATIF = re.compile(r"\b(may|is permitted|can elect|peut|peuvent)\b", re.I)
# Tournures qui contiennent un mot prescriptif sans rien imposer : renvois et négations.
_NEUTRES = re.compile(
    r"\b(paragraphs?|articles?|appendix|annexe?)\s+[A-Z]{0,3}\d[\w.()–-]*(\s*(and|or|et|ou|–|-)\s*[A-Z]{0,3}\d[\w.()–-]*)*\s+(requires?|required)\b"
    r"|\b(not|no longer|n'est pas|ne sont pas)\s+(required|tenue?s?)\b", re.I)
_BASE = re.compile(r"^[A-Za-z]*\d+(?:\.\d+)*[A-Z]?", re.I)
# « art. 17, II, 3° », « Article 17-II », « article 17 II » → numéro d'article + subdivision romaine
_BASE_ARTICLE = re.compile(r"^art(?:icle|\.)?\s*((?:[LRD]\.?\s*)?\d+(?:-\d+)?)(?:[\s,.;–-]+([IVXL]{1,6})\b)?", re.I)


def base_ref(ref: str) -> str:
    """« 5.5.17(a) » → « 5.5.17 » ; « art. 17, II, 3° » → « Article 17 II » ; « art. 6 » → « Article 6 »."""
    r = ref.strip()
    if m := _BASE_ARTICLE.match(r):
        return "Article " + m.group(1) + (" " + m.group(2).upper() if m.group(2) else "")
    m = _BASE.match(r)
    return m.group(0) if m else r


def compter_prescriptif(corps: str) -> int:
    return len(PRESCRIPTIF.findall(_NEUTRES.sub(" ", corps)))


def paragraphes_omis(texte: str, sections: list, lignes_par_tache: dict) -> list[dict]:
    """Paragraphes sans ligne, pour les sections présentes dans lignes_par_tache.

    Un repère « parent » d'un autre (« 5.4 » avant « 5.4.1 », « Article 17 » avant
    « Article 17 II ») est un titre : ignoré.
    """
    tous = reperes(texte)
    labels = [l for _, l in tous]
    titres = {l for l in labels if any(m.startswith(l + ".") or m.startswith(l + " ") for m in labels)}
    resultat = []
    for s in sections:
        if s.id not in lignes_par_tache:
            continue
        vus = {base_ref(l["ref"]) for l in lignes_par_tache[s.id]}
        # Le paragraphe où la citation a été TROUVÉE compte aussi : une référence trop
        # large (« Article 17 » pour une citation du 17 II) ne doit pas faire croire à un oubli.
        vus |= {l["_verif"]["paragraphe"] for l in lignes_par_tache[s.id]
                if (l.get("_verif") or {}).get("paragraphe")}
        paras = [(pos, l) for pos, l in tous if s.debut <= pos < s.fin and l not in titres]
        for k, (pos, l) in enumerate(paras):
            fin = paras[k + 1][0] if k + 1 < len(paras) else s.fin
            if l in vus:
                continue
            corps = texte[pos:fin]
            resultat.append({"section": s.id, "paragraphe": l, "debut": pos, "fin": fin,
                             "prescriptif": compter_prescriptif(corps),
                             "facultatif": len(FACULTATIF.findall(corps)),
                             "nb_paragraphes_section": len(paras)})
    return resultat
