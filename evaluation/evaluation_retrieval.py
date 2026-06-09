import os
import json
import time
from pathlib import Path
import argparse

import sys
from pathlib import Path

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

from evaluation.evaluator_utils import (
    hit_rate,
    reciprocal_rank,
    ndcg,
    precision_at_k,
    recall_at_k,
    semantic_similarity,
)

# Removed unused auto_question_generator import

# =========================================================
# CONFIG
# =========================================================

VECTOR_DB_DIR = ROOT_DIR / "vectordb"

COLLECTION_NAME = "dokumen_kewarganegaraan"

TOP_K = 5

# =========================================================
# ARGUMENT PARSER
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--mode",
    choices=["manual", "auto"],
    default="manual"
)

args = parser.parse_args()

# =========================================================
# LOAD DATASET
# =========================================================

if args.mode == "manual":

    from dataset_test.manual_test import MANUAL_TEST_SET

    TEST_SET = MANUAL_TEST_SET

else:

    from dataset_test.auto_test import load_questions

    TEST_SET = load_questions()

# =========================================================
# OUTPUT
# =========================================================

OUTPUT_DIR = Path("evaluation_results")

OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / f"retrieval_{args.mode}_results.json"

# =========================================================
# LOAD EMBEDDING
# =========================================================

embedding_model = HuggingFaceEmbeddings(
    **build_embedding_kwargs()
)

# =========================================================
# LOAD VECTOR DB
# =========================================================

db = Chroma(
    persist_directory=str(VECTOR_DB_DIR),
    embedding_function=embedding_model,
    collection_name=COLLECTION_NAME
)

# =========================================================
# EVALUATION
# =========================================================

all_results = []

hr1_all = []
mrr_all = []
ndcg_all = []
precision_all = []
recall_all = []
sim_all = []

for item in TEST_SET:

    query = item["question"]

    expected_answer = (
        item["answer"]
        if "answer" in item
        else item["reference_answer"]
    )

    print("\n" + "=" * 60)
    print(query)

    search_filter = detect_document_filter(query)

    start = time.time()

    results = hybrid_search(
        db=db,
        query=query,
        k=TOP_K,
        search_filter=search_filter
    )

    latency = time.time() - start

    # hr1 = hit_rate(results, item["doc_type"], 1)

    # mrr = reciprocal_rank(results, item["doc_type"])

    # ndcg5 = ndcg(results, item["doc_type"], 5)

    # precision5 = precision_at_k(results, item["doc_type"], 5)

    # recall5 = recall_at_k(results, item["doc_type"], 5)

    # top_doc = results[0][0].page_content if results else ""

    # sim = semantic_similarity(
    #     embedding_model,
    #     item["answer"] if "answer" in item else item["reference_answer"],
    #     top_doc
    # )

    print("\nTOP RESULTS:")

    for i, (doc, score) in enumerate(results):

        print(f"\nRank {i+1}")
        print("Score:", score)

        print("Metadata:", doc.metadata)

        print("Content:", doc.page_content[:300])

    top_doc = results[0][0].page_content if results else ""

    sim = semantic_similarity(
        embedding_model,
        item["answer"],
        top_doc
    )

    SIM_THRESHOLD = 0.5

    # =====================================================
    # HIT@1
    # =====================================================

    hr1 = 1 if sim >= SIM_THRESHOLD else 0

    # =====================================================
    # MRR
    # =====================================================

    mrr = 0

    for rank, (doc, score) in enumerate(results, start=1):

        candidate_sim = semantic_similarity(
            embedding_model,
            expected_answer,
            doc.page_content
        )

        if candidate_sim >= SIM_THRESHOLD:

            mrr = 1 / rank
            break

    # =====================================================
    # PRECISION@K
    # =====================================================

    relevant_count = 0

    for doc, score in results:

        candidate_sim = semantic_similarity(
            embedding_model,
            expected_answer,
            doc.page_content
        )

        if candidate_sim >= SIM_THRESHOLD:

            relevant_count += 1

    precision5 = relevant_count / TOP_K

    # =====================================================
    # RECALL@K
    # =====================================================

    recall5 = 1 if relevant_count > 0 else 0

    # =====================================================
    # NDCG@5
    # =====================================================

    ndcg5 = 0

    for rank, (doc, score) in enumerate(results, start=1):

        candidate_sim = semantic_similarity(
            embedding_model,
            expected_answer,
            doc.page_content
        )

        relevance = candidate_sim

        ndcg5 += relevance / (rank + 1)

    hr1_all.append(hr1)
    mrr_all.append(mrr)
    ndcg_all.append(ndcg5)
    precision_all.append(precision5)
    recall_all.append(recall5)
    sim_all.append(sim)

    print(f"Hit@1      : {hr1}")
    print(f"MRR        : {mrr:.4f}")
    print(f"NDCG@5     : {ndcg5:.4f}")
    print(f"Precision  : {precision5:.4f}")
    print(f"Recall     : {recall5:.4f}")
    print(f"Similarity : {sim:.4f}")
    print(f"Latency    : {latency:.2f}s")

    all_results.append({

        "question": query,

        "hit@1": hr1,

        "mrr": round(mrr, 4),

        "ndcg@5": round(ndcg5, 4),

        "precision@5": round(precision5, 4),

        "recall@5": round(recall5, 4),

        "semantic_similarity": round(sim, 4),

        "latency": round(latency, 3)
    })

n_items = len(hr1_all) if hr1_all else 1
summary = {

    "avg_hit@1":
        round(sum(hr1_all)/n_items, 4) if hr1_all else 0.0,

    "avg_mrr":
        round(sum(mrr_all)/n_items, 4) if mrr_all else 0.0,

    "avg_ndcg@5":
        round(sum(ndcg_all)/n_items, 4) if ndcg_all else 0.0,

    "avg_precision@5":
        round(sum(precision_all)/n_items, 4) if precision_all else 0.0,

    "avg_recall@5":
        round(sum(recall_all)/n_items, 4) if recall_all else 0.0,

    "avg_similarity":
        round(sum(sim_all)/n_items, 4) if sim_all else 0.0,
}

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

for k, v in summary.items():

    print(f"{k:<25}: {v}")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    json.dump({
        "summary": summary,
        "details": all_results
    }, f, ensure_ascii=False, indent=2)

print(f"\nHasil disimpan ke: {OUTPUT_FILE}")