"""
=============================================================
Chunking universel — Base de connaissances Master ESA (v4 enrichi)
=============================================================
Découpe les fichiers Markdown en chunks ET enrichit chaque chunk
avec un résumé contextuel pour améliorer la qualité des embeddings.

Le texte enrichi (avec contexte) est utilisé pour l'EMBEDDING.
Le texte original est conservé pour être envoyé au LLM.
"""

import re
import json
from pathlib import Path


# === CONFIGURATION ===
MARKDOWN_DIR = "./markdown_files"
OUTPUT_FILE = "./all_chunks.json"
MIN_TOKENS = 80
# ======================


# === DESCRIPTIONS SYNTHÉTIQUES PAR FICHIER ===
FILE_DESCRIPTIONS = {
    "master_esa_knowledge_base.md":
        "Présentation générale du Master ESA (Économétrie et Statistique Appliquée) "
        "de l'Université d'Orléans : organisation du cursus en 2 ans, programme M1/M2, "
        "certifications proposées, débouchés professionnels, entreprises partenaires.",

    "master_esa_candidature.md":
        "Procédure de candidature et d'admission au Master ESA : conditions d'accès, "
        "prérequis académiques, modalités de dépôt de dossier sur Mon Master ou via "
        "Campus France pour les étudiants étrangers, statistiques de recrutement.",

    "master_esa_equipe_pedagogique.md":
        "Équipe pédagogique du Master ESA : direction, enseignants-chercheurs, "
        "intervenants extérieurs issus du monde professionnel (SAS, banques, conseil).",

    "master_esa_insertion.md":
        "Statistiques d'insertion professionnelle des diplômés du Master ESA : "
        "enquêtes annuelles, taux d'emploi, salaires, types de contrats (CDI/CDD), "
        "rapidité d'insertion, évolution sur les promotions 2007 à 2024.",

    "master_esa_liens_utiles_contact.md":
        "Informations pratiques pour les étudiants : adresse, contact email et téléphone, "
        "liens vers l'université, services aux étudiants, prêt étudiant Crédit Agricole.",

    "master_esa_recherche.md":
        "Voie recherche du Master ESA : préparation au doctorat, mémoire de recherche, "
        "lien avec le laboratoire LEO, profils des doctorants, prix et distinctions "
        "obtenus, débouchés académiques (maître de conférences, professeur).",

    "master_esa_stages.md":
        "Stages de fin d'études du Master ESA : missions types, entreprises d'accueil, "
        "procédure de convention de stage, soutenance, calendrier.",

    "master_esa_syllabus_S7.md":
        "Programme détaillé du semestre 7 (M1, premier semestre) du Master ESA : "
        "matières enseignées (programmation SAS, R, Python, statistique mathématique, "
        "séries temporelles, analyse des données, apprentissage statistique, "
        "finance quantitative, anglais), enseignants, objectifs pédagogiques, plans de cours.",

    "master_esa_syllabus_S9.md":
        "Programme détaillé du semestre 9 (M2, premier semestre) du Master ESA : "
        "matières enseignées (scoring, modèles de durée, machine learning, big data, "
        "réglementation prudentielle, finance durable, détection de fraude), enseignants, "
        "objectifs pédagogiques, plans de cours.",

    "master_esa_syllabus_S10.md":
        "Programme détaillé du semestre 10 (M2, dernier semestre) du Master ESA : "
        "matières des voies professionnelle (data mining, risque de crédit, assurance) "
        "et recherche (macroéconomie, économétrie, microéconomie, finance avancées), "
        "stage de fin d'études ou mémoire de recherche.",
}


def slugify(text: str) -> str:
    text = text.lower()
    for old, new in [("àâä","a"), ("éèêë","e"), ("îï","i"), ("ôö","o"), ("ùûü","u"), ("ç","c")]:
        for char in old:
            text = text.replace(char, new)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def detect_access_flag(content: str) -> str:
    patterns = [r"réservé aux utilisateurs connectés", r"acces.*logged.in", r"connecté.*uniquement"]
    for pattern in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return "logged_in"
    return "public"


def is_alumni_file(filename: str) -> bool:
    return "diplomes_" in filename or "diplômes_" in filename


def extract_promotion_year(content: str, filename: str) -> str:
    title_match = re.search(r"# .*?(\d{4})", content)
    if title_match:
        return title_match.group(1)
    file_match = re.search(r"(\d{4})", filename)
    return file_match.group(1) if file_match else "inconnue"


def enrich_chunk_text(text: str, filename: str, section: str = "") -> str:
    """Préfixe le chunk avec un résumé contextuel pour améliorer l'embedding."""
    description = FILE_DESCRIPTIONS.get(filename, "")
    if not description:
        return text
    prefix = f"[Contexte : {description}]"
    if section:
        prefix += f"\n[Section : {section}]"

    # Cas spécial pour les enquêtes d'insertion : ajouter la convention de promo
    # "Promotion 2019/2020" correspond à l'année du diplôme 2020
    promo_match = re.search(r"Promotion\s+(\d{4})/(\d{4})", text)
    if promo_match:
        annee_debut = promo_match.group(1)
        annee_fin = promo_match.group(2)
        prefix += (
            f"\n[IMPORTANT — Convention de promotion : "
            f"« Promotion {annee_debut}/{annee_fin} » = « Promotion {annee_fin} » "
            f"(les étudiants ont été diplômés en {annee_fin}). "
            f"Si l'utilisateur demande des informations sur la « promotion {annee_fin} », "
            f"« promo {annee_fin} », ou « stats {annee_fin} », ce chunk est la BONNE réponse. "
            f"À ne pas confondre avec la promotion {annee_fin}/{int(annee_fin)+1} qui désignerait la promotion {int(annee_fin)+1}.]"
        )

    return f"{prefix}\n\n{text}"


def is_syllabus_file(filename: str) -> bool:
    """Vérifie si le fichier est un syllabus de semestre."""
    return "syllabus_" in filename.lower()


def extract_syllabus_semester(filename: str) -> str:
    """Extrait l'identifiant du semestre depuis le nom de fichier (S7, S9, S10)."""
    match = re.search(r"[Ss](\d+)", filename)
    return f"S{match.group(1)}" if match else "?"


def build_syllabus_summary_chunk(filepath: str, all_chunks: list) -> dict:
    """
    Construit un chunk synthèse listant toutes les matières d'un syllabus,
    avec leur enseignant si trouvé. À placer en plus des chunks détaillés.
    """
    filename = Path(filepath).name
    file_slug = slugify(Path(filepath).stem)
    semester = extract_syllabus_semester(filename)

    # Récupérer les titres des sections (= matières)
    matieres = []
    for c in all_chunks:
        section = c["metadata"].get("section", "")
        # On exclut les sections "Présentation", "Total", etc.
        if section and section not in matieres:
            matieres.append(section)

    if not matieres:
        return None

    # Mapping semestre → titre du chunk
    semester_labels = {
        "S7": "Semestre 7 (M1, premier semestre)",
        "S9": "Semestre 9 (M2, premier semestre)",
        "S10": "Semestre 10 (M2, dernier semestre)",
    }
    label = semester_labels.get(semester, f"Semestre {semester}")

    original_text = (
        f"# Liste complète des matières du {label} du Master ESA\n\n"
        f"Le {label} comprend {len(matieres)} matière(s) :\n\n"
    )
    for i, m in enumerate(matieres, 1):
        original_text += f"{i}. {m}\n"
    original_text += (
        "\n\nPour le détail de chaque matière (enseignant, prérequis, plan de cours, "
        "bibliographie), consulter les sections correspondantes du syllabus."
    )

    enriched_text = (
        f"[Contexte : Liste exhaustive de toutes les matières enseignées au {label} "
        f"du Master ESA. Utile pour les questions du type 'liste des matières', "
        f"'programme du semestre', 'enseignements du {semester}', 'cours du {semester}'.]\n\n"
        f"{original_text}"
    )

    return {
        "id": f"{file_slug}__liste_matieres",
        "text": enriched_text,
        "original_text": original_text,
        "metadata": {
            "source_file": filename,
            "doc_title": f"Syllabus {label}",
            "section": f"Liste complète des matières du {label}",
            "subsection": "",
            "approx_tokens": estimate_tokens(enriched_text),
            "url": "",
            "access": "public",
            "type": "syllabus_summary",
        }
    }


def chunk_alumni_file(filepath: str) -> list[dict]:
    filename = Path(filepath).name
    file_slug = slugify(Path(filepath).stem)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    title_match = re.match(r"^# (.+)", content, re.MULTILINE)
    doc_title = title_match.group(1).strip() if title_match else filename
    access = detect_access_flag(content)
    promo = extract_promotion_year(content, filename)
    is_current_cohort = bool(re.search(r"(étudiants en cours|en stage|promotion en cours)", content, re.IGNORECASE))
    status_label = "étudiant en cours (en stage)" if is_current_cohort else "diplômé"

    chunks = []
    # On garde aussi la liste de tous les alumni pour générer un chunk synthèse
    all_alumni_summary = []

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        if re.match(r"^\|[\s\-]+\|", line):
            continue
        if "Nom" in line and "Prénom" in line:
            continue

        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 4:
            continue

        nom = cols[0]
        prenom = cols[1]
        poste = cols[2] if cols[2] != "—" else None
        entreprise = cols[3] if cols[3] != "—" else None
        linkedin_raw = cols[4] if len(cols) > 4 else "—"
        linkedin_match = re.search(r"\((https?://[^\)]+)\)", linkedin_raw)
        linkedin = linkedin_match.group(1) if linkedin_match else None

        if nom == "—" and prenom == "—":
            continue

        text_parts = [f"**{prenom} {nom}** — Promotion {promo} du Master ESA ({status_label})"]
        if poste:
            text_parts.append(f"Poste actuel : {poste}")
        if entreprise:
            text_parts.append(f"Entreprise : {entreprise}")
        if not poste and not entreprise:
            text_parts.append("Poste et entreprise non renseignés.")
        if linkedin:
            text_parts.append(f"LinkedIn : {linkedin}")

        original_text = "\n".join(text_parts)
        enriched_text = (
            f"[Contexte : Diplômé du Master ESA, promotion {promo}. "
            f"Informations sur le parcours professionnel actuel d'un ancien étudiant.]\n\n"
            f"{original_text}"
        )

        chunk_id = f"{file_slug}__{slugify(nom)}_{slugify(prenom)}"
        chunks.append({
            "id": chunk_id,
            "text": enriched_text,
            "original_text": original_text,
            "metadata": {
                "source_file": filename,
                "doc_title": doc_title,
                "section": f"Diplômé promotion {promo}",
                "subsection": f"{prenom} {nom}",
                "approx_tokens": estimate_tokens(enriched_text),
                "url": "",
                "access": access,
                "type": "alumni",
                "promotion": promo,
                "nom": nom,
                "prenom": prenom,
                "entreprise": entreprise or "",
                "poste": poste or "",
            }
        })

        # Stocker une ligne synthétique pour le chunk de synthèse
        summary_line = f"- {prenom} {nom}"
        details = []
        if poste:
            details.append(poste)
        if entreprise:
            details.append(f"chez {entreprise}")
        if details:
            summary_line += " — " + ", ".join(details)
        all_alumni_summary.append(summary_line)

    # ── CHUNK SYNTHÈSE : liste complète de la promotion ──
    if all_alumni_summary:
        summary_header = f"# Liste complète des {status_label}s du Master ESA — Promotion {promo}\n\n"
        summary_header += f"Nombre total : {len(all_alumni_summary)}\n\n"
        original_summary = summary_header + "\n".join(all_alumni_summary)

        enriched_summary = (
            f"[Contexte : Liste exhaustive de tous les {status_label}s de la promotion {promo} "
            f"du Master ESA. Utile pour les questions du type 'liste des étudiants', "
            f"'noms des diplômés', 'qui était dans la promotion {promo}'.]\n\n"
            f"{original_summary}"
        )

        chunks.append({
            "id": f"{file_slug}__liste_complete",
            "text": enriched_summary,
            "original_text": original_summary,
            "metadata": {
                "source_file": filename,
                "doc_title": doc_title,
                "section": f"Liste complète promotion {promo}",
                "subsection": "",
                "approx_tokens": estimate_tokens(enriched_summary),
                "url": "",
                "access": access,
                "type": "alumni_summary",  # type différent pour le filtrage
                "promotion": promo,
                "nom": "",
                "prenom": "",
                "entreprise": "",
                "poste": "",
            }
        })

    return chunks


def chunk_standard_file(filepath: str) -> list[dict]:
    filename = Path(filepath).name
    file_slug = slugify(Path(filepath).stem)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    title_match = re.match(r"^# (.+)", content, re.MULTILINE)
    doc_title = title_match.group(1).strip() if title_match else filename
    source_match = re.search(r"Sources?\s*:\s*\[?([^\]\n]+)", content)
    url = source_match.group(1).strip() if source_match else ""
    access = detect_access_flag(content)

    raw_chunks = []
    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    has_sections = any(s.strip().startswith("## ") for s in sections)

    if not has_sections:
        raw_chunks.append({"section": "", "subsection": "", "text": content.strip(), "id_suffix": ""})
    else:
        for section in sections:
            section = section.strip()
            if not section or (section.startswith("# ") and not section.startswith("## ")):
                continue
            section_match = re.match(r"^## (.+)", section)
            if not section_match:
                continue
            section_title = section_match.group(1).strip()
            subsections = re.split(r"(?=^### )", section, flags=re.MULTILINE)
            if len(subsections) <= 1:
                raw_chunks.append({
                    "section": section_title, "subsection": "",
                    "text": section.strip(), "id_suffix": slugify(section_title),
                })
            else:
                for sub in subsections:
                    sub = sub.strip()
                    if not sub:
                        continue
                    sub_match = re.match(r"^### (.+)", sub)
                    if sub_match:
                        sub_title = sub_match.group(1).strip()
                        text = f"## {section_title}\n\n{sub}"
                    else:
                        sub_title = ""
                        text = sub
                        if len(text) < 50:
                            continue
                    id_suffix = slugify(section_title)
                    if sub_title:
                        id_suffix += f"__{slugify(sub_title)}"
                    raw_chunks.append({
                        "section": section_title, "subsection": sub_title,
                        "text": text, "id_suffix": id_suffix,
                    })

    # Fusionner les chunks trop petits
    merged_raw = []
    i = 0
    while i < len(raw_chunks):
        chunk = raw_chunks[i]
        if estimate_tokens(chunk["text"]) < MIN_TOKENS and i + 1 < len(raw_chunks):
            next_chunk = raw_chunks[i + 1]
            if next_chunk["section"] == chunk["section"]:
                next_chunk["text"] = chunk["text"] + "\n\n" + next_chunk["text"]
                i += 1
                continue
        merged_raw.append(chunk)
        i += 1

    chunks = []
    for rc in merged_raw:
        original_text = rc["text"]
        section_label = rc["section"]
        if rc["subsection"]:
            section_label = f"{rc['section']} — {rc['subsection']}"
        enriched_text = enrich_chunk_text(original_text, filename, section_label)
        chunk_id = file_slug
        if rc["id_suffix"]:
            chunk_id += f"__{rc['id_suffix']}"
        chunks.append({
            "id": chunk_id,
            "text": enriched_text,
            "original_text": original_text,
            "metadata": {
                "source_file": filename, "doc_title": doc_title,
                "section": rc["section"], "subsection": rc["subsection"],
                "approx_tokens": estimate_tokens(enriched_text),
                "url": url, "access": access, "type": "general",
            }
        })

    return chunks


def chunk_markdown(filepath: str) -> list[dict]:
    filename = Path(filepath).name
    if is_alumni_file(filename):
        return chunk_alumni_file(filepath)
    # Pour les syllabus, on ajoute un chunk synthèse en plus
    chunks = chunk_standard_file(filepath)
    if is_syllabus_file(filename):
        # Vérifier si une section "Liste complète" est déjà présente dans les chunks
        # (i.e. l'utilisateur l'a écrite manuellement dans le .md, plus complète et structurée).
        # Dans ce cas, on n'ajoute PAS la génération automatique pour éviter le doublon.
        has_manual_list = any(
            "liste complete" in slugify(c["metadata"].get("section", ""))
            or "liste complète" in (c["metadata"].get("section", "") or "").lower()
            for c in chunks
        )
        if not has_manual_list:
            summary = build_syllabus_summary_chunk(filepath, chunks)
            if summary:
                chunks.append(summary)
        else:
            print(f"   ↳ section 'Liste complète' déjà présente dans le .md, pas de génération auto")
    return chunks


def process_all_files(markdown_dir: str, output_file: str):
    md_files = sorted(Path(markdown_dir).glob("*.md"))
    if not md_files:
        print(f"❌ Aucun fichier .md trouvé dans {markdown_dir}")
        return

    all_chunks = []
    print(f"{'='*60}")
    print(f"CHUNKING (v4 enrichi) — Base de connaissances Master ESA")
    print(f"{'='*60}")
    print(f"Dossier source : {markdown_dir}")
    print(f"Fichiers trouvés : {len(md_files)}\n")

    for md_file in md_files:
        chunks = chunk_markdown(str(md_file))
        all_chunks.extend(chunks)
        total_tokens = sum(c["metadata"]["approx_tokens"] for c in chunks)
        is_alumni = is_alumni_file(md_file.name)
        prefix = "👥" if is_alumni else "📄"
        print(f"{prefix} {md_file.name} → {len(chunks)} chunks (~{total_tokens} tokens)")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    nb_logged = sum(1 for c in all_chunks if c["metadata"]["access"] == "logged_in")
    nb_public = len(all_chunks) - nb_logged
    nb_alumni = sum(1 for c in all_chunks if c["metadata"].get("type") == "alumni")
    nb_general = len(all_chunks) - nb_alumni

    print(f"\n{'='*60}")
    print(f"✅ TERMINÉ")
    print(f"   Chunks totaux : {len(all_chunks)} ({nb_general} généraux + {nb_alumni} alumni)")
    print(f"   Accès : {nb_public} publics + {nb_logged} connectés 🔒")
    print(f"   Sauvegardé : {output_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    process_all_files(MARKDOWN_DIR, OUTPUT_FILE)
