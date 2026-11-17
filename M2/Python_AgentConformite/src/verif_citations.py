"""Vérification DÉTERMINISTE des citations : la règle décide, le LLM extrait.

Pour chaque ligne produite par l'Agent 1, on vérifie dans le texte nettoyé :
1. que la citation `cit` existe, mot pour mot, après normalisation
   (casse, espaces, guillemets, tirets, coupures de mots en fin de ligne) ;
   une citation peut contenir des ellipses (« … » ou « ... ») : chaque morceau
   doit alors être retrouvé, dans l'ordre ;
2. que la référence `ref` correspond au paragraphe où se trouve la citation.

Aucun appel à un modèle. Le statut est l'un de :
  valide | ref_incoherente | introuvable | trop_courte
"""

import re
import unicodedata
from bisect import bisect_right

from src.decoupage import _ordre_numero, reperes

MOTS_MIN = 5  # une citation plus courte ne prouve rien (« the entity shall »)

_REMPLACEMENTS = {
    "‘": "'", "’": "'", "‚": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
    "–": "-", "—": "-", "‑": "-", "−": "-",
    " ": " ", " ": " ",
}
_ELLIPSE = re.compile(r"\s*(?:…|\.\.\.|\[\s*(?:…|\.\.\.)\s*\])\s*")
_NUM_REF = re.compile(r"[A-Z]{0,3}\d+(?:\.\d+)*[A-Z]?")


def normaliser(texte: str) -> tuple[str, list[int]]:
    """Texte normalisé + table « indice normalisé → indice d'origine ».

    Casse ignorée ; guillemets, apostrophes et tirets unifiés ; espaces multiples
    réduits à un seul ; pas d'espace contre un guillemet (« non » = "non") ;
    un tiret collé à une lettre puis suivi d'un blanc se recolle (« non-\\nfinancial »).
    """
    sortie, origine = [], []
    attente = None  # (indice du premier blanc, contient un saut de ligne)
    for i, c in enumerate(texte):
        c = unicodedata.normalize("NFKC", _REMPLACEMENTS.get(c, c)).lower()
        if c.isspace():
            if sortie:
                attente = (attente[0] if attente else i, (attente[1] if attente else False) or c == "\n")
            continue
        if attente is not None:
            debut_blanc, saut = attente
            # « credit-\\nadjusted » ou « credit- adjusted » : tiret collé à une lettre
            # puis blanc = coupure de mot. « risque - élevé » (espace avant) reste intact.
            coupure_de_mot = sortie[-1] == "-" and len(sortie) > 1 and sortie[-2].isalnum()
            contre_guillemet = sortie[-1] == '"' or c == '"'
            if not (coupure_de_mot or contre_guillemet):
                sortie.append(" ")
                origine.append(debut_blanc)
            attente = None
        for x in c:
            sortie.append(x)
            origine.append(i)
    return "".join(sortie), origine


def _norm_simple(s: str) -> str:
    return normaliser(s)[0].strip()


class IndexTexte:
    """Prépare une fois le texte source (normalisation + repères de paragraphes)."""

    def __init__(self, texte: str):
        self.texte = texte
        self.norm, self.origine = normaliser(texte)
        # Variante sans aucun tiret : « conver-\\ntible » doit aussi valoir « convertible ».
        garde = [k for k, c in enumerate(self.norm) if c != "-"]
        self.norm_st = "".join(self.norm[k] for k in garde)
        self.origine_st = [self.origine[k] for k in garde]
        self.reperes = reperes(texte)
        self._positions = [p for p, _ in self.reperes]

    def trouver(self, citation: str) -> tuple[int, int] | None:
        """(début, fin) de la PREMIÈRE occurrence de la citation, ou None."""
        toutes = self.trouver_tout(citation)
        return toutes[0] if toutes else None

    def trouver_tout(self, citation: str) -> list[tuple[int, int]]:
        """Toutes les occurrences (début, fin) de la citation dans le texte d'origine.

        Indispensable : les textes réglementaires répètent des formules mot pour mot
        dans plusieurs paragraphes (ex. IFRS 9, 6.8.4 / 6.8.5 / 6.8.6). Ne regarder que
        la première occurrence classerait à tort une bonne référence en « incohérente ».
        """
        morceaux = [m for m in (_norm_simple(x) for x in _ELLIPSE.split(citation)) if m]
        if not morceaux:
            return []
        trouves = self._chercher_tout(morceaux, self.norm, self.origine)
        if not trouves:  # repli : comparaison sans tirets des deux côtés
            sans = [m.replace("-", "") for m in morceaux]
            trouves = self._chercher_tout(sans, self.norm_st, self.origine_st)
        return trouves

    @staticmethod
    def _chercher_tout(morceaux, norm, origine):
        resultats, k0 = [], norm.find(morceaux[0])
        while k0 >= 0:
            depart, ok = k0 + len(morceaux[0]), True
            for m in morceaux[1:]:
                k = norm.find(m, depart)
                if k < 0:
                    ok = False
                    break
                depart = k + len(m)
            if not ok:
                break  # les morceaux suivants manquent après cette occurrence : aussi après les suivantes
            resultats.append((origine[k0], origine[depart - 1] + 1))
            k0 = norm.find(morceaux[0], k0 + 1)
        return resultats

    def paragraphe(self, position: int) -> str | None:
        """Numéro du paragraphe qui contient la position (dernier repère avant elle)."""
        j = bisect_right(self._positions, position) - 1
        return self.reperes[j][1] if j >= 0 else None


def _numeros(s: str) -> list[str]:
    return _NUM_REF.findall(s.replace("–", "-").replace("—", "-"))


def ref_coherente(ref: str, paragraphes: list[str]) -> bool:
    """La référence désigne-t-elle l'un des paragraphes touchés par la citation ?

    « 5.5.17(a) » couvre 5.5.17 ; « B5.5.17–B5.5.20 » couvre B5.5.18 ;
    « art. 17 II 3° » couvre « Article 17 » et « Article 17 II ».
    """
    nums_ref = _numeros(ref)
    ref_norm = _norm_simple(ref)
    for p in paragraphes:
        if p is None:
            continue
        nums_p = _numeros(p)
        if not nums_p:
            # repère sans numéro (« Appendix A », définitions) : comparaison du libellé
            if _norm_simple(p) and _norm_simple(p) in ref_norm:
                return True
            continue
        principal = nums_p[0]
        if principal in nums_ref:
            return True
        # intervalle « X–Y » ou « X-Y » dans la référence
        for a, b in re.findall(r"([A-Z]{0,3}\d+(?:\.\d+)+[A-Z]?)\s*[-–]\s*([A-Z]{0,3}\d+(?:\.\d+)+[A-Z]?)", ref):
            try:
                if _ordre_numero(a) <= _ordre_numero(principal) <= _ordre_numero(b):
                    return True
            except (AttributeError, ValueError):
                pass
    return False


def verifier_ligne(index: IndexTexte, ligne: dict) -> dict:
    """Renvoie {statut, debut, fin, paragraphe} pour une ligne au format pivot."""
    cit = (ligne.get("cit") or "").strip()
    if len(_norm_simple(cit).split()) < MOTS_MIN:
        return {"statut": "trop_courte", "debut": None, "fin": None, "paragraphe": None}
    occurrences = index.trouver_tout(cit)
    if not occurrences:
        return {"statut": "introuvable", "debut": None, "fin": None, "paragraphe": None}
    ref = ligne.get("ref") or ""
    for debut, fin in occurrences:  # valide si UNE occurrence est dans le paragraphe désigné
        touches = [index.paragraphe(debut), index.paragraphe(max(debut, fin - 1))]
        if ref_coherente(ref, touches):
            return {"statut": "valide", "debut": debut, "fin": fin, "paragraphe": touches[0],
                    "nb_occurrences": len(occurrences)}
    debut, fin = occurrences[0]
    return {"statut": "ref_incoherente", "debut": debut, "fin": fin,
            "paragraphe": index.paragraphe(debut), "nb_occurrences": len(occurrences)}


def verifier_referentiel(texte: str, lignes: list[dict]) -> dict:
    """Vérifie toutes les lignes ; renvoie le détail et les taux."""
    index = IndexTexte(texte)
    details = [{"id": l.get("id"), **verifier_ligne(index, l)} for l in lignes]
    n = len(details)
    compte = {s: sum(d["statut"] == s for d in details)
              for s in ("valide", "ref_incoherente", "introuvable", "trop_courte")}
    return {
        "nb_lignes": n,
        "comptes": compte,
        # hallucination factuelle : citation absente du texte OU référence fausse
        "taux_hallucination": (compte["introuvable"] + compte["ref_incoherente"]) / n if n else None,
        "taux_invalide": (n - compte["valide"]) / n if n else None,
        "details": details,
    }
