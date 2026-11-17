"""Lance l'Agent 1 v2 (synchrone) : extraction puis enrichissement.
Commencer TOUJOURS par --simulation (gratuit).

Exemples :
    # voir les sections du document (gratuit, sans clé)
    python scripts/lancer_agent1.py data/corpus/ifrs-9-financial-instruments.pdf --nom "IFRS 9 Financial Instruments" --lister

    # chiffrer puis lancer la mise au point sur un mini-document
    python scripts/lancer_agent1.py data/corpus/ifrs-9-financial-instruments.pdf --nom "IFRS 9 Financial Instruments" --sections S04,S18,S19 --mini --simulation
    python scripts/lancer_agent1.py data/corpus/ifrs-9-financial-instruments.pdf --nom "IFRS 9 Financial Instruments" --sections S04,S18,S19 --mini

    # passage unique sur un préfixe du document (étude de l'essoufflement selon la longueur)
    python scripts/lancer_agent1.py ... --mode unique --sections S01,S02,S03,S04 --mini --sans-enrichissement
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import agent1, config, couts, traces  # noqa: E402
from src.decoupage import decouper  # noqa: E402
from src.extraction import charger_document, empreinte  # noqa: E402

# Hypothèses de la simulation, mesurées sur le run v2 du 22/10 (S04, S18, S19, effort medium) :
# 71 lignes pour 17 471 tokens de texte = 4,1 lignes par millier ; on prend 5 pour la v3,
# qui ajoute options et critères de jugement. 186 et 205 tokens de sortie par ligne mesurés.
LIGNES_PAR_MILLE_TOKENS = 5.0
TOKENS_EXTRACTION_PAR_LIGNE = 190  # ref, cit, dom, obl, typ, crit + JSON
TOKENS_ENRICHISSEMENT_PAR_LIGNE = 210  # ctrl, test + JSON


def simuler(texte, sections, args, ids, modele):
    """Coût prévisionnel détaillé, à partir du compte exact du préfixe (count_tokens, gratuit)."""
    m = lambda x: f"{x:,}".replace(",", " ")
    langue = args.langue or agent1.detecter_langue(texte)
    systeme = agent1.construire_systeme(texte, args.nom, langue)
    try:
        import anthropic

        config.exiger_cle()
        r = anthropic.Anthropic().messages.count_tokens(
            model=modele, system=systeme, messages=[{"role": "user", "content": "x"}]
        )
        prefixe, source = r.input_tokens, "count_tokens (exact)"
    except Exception as e:
        prefixe, source = int(len(texte) / 3.04) + 2_400, f"estimation ({e.__class__.__name__})"

    zone = sum(s.tokens_estimes for s in sections if s.id in ids) if args.mode == "section" \
        else sum(s.tokens_estimes for s in sections)
    nb_lignes = round(zone / 1000 * LIGNES_PAR_MILLE_TOKENS)
    n_extr = 1 if args.mode == "unique" else len(ids)
    n_enr = 0 if args.sans_enrichissement else -(-nb_lignes // args.lot)
    n = n_extr + n_enr
    sortie = nb_lignes * TOKENS_EXTRACTION_PAR_LIGNE + (0 if args.sans_enrichissement else nb_lignes * TOKENS_ENRICHISSEMENT_PAR_LIGNE)
    t = config.TARIFS[modele]
    ecriture = prefixe * t["ecriture_cache"] / 1e6
    lectures = (n - 1) * prefixe * t["lecture_cache"] / 1e6
    cout_sortie = sortie * t["sortie"] / 1e6
    sortie_max = (n_extr * args.max_tokens + n_enr * agent1.MAX_TOKENS_ENRICHISSEMENT) * t["sortie"] / 1e6

    print(f"Modèle {modele} | effort {args.effort} | mode {args.mode} | préfixe {m(prefixe)} tokens [{source}]")
    print(f"Hypothèse : {m(zone)} tokens de texte × {LIGNES_PAR_MILLE_TOKENS} lignes/millier ≈ {nb_lignes} lignes")
    print(f"Requêtes : {n_extr} d'extraction + {n_enr} d'enrichissement (lots de {args.lot}) = {n}")
    print(f"  écriture du préfixe en cache : {m(prefixe)} × {t['ecriture_cache']} / 10⁶ = {ecriture:.3f} $")
    print(f"  relectures du cache          : {n - 1} × {m(prefixe)} × {t['lecture_cache']} / 10⁶ = {lectures:.3f} $")
    print(f"  sortie prévue                : {m(sortie)} × {t['sortie']} / 10⁶ = {cout_sortie:.3f} $")
    print(f"  TOTAL PRÉVU  ≈ {ecriture + lectures + cout_sortie:.2f} $")
    print(f"  TOTAL MAXIMUM (chaque réponse au plafond) ≈ {ecriture + lectures + sortie_max:.2f} $")
    print(f"Déjà dépensé ce mois : {couts.depense():.2f} $ sur {config.BUDGET_MENSUEL_USD:.0f} $ "
          f"(seuil {config.SEUIL_BUDGET:.0%})")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("document")
    p.add_argument("--nom", required=True, help="intitulé du texte, injecté dans le prompt")
    p.add_argument("--langue", help="langue du texte (détectée sinon)")
    p.add_argument("--mode", choices=["section", "unique"], default="section")
    p.add_argument("--sections", help="ex. S04,S18,S19 (toutes par défaut)")
    p.add_argument("--mini", action="store_true", help="document réduit aux sections choisies")
    p.add_argument("--max-tokens", type=int, default=agent1.MAX_TOKENS_DEFAUT)
    p.add_argument("--effort", choices=["low", "medium", "high"], default=agent1.EFFORT_DEFAUT)
    p.add_argument("--sans-enrichissement", action="store_true", help="extraction seule")
    p.add_argument("--lot", type=int, default=agent1.TAILLE_LOT_DEFAUT, help="lignes par lot d'enrichissement")
    p.add_argument("--modele", default=None)
    p.add_argument("--lister", action="store_true", help="afficher les sections et s'arrêter")
    p.add_argument("--simulation", action="store_true", help="chiffrer sans rien appeler de payant")
    a = p.parse_args()

    doc = charger_document(Path(a.document))
    texte, sha = doc["texte"], doc["sha256_texte"]
    params_dec = {"min_tokens": config.DECOUPAGE_MIN_TOKENS, "max_tokens": config.DECOUPAGE_MAX_TOKENS}
    sections = decouper(texte, **params_dec)

    if a.lister:
        for s in sections:
            debut = texte[s.debut : s.debut + 45].replace("\n", " ")
            print(f"{s.id}  {s.tokens_estimes:>6}  {s.titre:<24} | {debut}")
        return

    ids = a.sections.split(",") if a.sections else [s.id for s in sections]
    inconnus = set(ids) - {s.id for s in sections}
    if inconnus:
        sys.exit(f"Sections inconnues : {sorted(inconnus)} (voir --lister)")
    if a.mini:
        texte, sections = agent1.mini_document(texte, sections, ids)
        sha = empreinte(texte)
    modele = a.modele or config.MODELE_EXTRACTION

    if a.simulation:
        simuler(texte, sections, a, ids, modele)
        return

    res = agent1.executer(
        texte=texte, sections=sections, mode=a.mode, nom_document=a.nom, sha_texte=sha,
        ids=ids, langue=a.langue, modele=modele, max_tokens=a.max_tokens, effort=a.effort,
        enrichir=not a.sans_enrichissement, taille_lot=a.lot, params_decoupage=params_dec,
        etiquette=f"agent1-{a.mode}{'-mini' if a.mini else ''}",
    )
    print(f"\n{res['nb_lignes']} lignes au total, {len(res['non_enrichies'])} non enrichies → {res['fichier']}")
    print(json.dumps(couts.bilan(), indent=1, ensure_ascii=False))
    traces.vider()  # envoie les dernières traces LangSmith avant la fin du script
    if traces.actif():
        print(f"Traces envoyées au projet LangSmith « {os.getenv('LANGSMITH_PROJECT', 'projet-conformite')} ».")


if __name__ == "__main__":
    main()
