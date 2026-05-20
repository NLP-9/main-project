"""
evaluate_retrieval.py  —  Evaluasi Metrik Kuantitatif Retrieval SmartJuri-AI
Anggota 3: AI Evaluator & Technical Writer

Metrik yang dihitung:
  - Hit Rate @1, @3, @5
  - MRR (Mean Reciprocal Rank)
  - NDCG@3, NDCG@5
  - Average Semantic Similarity (cosine) antara context vs kunci jawaban

Jalankan: python evaluate_retrieval.py
Output  : hasil cetak di terminal + file evaluate_results.json
"""

import os
import json
import math
import time
from pathlib import Path

os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from sklearn.metrics.pairwise import cosine_similarity

# ==============================================================
# KONFIGURASI
# ==============================================================
VECTOR_DB_DIR     = Path("vectordb")
COLLECTION_NAME   = "dokumen_kewarganegaraan"
LEGACY_COLLECTION_NAME = "langchain"
EMBEDDING_MODEL   = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TOP_K             = 5       # ambil top-5, lalu hitung @1/@3/@5
OUTPUT_FILE       = Path("evaluate_results.json")

# ==============================================================
# TEST SET
# Setiap entry: pertanyaan + kunci jawaban + document_type yang
# diharapkan muncul di hasil (sebagai "ground truth" relevansi).
# Kamu bisa tambah/ubah soal ini sesuai materi LCC Empat Pilar.
# ==============================================================
TEST_SET = [
    {
        "id": 1,
        "pertanyaan": "Siapakah yang berwenang mengubah dan menetapkan Undang-Undang Dasar?",
        "kunci_jawaban": "Majelis Permusyawaratan Rakyat (MPR) berwenang mengubah dan menetapkan Undang-Undang Dasar.",
        "expected_doc_type": "UUD",
    },
    {
        "id": 2,
        "pertanyaan": "Berapa jumlah anggota Dewan Perwakilan Rakyat yang ditetapkan dalam UUD 1945?",
        "kunci_jawaban": "Jumlah anggota DPR diatur oleh undang-undang.",
        "expected_doc_type": "UUD",
    },
    {
        "id": 3,
        "pertanyaan": "Apa yang dimaksud dengan Pancasila sebagai dasar negara?",
        "kunci_jawaban": "Pancasila adalah dasar negara Republik Indonesia yang menjadi landasan penyelenggaraan negara.",
        "expected_doc_type": "EMPAT_PILAR",
    },
    {
        "id": 4,
        "pertanyaan": "Sebutkan sila-sila dalam Pancasila!",
        "kunci_jawaban": "Ketuhanan Yang Maha Esa, Kemanusiaan yang adil dan beradab, Persatuan Indonesia, Kerakyatan yang dipimpin oleh hikmat kebijaksanaan dalam permusyawaratan perwakilan, Keadilan sosial bagi seluruh rakyat Indonesia.",
        "expected_doc_type": "EMPAT_PILAR",
    },
    {
        "id": 5,
        "pertanyaan": "Apa isi Pasal 1 ayat 1 UUD 1945?",
        "kunci_jawaban": "Negara Indonesia ialah Negara Kesatuan yang berbentuk Republik.",
        "expected_doc_type": "UUD",
    },
    {
        "id": 6,
        "pertanyaan": "Apa yang dimaksud Bhinneka Tunggal Ika?",
        "kunci_jawaban": "Bhinneka Tunggal Ika berarti berbeda-beda tetapi tetap satu, merupakan semboyan negara Indonesia.",
        "expected_doc_type": "EMPAT_PILAR",
    },
    {
        "id": 7,
        "pertanyaan": "Bagaimana cara mengubah pasal-pasal UUD 1945?",
        "kunci_jawaban": "Usul perubahan pasal-pasal UUD dapat diagendakan dalam sidang MPR jika diajukan oleh sekurang-kurangnya 1/3 dari jumlah anggota MPR.",
        "expected_doc_type": "UUD",
    },
    {
        "id": 8,
        "pertanyaan": "Apa fungsi NKRI sebagai bentuk negara menurut UUD 1945?",
        "kunci_jawaban": "Negara Kesatuan Republik Indonesia merupakan negara yang tidak dapat dibagi-bagi wilayahnya.",
        "expected_doc_type": "UUD",
    },
    {
        "id": 9,
        "pertanyaan": "Jelaskan makna Pembukaan UUD 1945 alinea keempat!",
        "kunci_jawaban": "Alinea keempat memuat tujuan negara, bentuk negara, dan dasar negara yaitu Pancasila.",
        "expected_doc_type": "EMPAT_PILAR",
    },
    {
        "id": 10,
        "pertanyaan": "Apa kewajiban negara terhadap fakir miskin dan anak terlantar menurut UUD 1945?",
        "kunci_jawaban": "Fakir miskin dan anak-anak yang terlantar dipelihara oleh negara sesuai Pasal 34 UUD 1945.",
        "expected_doc_type": "UUD",
    },
]

# ==============================================================
# HELPER: resolve collection
# ==============================================================
def resolve_collection_name():
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    collections = [c.name for c in client.list_collections()]
    for name in [COLLECTION_NAME, LEGACY_COLLECTION_NAME]:
        if name in collections:
            c = client.get_collection(name)
            if c.count() > 0:
                return name
    raise ValueError("Vector DB kosong. Jalankan ingest.py terlebih dahulu.")

# ==============================================================
# METRIK HELPERS
# ==============================================================
def hit_rate(results, expected_doc_type, k):
    """Apakah ada hasil yang doc_type-nya sesuai di top-k?"""
    for doc, _ in results[:k]:
        if doc.metadata.get("document_type") == expected_doc_type:
            return 1
    return 0

def reciprocal_rank(results, expected_doc_type):
    """1/rank dari hasil pertama yang relevan."""
    for rank, (doc, _) in enumerate(results, start=1):
        if doc.metadata.get("document_type") == expected_doc_type:
            return 1.0 / rank
    return 0.0

def ndcg(results, expected_doc_type, k):
    """NDCG@k: relevan = doc_type sesuai (binary relevance)."""
    gains = []
    for doc, _ in results[:k]:
        gains.append(1 if doc.metadata.get("document_type") == expected_doc_type else 0)
    dcg  = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    # ideal DCG: semua k hasil relevan
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(k, sum(gains) + 1)))
    return dcg / idcg if idcg > 0 else 0.0

def semantic_similarity(embedding_fn, text_a, text_b):
    """Cosine similarity antara dua teks menggunakan embedding model."""
    vec_a = embedding_fn.embed_query(text_a)
    vec_b = embedding_fn.embed_query(text_b)
    return float(cosine_similarity([vec_a], [vec_b])[0][0])

# ==============================================================
# MAIN
# ==============================================================
def main():
    print("=" * 60)
    print("EVALUASI RETRIEVAL - SmartJuri-AI")
    print(f"Model : {EMBEDDING_MODEL}")
    print(f"Top-K : {TOP_K}")
    print(f"Jumlah soal: {len(TEST_SET)}")
    print("=" * 60)

    # Load embedding model
    print("\nMemuat embedding model...")
    embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # Load vector DB
    print("Memuat vector database...")
    active_col = resolve_collection_name()
    db = Chroma(
        persist_directory=str(VECTOR_DB_DIR),
        embedding_function=embedder,
        collection_name=active_col,
    )
    print(f"Collection: {active_col}\n")

    # Wadah akumulasi metrik
    hr1_list, hr3_list, hr5_list = [], [], []
    mrr_list = []
    ndcg3_list, ndcg5_list = [], []
    sim_list = []

    per_query_results = []

    for item in TEST_SET:
        qid   = item["id"]
        query = item["pertanyaan"]
        kunci = item["kunci_jawaban"]
        exp   = item["expected_doc_type"]

        print(f"[{qid:02d}] {query[:70]}...")

        start = time.time()
        results = db.similarity_search_with_score(query=query, k=TOP_K)
        elapsed = time.time() - start

        # Hitung metrik retrieval
        hr1 = hit_rate(results, exp, k=1)
        hr3 = hit_rate(results, exp, k=3)
        hr5 = hit_rate(results, exp, k=5)
        mrr = reciprocal_rank(results, exp)
        n3  = ndcg(results, exp, k=3)
        n5  = ndcg(results, exp, k=5)

        # Hitung semantic similarity: kunci jawaban vs konten chunk #1
        top_content = results[0][0].page_content if results else ""
        sim = semantic_similarity(embedder, kunci, top_content)

        hr1_list.append(hr1);  hr3_list.append(hr3);  hr5_list.append(hr5)
        mrr_list.append(mrr)
        ndcg3_list.append(n3); ndcg5_list.append(n5)
        sim_list.append(sim)

        print(f"      Hit@1={hr1} Hit@3={hr3} Hit@5={hr5} | MRR={mrr:.3f} | "
              f"NDCG@3={n3:.3f} NDCG@5={n5:.3f} | Sim={sim:.3f} | {elapsed:.2f}s")

        # Simpan detail
        per_query_results.append({
            "id": qid,
            "pertanyaan": query,
            "kunci_jawaban": kunci,
            "expected_doc_type": exp,
            "latency_s": round(elapsed, 3),
            "hit@1": hr1, "hit@3": hr3, "hit@5": hr5,
            "mrr": round(mrr, 4),
            "ndcg@3": round(n3, 4),
            "ndcg@5": round(n5, 4),
            "semantic_similarity_top1": round(sim, 4),
            "top_results": [
                {
                    "rank": i + 1,
                    "score_l2": round(score, 4),
                    "doc_type": doc.metadata.get("document_type"),
                    "source_file": doc.metadata.get("source_file"),
                    "page": doc.metadata.get("page_number"),
                    "content_preview": doc.page_content[:200],
                }
                for i, (doc, score) in enumerate(results)
            ],
        })

    # ===========================================================
    # RINGKASAN AGREGAT
    # ===========================================================
    summary = {
        "model": EMBEDDING_MODEL,
        "top_k": TOP_K,
        "n_queries": len(TEST_SET),
        "avg_hit_rate@1":  round(sum(hr1_list)  / len(hr1_list),  4),
        "avg_hit_rate@3":  round(sum(hr3_list)  / len(hr3_list),  4),
        "avg_hit_rate@5":  round(sum(hr5_list)  / len(hr5_list),  4),
        "avg_mrr":         round(sum(mrr_list)  / len(mrr_list),  4),
        "avg_ndcg@3":      round(sum(ndcg3_list)/ len(ndcg3_list),4),
        "avg_ndcg@5":      round(sum(ndcg5_list)/ len(ndcg5_list),4),
        "avg_semantic_similarity": round(sum(sim_list) / len(sim_list), 4),
    }

    print("\n" + "=" * 60)
    print("RINGKASAN METRIK EVALUASI")
    print("=" * 60)
    print(f"  Hit Rate @1  : {summary['avg_hit_rate@1']:.4f}  ({summary['avg_hit_rate@1']*100:.1f}%)")
    print(f"  Hit Rate @3  : {summary['avg_hit_rate@3']:.4f}  ({summary['avg_hit_rate@3']*100:.1f}%)")
    print(f"  Hit Rate @5  : {summary['avg_hit_rate@5']:.4f}  ({summary['avg_hit_rate@5']*100:.1f}%)")
    print(f"  MRR          : {summary['avg_mrr']:.4f}")
    print(f"  NDCG@3       : {summary['avg_ndcg@3']:.4f}")
    print(f"  NDCG@5       : {summary['avg_ndcg@5']:.4f}")
    print(f"  Sem. Similarity: {summary['avg_semantic_similarity']:.4f}")
    print("=" * 60)

    # Interpretasi
    print("\nINTERPRETASI:")
    hr3 = summary["avg_hit_rate@3"]
    mrr = summary["avg_mrr"]
    sim = summary["avg_semantic_similarity"]

    if hr3 >= 0.8 and mrr >= 0.6:
        verdict = "BAIK - Model saat ini sudah layak digunakan"
    elif hr3 >= 0.6 or mrr >= 0.4:
        verdict = "CUKUP - Pertimbangkan fine-tuning atau ganti model"
    else:
        verdict = "KURANG - Sangat disarankan mengganti model embedding"

    print(f"  Verdict: {verdict}")
    if sim < 0.4:
        print("  Catatan: Semantic Similarity rendah (<0.4) - context yang diambil")
        print("           kurang mirip dengan kunci jawaban. Coba model:")
        print("           - indobenchmark/indobert-base-p1 (lebih kuat untuk Bahasa Indonesia)")
        print("           - LazarusNLP/IndoNanoBeIR-MiniLM-v2 (ringan, khusus Indonesia)")
    elif sim >= 0.6:
        print("  Catatan: Semantic Similarity bagus (>=0.6) - context relevan")

    # Simpan ke JSON
    output = {"summary": summary, "per_query": per_query_results}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nHasil detail tersimpan di: {OUTPUT_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    main()