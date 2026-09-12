"""
=============================================================
Embedding & Ingestion ChromaDB v2 — modèle E5 + texte original
=============================================================
Améliorations :
- Modèle multilingual-e5-large (state-of-the-art multilingue)
- On embed le texte ENRICHI mais on stocke le texte ORIGINAL pour le LLM
- Préfixe "passage:" / "query:" requis par E5

NOTE :
- Premier lancement = téléchargement du modèle (~2 Go) — soyez patient
- Modèle plus lourd → embedding un peu plus lent (~1-2 min pour 850 chunks)
- Mais qualité de retrieval bien meilleure
"""

import json
import time
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


# === CONFIGURATION ===
CHUNKS_FILE = "./all_chunks.json"
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "master_esa"

# Modèle E5 : state-of-the-art multilingue (français inclus)
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"

BATCH_SIZE = 16  # E5 est plus lourd, batch plus petit
# ======================


def main():
    print("=" * 60)
    print("EMBEDDING & INGESTION CHROMADB v2 — Master ESA")
    print("=" * 60)

    chunks_path = Path(CHUNKS_FILE)
    if not chunks_path.exists():
        print(f"❌ Fichier introuvable : {CHUNKS_FILE}")
        print("   Lance d'abord python chunk_all.py")
        return

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"\n📂 Chunks chargés : {len(chunks)}")

    print(f"\n🧠 Chargement du modèle E5 : {EMBEDDING_MODEL}")
    print("   (téléchargement ~2 Go au premier lancement, soyez patient)")
    t0 = time.time()
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"   ✅ Modèle chargé en {time.time() - t0:.1f}s")

    # E5 demande un préfixe "passage:" pour les documents indexés
    ids = [c["id"] for c in chunks]
    # Texte ENRICHI pour l'embedding (avec préfixe E5)
    embedding_inputs = [f"passage: {c['text']}" for c in chunks]
    # Texte ORIGINAL stocké dans ChromaDB (visible par le LLM)
    documents = [c.get("original_text", c["text"]) for c in chunks]

    # Nettoyer les métadonnées (None → "")
    metadatas = []
    for c in chunks:
        clean_meta = {}
        for k, v in c["metadata"].items():
            clean_meta[k] = v if v is not None else ""
        metadatas.append(clean_meta)

    print(f"\n⚙️  Génération des embeddings (batch={BATCH_SIZE})...")
    t0 = time.time()
    embeddings = model.encode(
        embedding_inputs,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # E5 nécessite normalisation
    )
    print(f"   ✅ {len(embeddings)} embeddings générés en {time.time() - t0:.1f}s")
    print(f"   Dimension : {embeddings.shape[1]}")

    print(f"\n💾 Création de la base ChromaDB : {CHROMA_DIR}")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        client.delete_collection(name=COLLECTION_NAME)
        print(f"   (ancienne collection '{COLLECTION_NAME}' supprimée)")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": "Base de connaissances Master ESA - Université d'Orléans",
            "hnsw:space": "cosine",
        },
    )

    print(f"\n📥 Insertion dans ChromaDB...")
    collection.add(
        ids=ids,
        documents=documents,  # texte ORIGINAL (sans préfixe contextuel)
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )
    print(f"   ✅ {collection.count()} chunks insérés")

    # Test
    print(f"\n🔎 Test de retrieval — question : 'Quelles sont les matières du semestre 7 ?'")
    test_query = "query: Quelles sont les matières du semestre 7 ?"  # préfixe query: pour E5
    test_emb = model.encode([test_query], normalize_embeddings=True)
    results = collection.query(
        query_embeddings=test_emb.tolist(),
        n_results=5,
    )
    print("   Top 5 chunks les plus proches :")
    for i, (doc_id, meta, dist) in enumerate(zip(
        results["ids"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        section = meta.get("section") or "(document entier)"
        access = meta.get("access", "public")
        tag = " 🔒" if access == "logged_in" else ""
        print(f"   {i+1}. [dist={dist:.3f}]{tag} {meta['source_file']}")
        print(f"      Section : {section}")

    print(f"\n{'='*60}")
    print(f"✅ TERMINÉ")
    print(f"   Base ChromaDB : {CHROMA_DIR}")
    print(f"   Chunks indexés : {collection.count()}")
    print(f"   Modèle : {EMBEDDING_MODEL}")
    print(f"{'='*60}")
    print()
    print("PROCHAINE ÉTAPE : chainlit run app.py")


if __name__ == "__main__":
    main()
