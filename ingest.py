import re
from pathlib import Path

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ==================================================
# KONFIGURASI PROJECT
# ==================================================

# Folder PDF
DATA_FOLDER = Path("Data")
DATA_SUBFOLDERS = [
    "Contoh Soal",
    "Empat Pilar MPR RI",
    "TAP MPR",
    "UUD",
]

# Folder penyimpanan ChromaDB
VECTOR_DB_DIR = Path("vectordb")

# Nama collection agar konsisten saat ingest dan retrieval
COLLECTION_NAME = "dokumen_kewarganegaraan"

# Embedding multilingual terbaik untuk Indo
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Chunking untuk dokumen hukum
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# ==================================================
# PREPROCESSING RINGAN UNTUK RAG
# ==================================================

def preprocess_text(text):

    # lowercase
    text = text.lower()

    # hapus karakter rusak PDF ringan
    text = text.replace("�", "")
    text = text.replace("Â", "")
    text = text.replace("â", "")
    text = text.replace("™", "")
    text = text.replace("œ", "")
    text = text.replace("~", "")

    # rapikan whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def get_document_type(file_name, folder_name):
    normalized_name = file_name.lower()
    normalized_folder = folder_name.lower()

    if "contoh soal" in normalized_folder:
        return "CONTOH_SOAL"

    if "uud" in normalized_folder or "uud" in normalized_name:
        return "UUD"

    if "tap mpr" in normalized_folder or "tap" in normalized_name:
        return "TAP_MPR"

    return "EMPAT_PILAR"

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
missing_folders = [folder for folder in data_folders if not folder.exists()]

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

        # Load PDF
        loader = PyPDFLoader(str(file_path))

        docs = loader.load()

        # preprocessing + metadata
        for doc in docs:

            # preprocessing text
            doc.page_content = preprocess_text(doc.page_content)

            # metadata source file
            doc.metadata["source_file"] = file_name

            # metadata folder sumber
            doc.metadata["source_folder"] = source_folder

            # metadata nomor halaman
            doc.metadata["page_number"] = doc.metadata.get("page", 0) + 1

            # metadata jenis dokumen
            doc.metadata["document_type"] = get_document_type(file_name, source_folder)

        all_docs.extend(docs)

        print(f"Berhasil load {len(docs)} halaman")

    except Exception as e:

        print(f"Gagal load file: {file_name}")
        print(e)

print("\n" + "=" * 60)
print(f"TOTAL HALAMAN: {len(all_docs)}")
print("=" * 60)

# ==================================================
# TEXT CHUNKING
# ==================================================

print("\n" + "=" * 60)
print("MELAKUKAN TEXT CHUNKING")
print("=" * 60)

text_splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", ".", " ", ""],
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
)

chunks = text_splitter.split_documents(all_docs)

for i, chunk in enumerate(chunks, start=1):
    chunk.metadata["chunk_id"] = i
    chunk.metadata["chunk_size"] = len(chunk.page_content)

print(f"\nTotal chunks berhasil dibuat: {len(chunks)}")

if not chunks:
    raise ValueError("Tidak ada chunk yang berhasil dibuat. Cek isi file PDF.")

# ==================================================
# PREVIEW CHUNK
# ==================================================

print("\n" + "=" * 60)
print("CONTOH CHUNK PERTAMA")
print("=" * 60)

if len(chunks) > 0:

    print(chunks[0].page_content[:1200])

# ==================================================
# LOAD EMBEDDING MODEL
# ==================================================

print("\n" + "=" * 60)
print("MEMUAT MODEL EMBEDDING")
print("=" * 60)

embedding_model = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL
)

print(f"\nModel digunakan: {EMBEDDING_MODEL}")

# ==================================================
# MEMBUAT VECTOR DATABASE
# ==================================================

print("\n" + "=" * 60)
print("MEMBUAT VECTOR DATABASE")
print("=" * 60)

client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

existing_collections = [collection.name for collection in client.list_collections()]

if COLLECTION_NAME in existing_collections:
    print(f"\nCollection lama ditemukan: {COLLECTION_NAME}")
    print("Menghapus collection lama agar hasil ingest tidak duplikat.")
    client.delete_collection(COLLECTION_NAME)

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embedding_model,
    persist_directory=str(VECTOR_DB_DIR),
    collection_name=COLLECTION_NAME
)

print("\nVector Database berhasil dibuat!")

# ==================================================
# INFORMASI AKHIR
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