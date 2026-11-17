"""Dashboard de supervision et de pilotage du projet (Agent 1, Agent 2, essoufflement, coûts).

    streamlit run app_streamlit.py

Lecture seule par défaut : tous les onglets lisent des fichiers déjà produits (gratuit).
L'onglet « Pilotage » lance les scripts du projet : toujours en simulation d'abord ; un
lancement payant exige une case de confirmation, et chaque script appelle verifier_budget().

MODE DÉMONSTRATION : sans clé API (application déployée), ou avec MODE_DEMO=1, l'application
relit les runs figés dans demo/ (scripts/preparer_demo.py) et ne lance aucun appel.
CONFIDENTIALITÉ : le dashboard affiche les référentiels Deloitte. Déploiement uniquement
depuis un dépôt PRIVÉ, application restreinte aux destinataires (partage Streamlit Cloud).
"""

import io
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
if not os.getenv("ANTHROPIC_API_KEY"):  # pas de clé (application déployée) → démonstration
    os.environ.setdefault("MODE_DEMO", "1")

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from src import config, tableau, textes  # noqa: E402
from src.referentiels import charger_referentiel  # noqa: E402

DEMO = config.MODE_DEMO

RACINE = Path(__file__).resolve().parent
RESULTATS = config.DOSSIER_RESULTATS

st.set_page_config(page_title="Agent de conformité réglementaire", layout="wide",
                   page_icon=str(RACINE / "assets" / "icone.png"))



@st.cache_data(ttl=30)
def _runs():
    return tableau.lister_runs()


@st.cache_data(ttl=30)
def _budget():
    return tableau.resume_budget()


def _catalogue():
    """Runs de contrôle (31/10) et run de référence : pour ordonner les menus. Sur Streamlit Cloud,
    les dates de fichiers sont celles du clonage : sans cela, le menu pourrait s'ouvrir sur un placebo."""
    c = tableau._json(RESULTATS / "controles_couverture.json") or {}
    return c.get("source"), c.get("run_reference"), set((c.get("runs_controles") or {}).values())


def _ordonner(noms, prioritaire=None, a_la_fin=()):
    """Le fichier prioritaire en tête, les contrôles à la fin, l'ordre d'origine sinon."""
    def rang(n):
        return 0 if n == prioritaire else (2 if n in a_la_fin or n.startswith("controle-") else 1)
    return sorted(noms, key=rang)


def pct(x):
    return "—" if x is None else f"{100 * x:.1f} %"


def afficher_complementaires():
    """Expériences du 31/10 : essoufflement selon la longueur, Sapin 2, contrôles de couverture."""
    try:
        fichiers = tableau.lister_mesures()["complementaires"]
        if not fichiers:
            st.info("Aucune expérience complémentaire : lancer scripts/preparer_demo.py.")
            return

        st.markdown("Trois expériences menées après l'audition du 27/10, à la demande des encadrants.")
        st.subheader("Essoufflement selon la longueur du document")
        st.markdown(textes.RETENIR_LONGUEUR)
        lon = tableau._json(fichiers["longueur_prefixes.json"]) if "longueur_prefixes.json" in fichiers else None
        if lon:
            pts = pd.DataFrame([p for p in lon["points"] if not p["exclu"]])
            pts["milliers_tokens"] = pts.tokens / 1000
            pts["et"] = pts.ecart_type.fillna(0.0)
            pts["bas"], pts["haut"] = (pts.rappel_large - pts.et).clip(0, 1), (pts.rappel_large + pts.et).clip(0, 1)
            base = alt.Chart(pts).encode(x=alt.X("milliers_tokens:Q", title="Longueur du document (milliers de tokens)"))
            st.altair_chart((base.mark_rule(color="#1f77b4").encode(y="bas:Q", y2="haut:Q")
                             + base.mark_line(point=True, color="#1f77b4").encode(
                                 y=alt.Y("rappel_large:Q", title="Rappel large contre R*", scale=alt.Scale(domain=[0, 1])),
                                 tooltip=["configuration", "repetitions", alt.Tooltip("rappel_large:Q", format=".1%"),
                                          alt.Tooltip("ecart_type:Q", format=".1%"), "lignes"]))
                            .properties(height=340), width="stretch")
            reg = lon.get("regression") or {}
            if reg.get("pente") is not None:
                c = st.columns(4)
                c[0].metric("Pente pour 10 000 tokens", f"{100 * reg['pente_par_10k_tokens']:+.2f} pts")
                c[1].metric("t de Student", f"{reg['t']:.1f}")
                c[2].metric("R²", f"{reg['r2']:.2f}")
                c[3].metric("Observations", reg["n"])
            st.caption(f"{lon.get('document', '')} : passage unique sur les préfixes S01…Sk (une observation par "
                       "répétition, barres = ± un écart-type ; 5 longueurs répétées 3 fois, S01-S10 6 fois, le document "
                       "complet 5 fois). Le préfixe S01 seul est exclu (défaut de mesure sur un mini-document d'une section).")
            st.altair_chart(alt.Chart(pts).mark_line(point=True, color="#7f7f7f").encode(
                x=alt.X("milliers_tokens:Q", title="Longueur du document (milliers de tokens)"),
                y=alt.Y("lignes:Q", title="Lignes produites (moyenne)"), tooltip=["configuration", "lignes"])
                .properties(height=200, title="La sortie plafonne : 200 à 300 lignes quelle que soit la longueur"),
                width="stretch")

        st.subheader("Second texte : Sapin 2, passage unique contre mode section")
        st.markdown(textes.RETENIR_SAPIN)
        sap = tableau._json(fichiers["repetitions_sapin2.json"]) if "repetitions_sapin2.json" in fichiers else None
        if sap:
            st.dataframe(pd.DataFrame(tableau.synthese_repetitions(sap)).round(4), width="stretch", hide_index=True)
            st.caption("Une ligne par mode, 3 répétitions chacun, mesurées contre R* de Sapin 2 (mode section v3 du 24/10).")

        st.subheader("L'Agent 1 « surcouvre »-t-il ? Contrôles de l'Agent 2 (IFRS 9)")
        st.markdown(textes.RETENIR_CONTROLES)
        ctl = tableau._json(fichiers["controles_couverture.json"]) if "controles_couverture.json" in fichiers else None
        if not ctl:
            st.info("Tableau des contrôles absent : relancer scripts/preparer_demo.py (il affiche les runs associés).")
        else:
            df = pd.DataFrame(ctl["lignes"])
            vue = df.assign(**{k: df[k].map(pct) for k in ("couverture_large", "couverture_stricte", "qualite")})
            st.dataframe(vue, width="stretch", hide_index=True)
            st.altair_chart(alt.Chart(df).mark_circle(size=120).encode(
                x=alt.X("lignes_ia:Q", title="Lignes données à l'Agent 2"),
                y=alt.Y("couverture_large:Q", title="Couverture large (dénominateur fixe)", scale=alt.Scale(domain=[0, 1])),
                color=alt.Color("controle:N", title="Référentiel"),
                tooltip=["controle", "lignes_ia", "couverture_large", "qualite"]).properties(height=280), width="stretch")
            st.caption(f"Dénominateur fixe : {ctl['nb_lignes_reference'] - len(ctl['exclues_fixes'])} lignes de référence "
                       f"(exclues : {', '.join(ctl['exclues_fixes']) or 'aucune'}, hors périmètre sur le référentiel complet). "
                       "« hors_perimetre_juge » : lignes que le juge a classées hors périmètre dans ce run.")
    except Exception as exc:  # un onglet en erreur ne doit pas casser les autres
        st.error(f"Cet onglet n'a pas pu s'afficher : {type(exc).__name__}: {exc}")
        st.exception(exc)


def afficher_synthese():
    try:
        st.subheader("Les chiffres clés")
        for debut in range(0, len(textes.CHIFFRES_CLES), 4):
            colonnes = st.columns(4)
            for col, (titre, valeur, detail) in zip(colonnes, textes.CHIFFRES_CLES[debut:debut + 4]):
                with col.container(border=True):
                    st.metric(titre, valeur)
                    st.caption(detail)
        b = _budget()
        st.caption(f"Coût total du projet : {b['total_projet']:.2f} $ pour {b['nb_appels']} appels journalisés.")
        st.markdown(textes.MESSAGES_CLES)
        st.subheader("L'architecture")
        st.graphviz_chart(textes.ARCHITECTURE_DOT)
        with st.expander("Reproduire les résultats en local"):
            st.markdown(textes.REPRODUIRE)
        st.subheader("Versions du prompt de l'Agent 1")
        _, run_ref, controles = _catalogue()
        comp = pd.DataFrame(tableau.comparatif_versions(exclus=controles))
        if comp.empty:
            st.info("Aucun run de l'Agent 2 à comparer.")
        else:
            for k in ("couverture_large", "couverture_stricte", "qualite", "hallucination"):
                comp[k] = comp[k].map(pct)
            comp["lignes_ia"] = comp["lignes_ia"].round(0)
            st.dataframe(comp.rename(columns={"texte": "Texte", "version": "Version", "runs_agent2": "Runs Agent 2",
                                              "lignes_ia": "Lignes produites", "couverture_large": "Couverture large",
                                              "couverture_stricte": "Couverture stricte", "qualite": "Qualité",
                                              "hallucination": "Hallucination"}),
                         width="stretch", hide_index=True)
            st.caption(textes.AIDE_VERSIONS)
        st.subheader("Prise en main")
        st.markdown(textes.ACCUEIL)
        with st.expander("Glossaire : les termes et métriques utilisés dans l'application"):
            st.markdown(textes.GLOSSAIRE)
    except Exception as exc:  # un onglet en erreur ne doit pas casser les autres
        st.error(f"Cet onglet n'a pas pu s'afficher : {type(exc).__name__}: {exc}")
        st.exception(exc)


def afficher_fiche(ev: dict, referentiel: dict | None):
    """Fiche d'une ligne du référentiel : son texte, le verdict élément par élément, les lignes citées."""
    st.divider()
    st.subheader("Fiche d'une ligne du référentiel")
    st.caption("Choisir une ligne pour voir comment l'Agent 1 la couvre : le verdict du juge élément par élément, "
               "puis chaque ligne de l'Agent 1 citée, avec sa référence et sa citation exacte du texte.")
    evals = ev.get("evaluations") or []
    if not evals:
        return
    statut = {e["id_ref"]: e["couverture"] for e in evals}
    pastille = {"totale": "🟩", "partielle": "🟨", "absente": "🟥", "hors_perimetre": "⬜"}
    id_ref = st.selectbox("Ligne du référentiel", list(statut),
                          format_func=lambda i: f"{pastille.get(statut[i], '·')} {i} : {statut[i].replace('_', ' ')}")
    _, lignes_ia = tableau.referentiel_ia_evalue(ev)
    fiche = tableau.fiche_ligne(ev, id_ref, referentiel, lignes_ia)
    if not fiche:
        return
    gauche, droite = st.columns([3, 2])
    with gauche.container(border=True):
        st.markdown(f"**Ligne {id_ref} du référentiel**")
        if fiche["champs"]:
            for nom, valeur in fiche["champs"].items():
                if valeur:
                    st.markdown(f"**{nom}** : {valeur}")
        else:
            st.caption("Texte de la ligne indisponible (référentiel absent).")
    with droite.container(border=True):
        st.metric("Couverture", f"{pastille.get(fiche['couverture'], '')} {fiche['couverture'].replace('_', ' ')}")
        st.metric("Score de qualité", pct(fiche["score"]))
        if fiche["justification"]:
            st.caption(fiche["justification"])
    if fiche["elements"]:
        st.markdown("**Verdict élément par élément**")
        st.dataframe(pd.DataFrame(fiche["elements"]), width="stretch", hide_index=True)
    if fiche["lignes"]:
        st.markdown(f"**Lignes de l'Agent 1 citées par le juge ({len(fiche['lignes'])})**")
        if not lignes_ia:
            st.caption("Référentiel de l'Agent 1 évalué introuvable : seuls les identifiants sont connus.")
        for l in fiche["lignes"]:
            with st.container(border=True):
                if not l["trouvee"]:
                    st.markdown(f"`{l['id']}` : ligne introuvable dans le référentiel évalué.")
                    continue
                valide = "✅ citation retrouvée mot pour mot" if l["statut_citation"] == "valide" else \
                    f"⚠️ citation : {l['statut_citation']}"
                st.markdown(f"`{l['id']}` · **{l.get('ref') or '—'}** · {l.get('typ') or ''} · {l.get('crit') or ''} · {valide}")
                st.markdown(f"**Obligation** : {l.get('obl') or '—'}")
                if l.get("cit"):
                    st.markdown("> " + str(l["cit"]).replace("\n", " "))
                if l.get("ctrl") or l.get("test"):
                    st.markdown(f"**Contrôle** : {l.get('ctrl') or '—'}  \n**Test** : {l.get('test') or '—'}")
    elif fiche["couverture"] != "hors_perimetre":
        st.info("Aucune ligne de l'Agent 1 ne couvre cette ligne du référentiel.")


# ----------------------------------------------------------------------------- barre latérale
with st.sidebar:
    st.image(str(RACINE / "assets" / "logo_master_esa.png"), width=120)
    st.header("Agent de conformité réglementaire")
    if DEMO:
        st.info("**Mode démonstration** : résultats de runs déjà effectués, relus sans clé API "
                "(clés révoquées le 31/10/2026). Aucun appel n'est possible depuis cette application.")
    b = _budget()
    st.metric(f"Dépensé ({b.get('mois') or '—'})", f"{b['depense_mois']:.2f} $",
              help="Source : logs/couts.jsonl (append-only). Dernier mois présent dans le journal.")
    st.progress(min(1.0, b["depense_mois"] / b["budget"]), text=f"sur {b['budget']:.0f} \\$ "
                f"(blocage à {b['plafond_blocage']:.0f} \\$)")
    st.caption(f"Modèle d'extraction : `{config.MODELE_EXTRACTION}`  \nModèle mécanique : `{config.MODELE_MECANIQUE}`")
    if st.button("Relire les fichiers", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("⚠️ Affiche des référentiels Deloitte confidentiels : ne pas diffuser le lien de l'application.")
    st.divider()
    st.caption("**Réalisé par**  \n" + textes.EQUIPE.replace(" · ", "  \n"))

st.title("Agent de conformité réglementaire")
st.caption(f"{textes.SOUS_TITRE}  \n{textes.EQUIPE}")

# L'onglet Pilotage lance des appels API : il n'existe qu'en mode complet (clé dans .env).
onglets = st.tabs(["Synthèse", "Runs", "Coûts", "Agent 1 — référentiel", "Agent 2 — couverture",
                   "Essoufflement", "Expériences complémentaires"] + ([] if DEMO else ["Pilotage"]))

# ----------------------------------------------------------------------------- synthèse
with onglets[0]:
    afficher_synthese()

# ----------------------------------------------------------------------------- runs
with onglets[1]:
    try:
        st.subheader("Runs enregistrés")
        st.caption("Chaque exécution d'un agent est enregistrée avec son modèle, sa version de prompt, l'empreinte du "
                   "texte traité et son nombre de lignes. Filtrer par document pour isoler IFRS 9 ou Sapin 2.")
        runs = _runs()
        if not runs:
            st.info(f"Aucun run dans {RESULTATS}.")
        else:
            df = pd.DataFrame(runs)
            if "erreur" in df.columns and df.erreur.notna().any():
                st.warning("Fichiers illisibles (ignorés) : " + "; ".join(
                    f"{r.fichier} ({r.erreur})" for r in df[df.erreur.notna()].itertuples()))
                df = df[df.erreur.isna()]
            for col in ["fichier", "agent", "mode", "document", "sections", "repetition", "batch", "modele", "effort",
                        "version_prompt", "nb_lignes", "citations_valides", "sortie_tokens"]:
                if col not in df.columns:
                    df[col] = None
            a1, a2 = df[df.agent == "agent1"], df[df.agent == "agent2"]
            c = st.columns(4)
            c[0].metric("Runs Agent 1", len(a1))
            c[1].metric("dont batch", int(a1.batch.sum()))
            c[2].metric("Runs Agent 2", len(a2))
            c[3].metric("Lignes produites (Agent 1, total)", int(a1.nb_lignes.fillna(0).sum()))
            filtre = st.multiselect("Document", sorted(df.document.dropna().unique()))
            vue = df[df.document.isin(filtre)] if filtre else df
            st.dataframe(vue[["fichier", "agent", "mode", "document", "sections", "repetition", "batch", "modele", "effort",
                              "version_prompt", "nb_lignes", "citations_valides", "sortie_tokens"]],
                         width="stretch", hide_index=True)
    except Exception as exc:  # un onglet en erreur ne doit pas casser les autres
        st.error(f"Cet onglet n'a pas pu s'afficher : {type(exc).__name__}: {exc}")
        st.exception(exc)

# ----------------------------------------------------------------------------- coûts
with onglets[2]:
    try:
        st.subheader("Suivi des coûts")
        with st.expander("Comment lire cet onglet"):
            st.markdown(textes.AIDE_COUTS)
        b = _budget()
        c = st.columns(4)
        c[0].metric(f"Dépensé ({b.get('mois') or '—'})", f"{b['depense_mois']:.2f} $")
        if DEMO:
            c[1].metric("Total du projet", f"{b['total_projet']:.2f} $")
        else:
            c[1].metric("Reste avant blocage", f"{b['reste_avant_blocage']:.2f} $")
        c[2].metric("Appels journalisés", b["nb_appels"])
        detail = pd.DataFrame(b["par_etiquette"])
        if not detail.empty:
            lu, ecrit = detail.cache_lu.sum(), detail.cache_ecrit.sum()
            c[3].metric("Lectures / écritures de cache", f"{lu / ecrit:.1f}" if ecrit else "—",
                        help="Rituel du vendredi : plus le ratio est haut, mieux le cache sert")
            st.altair_chart(alt.Chart(pd.DataFrame(b["par_jour"])).mark_bar().encode(
                x=alt.X("jour:N", title="Jour"), y=alt.Y("cout_usd:Q", title="Coût (USD)"),
                tooltip=["jour", "cout_usd"]).properties(height=220), width="stretch")
            st.markdown("**Répartition par étiquette**")
            st.dataframe(detail, width="stretch", hide_index=True)
            st.caption("Tarifs : support de cadrage (versions 5), batch −50 %. Le journal est la source de vérité ; "
                       "LangSmith n'en est qu'une copie (traces sans texte).")
    except Exception as exc:  # un onglet en erreur ne doit pas casser les autres
        st.error(f"Cet onglet n'a pas pu s'afficher : {type(exc).__name__}: {exc}")
        st.exception(exc)

# ----------------------------------------------------------------------------- agent 1
with onglets[3]:
    try:
        st.subheader("Référentiel produit par l'Agent 1")
        with st.expander("Comment lire cet onglet", expanded=DEMO):
            st.markdown(textes.AIDE_AGENT1)
        fichiers = tableau.lister_referentiels_ia()
        sources = [f.name for f in fichiers] + [r["fichier"] for r in _runs() if r["agent"] == "agent1"]
        if not sources:
            st.info("Aucun référentiel consolidé ni run d'Agent 1.")
        else:
            source_ref, _, _ = _catalogue()
            choix = st.selectbox("Référentiel", _ordonner(sources, f"{source_ref}.json" if source_ref else None))
            meta, lignes = tableau.lignes_referentiel(RESULTATS / choix)
            df = pd.DataFrame(lignes)
            if df.empty:
                st.warning("Ce fichier ne contient aucune ligne.")
            else:
                statuts = tableau.statuts_citations(lignes)
                n = len(lignes)
                c = st.columns(4)
                c[0].metric("Lignes", n)
                c[1].metric("Citations valides", pct(statuts.get("valide", 0) / n))
                c[2].metric("Hallucination factuelle",
                            pct((statuts.get("introuvable", 0) + statuts.get("ref_incoherente", 0)) / n),
                            help="Citation introuvable dans le texte, ou référence incohérente (contrôle déterministe)")
                c[3].metric("Lignes fusionnées (doublons)", sum(len(l.get("_doublons") or []) for l in lignes))
                df["statut_citation"] = [(l.get("_verif") or {}).get("statut") for l in lignes]
                df["section"] = [l.get("_tache") for l in lignes]
                f1, f2, f3 = st.columns(3)
                crit = f1.multiselect("Criticité", sorted(df.crit.dropna().unique()) if "crit" in df else [])
                typ = f2.multiselect("Type", sorted(df.typ.dropna().unique()) if "typ" in df else [])
                texte = f3.text_input("Recherche (obligation, domaine, référence)")
                vue = df
                if crit:
                    vue = vue[vue.crit.isin(crit)]
                if typ:
                    vue = vue[vue.typ.isin(typ)]
                if texte:
                    m = texte.lower()
                    vue = vue[vue.apply(lambda r: m in f"{r.get('obl')} {r.get('dom')} {r.get('ref')}".lower(), axis=1)]
                colonnes = [c for c in ["id", "ref", "dom", "obl", "typ", "crit", "ctrl", "test", "statut_citation", "cit"]
                            if c in vue.columns]
                st.dataframe(vue[colonnes], width="stretch", hide_index=True, height=420)
                d1, d2 = st.columns(2)
                pivot = df[[c for c in ["id", "ref", "cit", "dom", "obl", "typ", "crit", "ctrl", "test",
                                        "statut_citation", "section"] if c in df.columns]]
                tampon = io.BytesIO()
                pivot.to_excel(tampon, index=False, sheet_name="referentiel")
                d1.download_button("Télécharger ce référentiel (format pivot, Excel)", tampon.getvalue(),
                                   file_name=f"{Path(choix).stem}_pivot.xlsx", width="stretch")
                exports = sorted(RESULTATS.glob(f"{Path(choix).stem}_export_*.xlsx"))
                if exports:
                    d2.download_button("Télécharger au format du référentiel Deloitte (Excel)", exports[0].read_bytes(),
                                       file_name=exports[0].name, width="stretch",
                                       help="Conversion déterministe du pivot vers les colonnes du référentiel, sans LLM.")
                else:
                    d2.caption("Format Deloitte : disponible pour les référentiels dédoublonnés de la chaîne complète.")
                g1, g2 = st.columns(2)
                g1.altair_chart(alt.Chart(df).mark_bar().encode(
                    x=alt.X("count():Q", title="Lignes"), y=alt.Y("crit:N", title="Criticité", sort="-x")
                ).properties(height=180, title="Criticité"), width="stretch")
                if df.section.notna().any():
                    g2.altair_chart(alt.Chart(df.dropna(subset=["section"])).mark_bar().encode(
                        x=alt.X("section:N", title="Section"), y=alt.Y("count():Q", title="Lignes")
                    ).properties(height=180, title="Lignes par section"), width="stretch")
    except Exception as exc:  # un onglet en erreur ne doit pas casser les autres
        st.error(f"Cet onglet n'a pas pu s'afficher : {type(exc).__name__}: {exc}")
        st.exception(exc)

# ----------------------------------------------------------------------------- agent 2
with onglets[4]:
    try:
        st.subheader("Couverture du référentiel de référence (Agent 2)")
        with st.expander("Comment lire cet onglet", expanded=DEMO):
            st.markdown(textes.AIDE_AGENT2)
        runs2 = [r for r in _runs() if r["agent"] == "agent2"]
        if not runs2:
            st.info("Aucun run d'Agent 2.")
        else:
            _, run_ref, controles = _catalogue()
            choix = st.selectbox("Run de l'Agent 2", _ordonner([r["fichier"] for r in runs2], run_ref, controles),
                                 help="Les runs de contrôle (placebo, sous-échantillons) sont en fin de liste.")
            ev = tableau.evaluation_agent2(RESULTATS / choix)
            if not ev or not ev.get("metriques"):
                st.warning("Run incomplet.")
            else:
                m, e = ev["metriques"], ev["entete"]
                st.caption(f"Document : {e.get('nom_document')} · référentiel : {e.get('referentiel')} · "
                           f"source des chiffres : {ev['source']}")
                c = st.columns(5)
                c[0].metric("Couverture stricte", pct(m.get("couverture_stricte")), help="Lignes couvertes totalement")
                c[1].metric("Couverture large", pct(m.get("couverture_large")), help="Totalement ou partiellement")
                c[2].metric("Qualité moyenne", pct(m.get("qualite_moyenne")))
                c[3].metric("Hors périmètre", m.get("nb_hors_perimetre"))
                c[4].metric("Lignes IA pertinentes (suppl.)", pct(m.get("taux_pertinence_supplementaires")))
                referentiel = None
                chemin_ref = config.DOSSIER_REFERENTIELS / str(e.get("referentiel"))
                if chemin_ref.exists():
                    referentiel = charger_referentiel(chemin_ref)
                couv = pd.DataFrame(tableau.table_couverture(ev, referentiel))
                couleurs = {"totale": "#cfe8cf", "partielle": "#fff1c2", "absente": "#f6c9c9", "hors_perimetre": "#e3e3e3"}
                st.markdown("**Ligne par ligne**")
                st.dataframe(couv.style.apply(lambda r: [(f"background-color: {couleurs[r.couverture]}; color: #1A1A1A"
                                                         if r.couverture in couleurs else "")] * len(r),
                                              axis=1), width="stretch", hide_index=True)
                g1, g2 = st.columns(2)
                g1.altair_chart(alt.Chart(couv).mark_bar().encode(
                    x=alt.X("count():Q", title="Lignes de référence"), y=alt.Y("couverture:N", sort="-x"),
                    color=alt.Color("couverture:N", scale=alt.Scale(domain=list(couleurs), range=list(couleurs.values())),
                                    legend=None)).properties(height=180, title="Statuts"), width="stretch")
                pert = pd.DataFrame(ev.get("pertinences") or [])
                if not pert.empty:
                    g2.altair_chart(alt.Chart(pert).mark_bar().encode(
                        x=alt.X("count():Q", title="Lignes IA supplémentaires"), y=alt.Y("p:N", title="Pertinence")
                    ).properties(height=180, title="Lignes ajoutées par l'IA"), width="stretch")
                with st.expander("Éléments évalués (pour la relecture humaine du juge)"):
                    st.dataframe(pd.DataFrame(tableau.table_elements(ev)), width="stretch", hide_index=True)
                with st.expander("Lignes IA supplémentaires et leur pertinence"):
                    st.dataframe(pert, width="stretch", hide_index=True)
                gap = RESULTATS / (Path(choix).stem + "_gap_analysis.xlsx")
                if gap.exists():
                    st.download_button("Télécharger la gap analysis (Excel)", gap.read_bytes(), file_name=gap.name)
                afficher_fiche(ev, referentiel)
    except Exception as exc:  # un onglet en erreur ne doit pas casser les autres
        st.error(f"Cet onglet n'a pas pu s'afficher : {type(exc).__name__}: {exc}")
        st.exception(exc)

# ----------------------------------------------------------------------------- essoufflement
with onglets[5]:
    try:
        st.subheader("Essoufflement : rappel selon la position dans le texte")
        st.markdown(textes.RETENIR_ESSOUFFLEMENT)
        with st.expander("Comment lire le graphique"):
            st.markdown(textes.AIDE_ESSOUFFLEMENT)
        mesures = tableau.lister_mesures()
        if not mesures["repetitions"] and not mesures["essoufflement"]:
            st.info("Aucune mesure : lancer scripts/essoufflement.py ou scripts/repetitions.py.")
        else:
            regle = st.radio("Règle d'appariement", ["large", "stricte"], horizontal=True,
                             help="stricte : citations qui se chevauchent ; large : même paragraphe")
            fusion, synth = {}, []
            for f in mesures["repetitions"]:
                d = tableau._json(f) or {}
                fusion.update({k: v for k, v in d.items() if not k.startswith("_")})
            if fusion:
                pts = pd.DataFrame(tableau.courbes_rc(fusion))
                pts = pts[pts.regle == regle]
                choix = st.multiselect("Configurations", sorted(pts.configuration.unique()),
                                       default=sorted(pts.configuration.unique()))
                pts = pts[pts.configuration.isin(choix)]
                palette = {"unique:complet": "#d62728", "section:complet": "#1f77b4", "unique:S01-S10": "#ff7f0e",
                           "unique:S11-S27": "#2ca02c"}
                noms = sorted(pts.configuration.unique())
                couleurs_cfg = [palette.get(n, "#7f7f7f") for n in noms]
                base = alt.Chart(pts).encode(
                    x=alt.X("c:Q", title="Section c (position dans le document complet)"),
                    color=alt.Color("configuration:N", title="Configuration",
                                    scale=alt.Scale(domain=noms, range=couleurs_cfg)))
                st.altair_chart((base.mark_area(opacity=0.15).encode(y="bas:Q", y2="haut:Q")
                                 + base.mark_line(point=True).encode(
                                     y=alt.Y("rappel:Q", title="Rappel moyen r(c) contre R*", scale=alt.Scale(domain=[0, 1])),
                                     tooltip=["configuration", "section", alt.Tooltip("rappel:Q", format=".1%"), "k"]))
                                .properties(height=380), width="stretch")
                st.caption("Bande : ± un écart-type entre les répétitions. Les mini-documents (S01-S10, S11-S27) sont "
                           "placés sur les numéros de section du document complet : on compare ainsi le même contenu "
                           "traité seul ou en fin de document.")
                synth = pd.DataFrame(tableau.synthese_repetitions(fusion)).round(4)
                st.markdown("**Synthèse par configuration**")
                st.dataframe(synth, width="stretch", hide_index=True)
            with st.expander("Mesures sur un run isolé"):
                if mesures["essoufflement"]:
                    f = st.selectbox("Fichier", [p.name for p in mesures["essoufflement"]])
                    d = tableau._json(RESULTATS / f) or {}
                    ps = pd.DataFrame(d.get("par_section", []))
                    if not ps.empty:
                        st.altair_chart(alt.Chart(ps).mark_line(point=True).encode(
                            x=alt.X("c:Q"), y=alt.Y(f"r_{regle}:Q", scale=alt.Scale(domain=[0, 1]), title="r(c)"),
                            tooltip=["section", "n_ref", f"r_{regle}"]).properties(height=260), width="stretch")
                        st.json({k: v for k, v in (d.get("regressions") or {}).items()})
    except Exception as exc:  # un onglet en erreur ne doit pas casser les autres
        st.error(f"Cet onglet n'a pas pu s'afficher : {type(exc).__name__}: {exc}")
        st.exception(exc)

# ----------------------------------------------------------------------------- expériences complémentaires
with onglets[6]:
    afficher_complementaires()

# ----------------------------------------------------------------------------- pilotage
if not DEMO:
    with onglets[7]:
        try:
            st.subheader("Pilotage des agents")
            st.markdown("Chaque action lance un script du projet. **Simuler** est gratuit (chiffrage, aucun appel payant). "
                        "**Lancer** est payant : il faut cocher la confirmation après avoir lu la simulation. "
                        "Le plafond budgétaire est vérifié par les scripts eux-mêmes.")
            corpus = sorted((config.RACINE / "data" / "corpus").glob("*.pdf"))
            refs = sorted((config.RACINE / "data" / "referentiels").glob("*.xlsx"))
            consolides = [p.name for p in tableau.lister_referentiels_ia()]
            action = st.selectbox("Action", ["Pipeline complet (LangGraph)", "Agent 1 (mode section)", "Agent 1 (passage unique, extraction seule)",
                                             "Dédoublonnage", "Agent 2", "Export au format du référentiel",
                                             "Essoufflement d'un run"])
            cmd, payant, confirmation = None, True, []
            if action.startswith("Pipeline"):
                doc = st.selectbox("Document", [p.name for p in corpus], key="pl_doc")
                nom = st.text_input("Intitulé du texte (injecté dans le prompt)", key="pl_nom")
                ref = st.selectbox("Référentiel de référence (Agent 2 et export)", ["(aucun)"] + [p.name for p in refs])
                versions = sorted({f.stem.split("_")[-1] for f in (RACINE / "src" / "prompts").glob("agent1_systeme_*.txt")})
                version = st.selectbox("Version des prompts de l'Agent 1", ["défaut"] + versions)
                etapes = st.multiselect("Étapes", ["agent1", "rattrapage", "dedoublonnage", "agent2", "export"],
                                        default=["agent1", "rattrapage", "dedoublonnage", "agent2", "export"])
                if doc and nom and etapes:
                    cmd = ["scripts/lancer_pipeline.py", f"data/corpus/{doc}", "--nom", nom, "--etapes", ",".join(etapes)]
                    if ref != "(aucun)":
                        cmd += ["--referentiel", f"data/referentiels/{ref}"]
                    if version != "défaut":
                        cmd += ["--version", version]
                    confirmation = ["--confirmer"]
            elif action.startswith("Agent 1"):
                doc = st.selectbox("Document", [p.name for p in corpus])
                nom = st.text_input("Intitulé du texte (injecté dans le prompt)")
                sections = st.text_input("Sections (vide = toutes ; ex. S04,S18)")
                if doc and nom:
                    cmd = ["scripts/lancer_agent1.py", f"data/corpus/{doc}", "--nom", nom]
                    if "unique" in action:
                        cmd += ["--mode", "unique", "--sans-enrichissement", "--max-tokens", "128000"]
                    if sections.strip():
                        cmd += ["--sections", sections.strip(), "--mini"]
            elif action == "Dédoublonnage":
                src_ = st.selectbox("Référentiel consolidé", [c for c in consolides if "dedoublonne" not in c])
                if src_:
                    cmd = ["scripts/dedoublonner.py", f"resultats/{src_}"]
            elif action == "Agent 2":
                ia = st.selectbox("Référentiel de l'IA", consolides)
                ref = st.selectbox("Référentiel de référence", [p.name for p in refs])
                nom = st.text_input("Intitulé du texte")
                if ia and ref and nom:
                    cmd = ["scripts/lancer_agent2.py", "--ia", f"resultats/{ia}", "--referentiel",
                           f"data/referentiels/{ref}", "--nom", nom]
            elif action == "Export au format du référentiel":
                payant = False
                ia = st.selectbox("Référentiel de l'IA", consolides)
                ref = st.selectbox("Format (référentiel de référence)", [p.name for p in refs])
                if ia and ref:
                    cmd = ["scripts/exporter.py", f"resultats/{ia}", "--format", f"data/referentiels/{ref}"]
            else:
                payant = False
                run = st.selectbox("Run", [r["fichier"] for r in _runs() if r["agent"] == "agent1"])
                ref = st.selectbox("Pseudo-référence R* (consolidé du mode section)", consolides)
                doc = st.selectbox("Document", [p.name for p in corpus])
                if run and ref and doc:
                    cmd = ["scripts/essoufflement.py", f"resultats/{run}", "--reference", f"resultats/{ref}",
                           "--document", f"data/corpus/{doc}"]

            def executer(arguments):
                st.code("python " + " ".join(f'"{a}"' if " " in a else a for a in arguments), language="bash")
                zone, sortie = st.empty(), []
                with subprocess.Popen([sys.executable, *arguments], cwd=RACINE, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                      env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}) as p:
                    for ligne in p.stdout:
                        sortie.append(ligne.rstrip())
                        zone.code("\n".join(sortie[-60:]), language="text")
                (st.success if p.returncode == 0 else st.error)(f"Terminé (code {p.returncode}).")
                st.cache_data.clear()

            if cmd:
                c1, c2 = st.columns(2)
                if payant:
                    if c1.button("Simuler (gratuit)", width="stretch"):
                        executer(cmd + ["--simulation"])
                    ok = c2.checkbox("J'ai lu la simulation et j'accepte le coût annoncé")
                    if c2.button("Lancer (payant)", disabled=not ok, type="primary", width="stretch"):
                        executer(cmd + confirmation)
                elif c1.button("Exécuter (gratuit)", width="stretch"):
                    executer(cmd)
            else:
                st.caption("Renseigner les champs ci-dessus.")
        except Exception as exc:  # un onglet en erreur ne doit pas casser les autres
            st.error(f"Cet onglet n'a pas pu s'afficher : {type(exc).__name__}: {exc}")
            st.exception(exc)
