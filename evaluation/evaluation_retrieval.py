import os
import json
import time
import math
from pathlib import Path

import sys
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

os.environ["ANONYMIZED_TELEMETRY"] = "False"

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from retrieval_core import (
    EMBEDDING_MODEL,
    build_embedding_kwargs,
    hybrid_search,
    detect_document_filter,
)

from evaluation.evaluator_utils import semantic_similarity

# =========================================================
# CONFIG
# =========================================================
VECTOR_DB_DIR = ROOT_DIR / "vectordb"
COLLECTION_NAME = "dokumen_kewarganegaraan"

OUTPUT_DIR = Path("evaluation_results")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "retrieval_manual_results.json"

# =========================================================
# LOAD DATASET (Murni Manual 50 Soal)
# =========================================================
from dataset_test.manual_test import MANUAL_TEST_SET
TEST_SET = MANUAL_TEST_SET

# =========================================================
# LOAD EMBEDDING & VECTOR DB
# =========================================================
embedding_model = HuggingFaceEmbeddings(**build_embedding_kwargs())
db = Chroma(
    persist_directory=str(VECTOR_DB_DIR),
    embedding_function=embedding_model,
    collection_name=COLLECTION_NAME
)

# =========================================================
# EVALUATION STEPWISE K
# =========================================================
K_VALUES = [1, 3, 5, 10]
stepwise_summaries = {}

# Peringatan: gunakan threshold yang ketat agar hasil lebih realistis
SIM_THRESHOLD = 0.75

for k_val in K_VALUES:
    print("\n" + "=" * 60)
    print(f"MENGEVALUASI RETRIEVAL UNTUK K = {k_val}")
    print("=" * 60)
    
    hr1_all = []
    mrr_all = []
    ndcg_all = []
    precision_all = []
    recall_all = []
    sim_all = []
    
    for item in TEST_SET:
        query = item["question"]
        expected_answer = item["answer"]
        search_filter = detect_document_filter(query)
        
        start = time.time()
        # Retrieval dengan K dinamis
        results = hybrid_search(
            db=db,
            query=query,
            k=k_val,
            search_filter=search_filter
        )
        latency = time.time() - start
        
        top_doc = results[0][0].page_content if results else ""
        sim = semantic_similarity(embedding_model, expected_answer, top_doc)
        
        # Hit@1
        hr1 = 1 if sim >= SIM_THRESHOLD else 0
        
        # MRR
        mrr = 0
        for rank, (doc, score) in enumerate(results, start=1):
            candidate_sim = semantic_similarity(embedding_model, expected_answer, doc.page_content)
            if candidate_sim >= SIM_THRESHOLD:
                mrr = 1 / rank
                break
                
        # Precision@K & Recall@K
        relevant_count = 0
        for doc, score in results:
            candidate_sim = semantic_similarity(embedding_model, expected_answer, doc.page_content)
            if candidate_sim >= SIM_THRESHOLD:
                relevant_count += 1
        
        precision_k = relevant_count / k_val
        recall_k = 1 if relevant_count > 0 else 0
        
        # NDCG@K
        relevance_scores = []
        for doc, score in results:
            candidate_sim = semantic_similarity(embedding_model, expected_answer, doc.page_content)
            relevance_scores.append(candidate_sim)
            
        dcg_k = sum(rel / math.log2(rank + 1) for rank, rel in enumerate(relevance_scores, start=1))
        ideal_scores = sorted(relevance_scores, reverse=True)
        idcg_k = sum(rel / math.log2(rank + 1) for rank, rel in enumerate(ideal_scores, start=1))
        ndcg_k = dcg_k / idcg_k if idcg_k > 0 else 0.0
        
        hr1_all.append(hr1)
        mrr_all.append(mrr)
        ndcg_all.append(ndcg_k)
        precision_all.append(precision_k)
        recall_all.append(recall_k)
        sim_all.append(sim)
        
    # Hitung rata-rata metrik untuk K saat ini
    n_items = len(TEST_SET)
    avg_p = sum(precision_all) / n_items
    avg_r = sum(recall_all) / n_items
    
    # Hitung F1-Score Retrieval
    f1_retrieval = (2 * avg_p * avg_r) / (avg_p + avg_r) if (avg_p + avg_r) > 0 else 0.0
    
    stepwise_summaries[f"K={k_val}"] = {
        "avg_hit@1": round(sum(hr1_all) / n_items, 4),
        "avg_mrr": round(sum(mrr_all) / n_items, 4),
        "avg_ndcg@K": round(sum(ndcg_all) / n_items, 4),
        "avg_precision@K": round(avg_p, 4),
        "avg_recall@K": round(avg_r, 4),
        "f1_score_retrieval": round(f1_retrieval, 4),
        "avg_similarity": round(sum(sim_all) / n_items, 4)
    }

# =========================================================
# CETAK HASIL AKHIR STEPWISE K
# =========================================================
print("\n" + "=" * 80)
print("RINGKASAN EVALUASI RETRIEVAL STEPWISE K")
print("=" * 80)
for k_key, metrics in stepwise_summaries.items():
    print(f"\n--- Konfigurasi {k_key} ---")
    for met_name, met_val in metrics.items():
        print(f"  {met_name:<22}: {met_val}")

# Simpan hasil
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(stepwise_summaries, f, ensure_ascii=False, indent=2)
print(f"\nHasil perbandingan stepwise K disimpan ke: {OUTPUT_FILE}")