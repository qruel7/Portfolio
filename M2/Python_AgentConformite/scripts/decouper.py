"""Nettoie un document et le découpe en sections. GRATUIT (aucune génération).

Usage :
    python scripts/decouper.py data/corpus/ifrs-9-financial-instruments.pdf
    python scripts/decouper.py data/corpus/ifrs-9-financial-instruments.pdf --compter

Produit, à côté du document (dossier data/, non versionné) :
    <nom>_net.txt        le texte nettoyé : LE texte que lit le modèle et où l'on vérifie les citations
    <nom>_sections.json  les sections (positions dans le texte nettoyé, tokens)
--compter : remplace l'estimation par le compte exact de count_tokens (gratuit, clé requise).
"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.decoupage import decouper  # noqa: E402
from src.extraction import charger_document  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("document")
    p.add_argument("--compter", action="store_true", help="tokens exacts via count_tokens")
    p.add_argument("--min", type=int, default=config.DECOUPAGE_MIN_TOKENS)
    p.add_argument("--max", type=int, default=config.DECOUPAGE_MAX_TOKENS)
    a = p.parse_args()

    chemin = Path(a.document)
    doc = charger_document(chemin)
    texte = doc["texte"]
    sections = decouper(texte, min_tokens=a.min, max_tokens=a.max)

    sortie_txt = chemin.with_name(chemin.stem + "_net.txt")
    sortie_txt.write_text(texte, encoding="utf-8")

    exacts = None
    if a.compter:
        import anthropic

        config.exiger_cle()
        client = anthropic.Anthropic()
        exacts = []
        for s in sections:
            r = client.messages.count_tokens(
                model=config.MODELE_EXTRACTION,
                messages=[{"role": "user", "content": s.texte(texte)}],
            )
            exacts.append(r.input_tokens)

    lignes = []
    for k, s in enumerate(sections):
        d = asdict(s)
        if exacts:
            d["tokens_exacts"] = exacts[k]
        lignes.append(d)
    sortie_json = chemin.with_name(chemin.stem + "_sections.json")
    sortie_json.write_text(
        json.dumps(
            {"sha256_texte": doc["sha256_texte"], "rapport_nettoyage": doc["rapport"], "sections": lignes},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    print(f"Lignes retirées (en-têtes/pieds) : {doc['rapport']['formes_retirees']}")
    nb = f"{len(texte):,}".replace(",", " ")
    print(f"Texte nettoyé : {nb} caractères, SHA-256 {doc['sha256_texte'][:12]}…")
    print(f"\n{'id':4} {'estimés':>8} {'exacts':>8}  titre / début")
    for k, s in enumerate(sections):
        ex = f"{exacts[k]:>8}" if exacts else f"{'-':>8}"
        debut = texte[s.debut : s.debut + 40].replace("\n", " ")
        print(f"{s.id:4} {s.tokens_estimes:>8} {ex}  {s.titre:<22} | {debut}")
    total_est = sum(s.tokens_estimes for s in sections)
    millier = lambda n: f"{n:,}".replace(",", " ")
    bilan = f"\n{len(sections)} sections, {millier(total_est)} tokens estimés"
    print(bilan + (f", {millier(sum(exacts))} exacts" if exacts else ""))
    print(f"Écrit : {sortie_txt}\n        {sortie_json}")


if __name__ == "__main__":
    main()
