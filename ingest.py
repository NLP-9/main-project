import os
import re
from pathlib import Path

os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from retrieval_core import (
    EMBEDDING_MODEL,
    build_embedding_kwargs,
    format_document_for_embedding,
)

# ==================================================
# KONFIGURASI PROJECT
# ==================================================

DATA_FOLDER = Path("Data")

DATA_SUBFOLDERS = [
    "Contoh Soal",
    "Empat Pilar MPR RI",
    "TAP MPR",
    "UUD",
]

VECTOR_DB_DIR = Path("vectordb")

COLLECTION_NAME = "dokumen_kewarganegaraan"

# Untuk dokumen hukum/kewarganegaraan, chunk jangan terlalu kecil
CHUNK_SIZE = 900
CHUNK_OVERLAP = 180

BATCH_SIZE = 2000


# ==================================================
# PREPROCESSING RINGAN
# ==================================================

def preprocess_text(text: str) -> str:
    """
    Preprocessing ringan untuk PDF.
    Tidak dibuat terlalu agresif agar konteks pasal, kalimat,
    dan istilah hukum tetap aman.
    """

    if text is None:
        return ""

    # Hapus karakter rusak ringan dari PDF
    text = text.replace("�", "")
    text = text.replace("Â", "")
    text = text.replace("â", "")
    text = text.replace("™", "")
    text = text.replace("œ", "")

    # Rapikan whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_document_type(file_name: str, folder_name: str) -> str:
    normalized_name = file_name.lower()
    normalized_folder = folder_name.lower()

    if "contoh soal" in normalized_folder:
        return "CONTOH_SOAL"

    if "uud" in normalized_folder or "uud" in normalized_name:
        return "UUD"

    if "tap mpr" in normalized_folder or "tap" in normalized_name:
        return "TAP_MPR"

    return "EMPAT_PILAR"


def build_context_prefix(metadata: dict) -> str:
    return (
        f"jenis dokumen: {metadata.get('document_type', '')}. "
        f"sumber: {metadata.get('source_folder', '')} / {metadata.get('source_file', '')}. "
        f"halaman: {metadata.get('page_number', '')}. "
    )


# ==================================================
# LOAD DOKUMEN PDF
# ==================================================

print("=" * 60)
print("MEMBACA DOKUMEN PDF")
print("=" * 60)

all_docs = []

if not DATA_FOLDER.exists():
    raise FileNotFoundError(f"Folder data tidak ditemukan: {DATA_FOLDER}")

data_folders = [DATA_FOLDER / folder_name for folder_name in DATA_SUBFOLDERS]

missing_folders = [
    folder
    for folder in data_folders
    if not folder.exists()
]

if missing_folders:
    missing_folder_names = ", ".join(str(folder) for folder in missing_folders)
    raise FileNotFoundError(f"Folder data tidak ditemukan: {missing_folder_names}")

pdf_files = sorted(
    file_path
    for folder in data_folders
    for file_path in folder.rglob("*.pdf")
)

if not pdf_files:
    folder_names = ", ".join(str(folder) for folder in data_folders)
    raise FileNotFoundError(f"Tidak ada file PDF di folder: {folder_names}")

for file_path in pdf_files:
    file_name = file_path.name
    source_folder = file_path.parent.name

    print(f"\nLoading file: {source_folder}/{file_name}")

    try:
        loader = PyPDFLoader(str(file_path))
        docs = loader.load()

        for doc in docs:
            clean_text = preprocess_text(doc.page_content)

            doc.page_content = clean_text

            doc.metadata["source_file"] = file_name
            doc.metadata["source_folder"] = source_folder
            doc.metadata["page_number"] = doc.metadata.get("page", 0) + 1
            doc.metadata["document_type"] = get_document_type(
                file_name=file_name,
                folder_name=source_folder,
            )

        all_docs.extend(docs)

        print(f"Berhasil load {len(docs)} halaman")

    except Exception as e:
        print(f"Gagal load file: {file_name}")
        print(e)

print("\n" + "=" * 60)
print(f"TOTAL HALAMAN: {len(all_docs)}")
print("=" * 60)

if not all_docs:
    raise ValueError("Tidak ada dokumen yang berhasil dimuat.")


# ==================================================
# TEXT CHUNKING
# ==================================================

print("\n" + "=" * 60)
print("MELAKUKAN TEXT CHUNKING")
print("=" * 60)

text_splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", ". ", ".", " "],
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)

chunks = text_splitter.split_documents(all_docs)

if not chunks:
    raise ValueError("Tidak ada chunk yang berhasil dibuat. Cek isi file PDF.")

for i, chunk in enumerate(chunks, start=1):
    chunk.metadata["chunk_id"] = i

    context_prefix = build_context_prefix(chunk.metadata)

    chunk_text_with_context = f"{context_prefix}{chunk.page_content}"

    # Penting:
    # Jika pakai E5, setiap chunk akan otomatis diawali 'passage:'
    chunk.page_content = format_document_for_embedding(chunk_text_with_context)

    chunk.metadata["chunk_size"] = len(chunk.page_content)

print(f"\nTotal chunks berhasil dibuat: {len(chunks)}")


# ==================================================
# PREVIEW CHUNK
# ==================================================

print("\n" + "=" * 60)
print("CONTOH CHUNK PERTAMA")
print("=" * 60)

print(chunks[0].page_content[:1200])


# ==================================================
# LOAD EMBEDDING MODEL
# ==================================================

print("\n" + "=" * 60)
print("MEMUAT MODEL EMBEDDING")
print("=" * 60)

embedding_model = HuggingFaceEmbeddings(**build_embedding_kwargs())

print(f"\nModel digunakan: {EMBEDDING_MODEL}")


# ==================================================
# MEMBUAT VECTOR DATABASE
# ==================================================

print("\n" + "=" * 60)
print("MEMBUAT VECTOR DATABASE")
print("=" * 60)

client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

existing_collections = [
    collection.name
    for collection in client.list_collections()
]

if COLLECTION_NAME in existing_collections:
    print(f"\nCollection lama ditemukan: {COLLECTION_NAME}")
    print("Menghapus collection lama agar hasil ingest tidak duplikat.")
    client.delete_collection(COLLECTION_NAME)

vectorstore = Chroma(
    persist_directory=str(VECTOR_DB_DIR),
    embedding_function=embedding_model,
    collection_name=COLLECTION_NAME,
)

total = len(chunks)

print(
    f"\nMenambahkan {total} chunk ke collection "
    f"dalam batch berukuran {BATCH_SIZE}..."
)

for start in range(0, total, BATCH_SIZE):
    end = min(start + BATCH_SIZE, total)
    batch = chunks[start:end]

    print(
        f"  Menambahkan batch {start // BATCH_SIZE + 1}: "
        f"indeks {start}-{end - 1} "
        f"(jumlah {len(batch)})"
    )

    vectorstore.add_documents(batch)

try:
    vectorstore.persist()
except Exception:
    pass

print("\nVector Database berhasil dibuat!")


# ==================================================
# RINGKASAN AKHIR
# ==================================================

print("\n" + "=" * 60)
print("RINGKASAN PROSES")
print("=" * 60)

print(f"Jumlah file PDF   : {len(pdf_files)}")
print(f"Jumlah halaman    : {len(all_docs)}")
print(f"Jumlah chunks     : {len(chunks)}")
print(f"Chunk size        : {CHUNK_SIZE}")
print(f"Chunk overlap     : {CHUNK_OVERLAP}")
print(f"Model embedding   : {EMBEDDING_MODEL}")
print(f"Collection name   : {COLLECTION_NAME}")
print(f"Lokasi Vector DB  : {VECTOR_DB_DIR}")

print("\nINGEST SELESAI!")