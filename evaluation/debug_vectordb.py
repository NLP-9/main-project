"""
debug_vectordb.py
Jalankan di root folder project: python debug_vectordb.py
"""

from pathlib import Path
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb

VECTOR_DB_DIR = Path("vectordb")
COLLECTION_NAME = "dokumen_kewarganegaraan"
LEGACY_COLLECTION_NAME = "langchain"

print("=" * 60)
print("DEBUG VECTOR DATABASE - SmartJuri-AI")
print("=" * 60)

# 1. Cek folder ada atau tidak
if not VECTOR_DB_DIR.exists():
    print("\n[ERROR] Folder vectordb/ tidak ditemukan!")
    print("  Jalankan: python ingest.py")
    exit(1)
print(f"\n[OK] Folder vectordb/ ditemukan di: {VECTOR_DB_DIR.resolve()}")

# 2. Cek ukuran folder
total_size = sum(f.stat().st_size for f in VECTOR_DB_DIR.rglob("*") if f.is_file())
print(f"[INFO] Ukuran total vectordb/: {total_size / 1024 / 1024:.2f} MB")
if total_size < 1_000_000:
    print("[WARN] Ukuran sangat kecil (<1 MB) - mungkin database kosong atau corrupt")

# 3. List semua collection
print("\n" + "-" * 40)
print("DAFTAR COLLECTIONS:")
client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
collections = client.list_collections()
if not collections:
    print("[ERROR] Tidak ada collection sama sekali di vectordb/")
    print("  Jalankan: python ingest.py")
    exit(1)

for col in collections:
    c = client.get_collection(col.name)
    print(f"  - {col.name}: {c.count()} chunk")

# 4. Pilih collection aktif
active_name = None
for name in [COLLECTION_NAME, LEGACY_COLLECTION_NAME]:
    try:
        c = client.get_collection(name)
        if c.count() > 0:
            active_name = name
            break
    except Exception:
        pass

if not active_name:
    print("\n[ERROR] Semua collection kosong (0 chunk)")
    print("  Jalankan: python ingest.py")
    exit(1)

collection = client.get_collection(active_name)
total_chunks = collection.count()
print(f"\n[OK] Collection aktif: '{active_name}' ({total_chunks} chunk)")

# 5. Ambil 5 sample chunk - cek isi & metadata
print("\n" + "-" * 40)
print("SAMPLE 5 CHUNK PERTAMA:")
sample = collection.get(limit=5, include=["documents", "metadatas"])

empty_count = 0
for i, (doc, meta) in enumerate(zip(sample["documents"], sample["metadatas"])):
    doc_preview = doc.strip() if doc else ""
    is_empty = len(doc_preview) == 0 or doc_preview in [".", "", " "]
    if is_empty:
        empty_count += 1
    print(f"\n  [Chunk {i+1}]")
    print(f"    Metadata : {meta}")
    print(f"    Isi      : {repr(doc_preview[:120]) if doc_preview else '[KOSONG]'}")
    print(f"    Status   : {'!! KOSONG/TITIK' if is_empty else 'OK Ada isi'}")

# 6. Estimasi chunk kosong dari sampling 50
print("\n" + "-" * 40)
print("CEK SAMPLE 50 CHUNK (ESTIMASI KERUSAKAN):")
sample_50 = collection.get(limit=50, include=["documents"])
kosong = sum(
    1 for d in sample_50["documents"]
    if not d or d.strip() in [".", "", " "]
)
print(f"  Dari 50 chunk: {kosong} kosong/berisi titik ({kosong/50*100:.0f}%)")
if kosong > 25:
    print("  [WARN] >50% chunk kosong - proses ingest kemungkinan bermasalah")
elif kosong > 0:
    print("  [WARN] Ada chunk kosong - mungkin sebagian dokumen gagal di-parse")
else:
    print("  [OK] Semua sampel berisi teks - embedding seharusnya valid")

# 7. Cek variasi document_type
print("\n" + "-" * 40)
print("VARIASI METADATA (document_type):")
sample_meta = collection.get(limit=200, include=["metadatas"])
doc_types = {}
for m in sample_meta["metadatas"]:
    dt = m.get("document_type", "UNKNOWN")
    doc_types[dt] = doc_types.get(dt, 0) + 1
for dt, count in sorted(doc_types.items()):
    print(f"  - {dt}: {count} (dari 200 sample)")

# 8. Uji query teks langsung ke collection (tanpa embedding)
print("\n" + "-" * 40)
print("UJI QUERY TEKS (tanpa embedding, pakai where filter):")
try:
    res = collection.get(
        where={"document_type": "UUD"},
        limit=3,
        include=["documents", "metadatas"]
    )
    print(f"  Ditemukan {len(res['documents'])} chunk ber-type UUD")
    for i, (d, m) in enumerate(zip(res["documents"], res["metadatas"])):
        preview = d.strip()[:100] if d else "[KOSONG]"
        print(f"  [{i+1}] hal {m.get('page_number')} | {repr(preview)}")
except Exception as e:
    print(f"  [ERROR] {e}")

print("\n" + "=" * 60)
print("RINGKASAN DIAGNOSIS:")
print(f"  Total chunk   : {total_chunks}")
print(f"  Chunk kosong  : ~{kosong/50*100:.0f}% (dari 50 sampel)")
print(f"  Doc types     : {list(doc_types.keys())}")
if kosong > 25:
    print("\n  KESIMPULAN: Vector DB bermasalah - perlu ingest ulang")
    print("  Coba jalankan: python ingest.py")
else:
    print("\n  KESIMPULAN: Vector DB terlihat OK - lanjut ke evaluasi metrik")
print("=" * 60)