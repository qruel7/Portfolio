"""Export DÉTERMINISTE (sans LLM) du référentiel pivot au format d'un référentiel de référence.

Lecture retenue de la consigne Deloitte « le référentiel servira d'exemple de format attendu
en sortie » (décision 4.1, à faire confirmer) : l'Agent 1 produit toujours le pivot ; ce
module le recopie dans les COLONNES du fichier de référence. Seule la ligne d'en-tête du
fichier de référence est lue : aucune de ses lignes de contenu n'est utilisée.

Chaque en-tête est reconnu par mots-clés (accents, casse et coquilles courantes tolérés) et
relié à un ou plusieurs champs du pivot. Un en-tête non reconnu reste vide et est signalé.
Deux colonnes de traçabilité sont ajoutées à droite (référence et citation exacte du texte),
sauf si le format les contient déjà.
"""

import re
import unicodedata
from pathlib import Path

from src.referentiels import charger_referentiel

ECHELLES = {
    "en": {"critique": "Critical", "majeure": "Major", "significative": "Significant", "mineure": None},
    "fr": {"critique": "Critique", "majeure": "Majeure", "significative": "Significative", "mineure": "Mineure"},
}


def _sans_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"\s+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip().lower()


def _langue_entete(colonnes: list[str]) -> str:
    texte = " ".join(_sans_accents(c) for c in colonnes)
    return "en" if re.search(r"\b(finding|recommendation|criticality|control)\b", texte) else "fr"


def role_colonne(entete: str) -> str | None:
    """Rôle d'un en-tête : id, dom, finding, recommandation, ctrl, test, crit, ref, cit, obl."""
    e = _sans_accents(entete)
    regles = [
        ("id", r"(^|_|\b)id\b|identifiant"),
        ("crit", r"critic|criticit|severit|gravit"),
        ("test", r"\btest"),
        ("ctrl", r"controle cle|key control|\bcontrole\b|\bcontrol\b"),
        ("recommandation", r"recommend|recommand"),
        ("finding", r"finding|constat"),
        ("obl", r"obligation|exigence|requirement"),
        ("ref", r"reference|\bref\b|article|paragraphe"),
        ("cit", r"citation|extrait|quote"),
        ("dom", r"classi|domaine|domain|theme|categorie|category|pilier"),
    ]
    for role, motif in regles:
        if re.search(motif, e):
            return role
    return None


def valeur(ligne: dict, role: str, langue: str, anomalies: list) -> str:
    if role == "id":
        return ligne.get("id", "")
    if role == "dom":
        return ligne.get("dom", "")
    if role == "obl":
        return ligne.get("obl", "")
    if role == "finding":  # l'obligation, ancrée dans le texte
        return f"{ligne.get('obl', '')}\n« {ligne.get('cit', '')} » ({ligne.get('ref', '')})"
    if role == "recommandation":
        return "\n".join(x for x in (ligne.get("ctrl"), ligne.get("test")) if x)
    if role == "ctrl":
        return ligne.get("ctrl", "")
    if role == "test":
        return ligne.get("test", "")
    if role == "ref":
        return ligne.get("ref", "")
    if role == "cit":
        return ligne.get("cit", "")
    if role == "crit":
        crit = ligne.get("crit", "")
        lib = ECHELLES[langue].get(crit)
        if lib is None:
            anomalies.append({"id": ligne.get("id"), "raison": f"criticité « {crit} » sans équivalent dans l'échelle "
                                                                 f"du format ({', '.join(v for v in ECHELLES[langue].values() if v)})"})
            return f"({crit})"
        return lib
    return ""


def exporter(lignes: list[dict], chemin_format: Path, sortie: Path, feuille=0) -> dict:
    """Écrit `sortie` (.xlsx) avec les colonnes du fichier de référence. Renvoie un rapport."""
    import openpyxl
    from openpyxl.styles import Alignment, Font

    fmt = charger_referentiel(chemin_format, feuille)  # seules les colonnes sont utilisées
    colonnes = fmt["colonnes"]
    roles = {c: role_colonne(c) for c in colonnes}
    langue = _langue_entete(colonnes)
    ajoutees = [c for c, r in (("Référence (texte)" if langue == "fr" else "Reference (text)", "ref"),
                               ("Citation exacte" if langue == "fr" else "Exact quote", "cit"))
                if r not in roles.values() and not (r == "cit" and "finding" in roles.values())]
    roles_ajoutes = {c: ("ref" if "fér" in c or "Ref" in c else "cit") for c in ajoutees}
    anomalies = [{"colonne": c, "raison": "en-tête non reconnu : colonne laissée vide"} for c, r in roles.items() if r is None]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = (fmt["feuille"] or "Référentiel")[:31]
    ws.append(colonnes + ajoutees)
    for c in ws[1]:
        c.font = Font(bold=True)
    for l in lignes:
        ws.append([valeur(l, roles[c], langue, anomalies) if roles[c] else "" for c in colonnes]
                  + [valeur(l, roles_ajoutes[c], langue, anomalies) for c in ajoutees])
    for k, _ in enumerate(colonnes + ajoutees):
        ws.column_dimensions[openpyxl.utils.get_column_letter(k + 1)].width = 18 if k == 0 else 55
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    wb.save(sortie)
    return {"fichier": str(sortie), "format": fmt["fichier"], "colonnes": colonnes, "roles": roles,
            "colonnes_ajoutees": ajoutees, "langue_echelle": langue, "nb_lignes": len(lignes), "anomalies": anomalies}
