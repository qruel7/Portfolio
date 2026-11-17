"""Vérifications initiales GRATUITES : aucune génération, aucun coût.

1. Empreinte SHA-256 du PDF (pour le pointeur versionné dans docs/corpus.md).
2. Extraction du texte brut du PDF vers un .txt à côté du PDF (non versionné).
3. Liste des modèles accessibles avec la clé du groupe (models.list, gratuit).
4. Comptage exact des tokens du texte pour chaque modèle passé en argument
   (messages.count_tokens, gratuit).

Usage :
    python scripts/verif_initiale.py CHEMIN_DU_PDF [ID_MODELE ...]

Exemples :
    python scripts/verif_initiale.py data/corpus/ifrs-9-financial-instruments.pdf
    python scripts/verif_initiale.py data/corpus/ifrs-9-financial-instruments.pdf <id_haiku> <id_sonnet>
"""

import hashlib
import os
import sys
from pathlib import Path

import anthropic
import pymupdf
from dotenv import load_dotenv


def empreinte_sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def extraire_texte(chemin_pdf: Path) -> tuple[str, int]:
    with pymupdf.open(chemin_pdf) as doc:
        pages = [page.get_text() for page in doc]
    return "\n".join(pages), len(pages)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    chemin_pdf = Path(sys.argv[1])
    modeles_a_compter = sys.argv[2:]
    if not chemin_pdf.is_file():
        sys.exit(f"Fichier introuvable : {chemin_pdf}")

    # --- 1. Empreinte du document source
    print(f"Document     : {chemin_pdf.name}")
    print(f"Taille       : {chemin_pdf.stat().st_size:,} octets".replace(",", " "))
    print(f"SHA-256      : {empreinte_sha256(chemin_pdf)}")

    # --- 2. Extraction du texte brut (aucun nettoyage à ce stade)
    texte, nb_pages = extraire_texte(chemin_pdf)
    if not texte.strip():
        sys.exit("Aucun texte extrait : le PDF est peut-être scanné (images).")
    chemin_txt = chemin_pdf.with_name(chemin_pdf.stem + "_brut.txt")
    chemin_txt.write_text(texte, encoding="utf-8")
    print(f"Pages        : {nb_pages}")
    print(f"Caractères   : {len(texte):,}".replace(",", " "))
    print(f"Texte écrit  : {chemin_txt}")

    # --- 3. Clé et modèles accessibles
    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY absente : vérifiez le fichier .env à la racine.")
    client = anthropic.Anthropic()  # lit la clé dans l'environnement, jamais en dur

    print("\nModèles accessibles avec cette clé :")
    for m in client.models.list(limit=100):
        print(f"  {m.id:45s} {m.display_name}")

    # --- 4. Comptage exact des tokens, modèle par modèle
    if not modeles_a_compter:
        print("\nRelancez avec un ou plusieurs identifiants de modèle pour compter les tokens.")
        return

    print("\nTokens du texte brut, par modèle :")
    for modele in modeles_a_compter:
        try:
            r = client.messages.count_tokens(
                model=modele,
                messages=[{"role": "user", "content": texte}],
            )
            print(f"  {modele:45s} {r.input_tokens:>9,}".replace(",", " "))
        except anthropic.APIStatusError as e:
            print(f"  {modele:45s} ERREUR {e.status_code} : {e.message}")


if __name__ == "__main__":
    main()
