from pathlib import Path

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ==================================================
# KONFIGURASI
# ==================================================

VECTOR_DB_DIR = Path("vectordb")

COLLECTION_NAME = "dokumen_kewarganegaraan"

LEGACY_COLLECTION_NAME = "langchain"

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

TOP_K = 3

def detect_document_filter(query):
    normalized_query = query.lower()

    if "uud" in normalized_query:
        return {"document_type": "UUD"}

    if "tap" in normalized_query:
        return {"document_type": "TAP_MPR"}

    if "empat pilar" in normalized_query or "pilar" in normalized_query:
        return {"document_type": "EMPAT_PILAR"}

    return None

def preview_collection():
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    collection = client.get_collection(resolve_collection_name())
    return collection.count()

def resolve_collection_name():
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    collections = client.list_collections()
    collection_names = [collection.name for collection in collections]

    if COLLECTION_NAME in collection_names:
        preferred_collection = client.get_collection(COLLECTION_NAME)

        if preferred_collection.count() > 0:
            return COLLECTION_NAME

    if LEGACY_COLLECTION_NAME in collection_names:
        legacy_collection = client.get_collection(LEGACY_COLLECTION_NAME)

        if legacy_collection.count() > 0:
            return LEGACY_COLLECTION_NAME

    raise ValueError(
        "Vector database belum berisi data. Jalankan ingest.py terlebih dahulu."
    )

# ==================================================
# LOAD EMBEDDING MODEL
# ==================================================

print("=" * 60)
print("MEMUAT MODEL EMBEDDING")
print("=" * 60)

embedding_model = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL
)

print(f"\nModel digunakan: {EMBEDDING_MODEL}")

# ==================================================
# LOAD VECTOR DATABASE
# ==================================================

print("\n" + "=" * 60)
print("MEMUAT VECTOR DATABASE")
print("=" * 60)

if not VECTOR_DB_DIR.exists():
    raise FileNotFoundError(
        "Folder vectordb belum ada. Jalankan ingest.py terlebih dahulu."
    )

active_collection_name = resolve_collection_name()

db = Chroma(
    persist_directory=str(VECTOR_DB_DIR),
    embedding_function=embedding_model,
    collection_name=active_collection_name
)

print("\nVector Database berhasil dimuat!")
print(f"Collection name: {active_collection_name}")
print(f"Jumlah chunk di database: {preview_collection()}")

# ==================================================
# QUERY LOOP
# ==================================================

while True:

    print("\n" + "=" * 60)

    query = input("Masukkan pertanyaan (ketik exit untuk keluar): ").strip()

    if query.lower() == "exit":

        print("\nProgram selesai.")
        break

    if not query:

        print("Pertanyaan tidak boleh kosong.")
        continue

    print("\nMENCARI CONTEXT PALING RELEVAN...\n")

    # ==================================================
    # OPTIONAL FILTER DOKUMEN
    # ==================================================

    search_filter = detect_document_filter(query)

    if search_filter:
        print(f"Filter dokumen aktif: {search_filter['document_type']}\n")

    # ==================================================
    # RETRIEVAL
    # ==================================================

    results = db.similarity_search_with_score(
        query=query,
        k=TOP_K,
        filter=search_filter
    )

    print(f"Jumlah hasil ditemukan: {len(results)}\n")

    # ==================================================
    # TAMPILKAN HASIL
    # ==================================================

    for i, (doc, score) in enumerate(results):

        print("=" * 60)
        print(f"HASIL {i+1}")
        print("=" * 60)

        print(f"\nSCORE : {score}")

        print("\nSUMBER FILE:")
        print(doc.metadata.get("source_file"))

        print("\nJENIS DOKUMEN:")
        print(doc.metadata.get("document_type"))

        print("\nHALAMAN:")
        print(doc.metadata.get("page_number"))

        print("\nCHUNK ID:")
        print(doc.metadata.get("chunk_id"))

        print("\nISI CONTEXT:")
        print(doc.page_content[:1500])

        print("\n")
