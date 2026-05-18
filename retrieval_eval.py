import os
from pathlib import Path

import numpy as np
import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from retrieval_core import (
    EMBEDDING_MODEL,
    build_embedding_kwargs,
    detect_document_filter,
    hybrid_search,
)

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


VECTOR_DB_DIR = Path("vectordb")
COLLECTION_NAME = "dokumen_kewarganegaraan"

TEST_QUERIES = [
    (
        "apa itu UUD 1945 dan fungsinya",
        {"UUD"},
        ["uud", "konstitusi", "dasar negara"],
    ),
    (
        "jelaskan hak dan kewajiban warga negara",
        {"UUD", "EMPAT_PILAR"},
        ["hak", "kewajiban", "warga negara"],
    ),
    (
        "bagaimana proses amandemen UUD",
        {"UUD", "TAP_MPR"},
        ["amandemen", "perubahan", "uud"],
    ),
    (
        "apa saja empat pilar kewarganegaraan Indonesia",
        {"EMPAT_PILAR"},
        ["pilar", "pancasila", "bhinneka", "nkri"],
    ),
    (
        "apa itu TAP MPR dan fungsinya",
        {"TAP_MPR"},
        ["tap", "mpr", "ketetapan"],
    ),
    (
        "siapa saja yang bisa menjadi presiden",
        {"UUD"},
        ["presiden", "syarat", "pemilihan"],
    ),
    (
        "bagaimana sistem pemerintahan di Indonesia",
        {"UUD", "EMPAT_PILAR"},
        ["pemerintah", "sistem", "struktur"],
    ),
    (
        "apa makna Pancasila dalam kehidupan berbangsa",
        {"EMPAT_PILAR"},
        ["pancasila", "ideologi", "nilai"],
    ),
]


def resolve_collection_name():
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    collection_names = [collection.name for collection in client.list_collections()]

    if COLLECTION_NAME in collection_names:
        collection = client.get_collection(COLLECTION_NAME)
        if collection.count() > 0:
            return COLLECTION_NAME

    raise ValueError("Vector database belum berisi data. Jalankan ingest.py terlebih dahulu.")


def calculate_metrics(results, expected_doc_types, keywords, top_k=5):
    relevant_count = 0
    keyword_match_count = 0
    mrr = 0
    first_relevant_rank = None

    for rank, (doc, _) in enumerate(results[:top_k], 1):
        doc_type = doc.metadata.get("document_type", "")
        content = doc.page_content.lower()

        is_correct_type = doc_type in expected_doc_types
        has_keyword = any(keyword.lower() in content for keyword in keywords)

        if is_correct_type and has_keyword:
            relevant_count += 1
            if first_relevant_rank is None:
                first_relevant_rank = rank
                mrr = 1.0 / rank

        if has_keyword:
            keyword_match_count += 1

    result_count = len(results[:top_k])
    precision_at_k = relevant_count / result_count if result_count else 0
    keyword_match_rate = keyword_match_count / result_count if result_count else 0

    return {
        "precision_at_k": precision_at_k,
        "keyword_match_rate": keyword_match_rate,
        "mrr": mrr,
        "relevant_count": relevant_count,
        "first_relevant_rank": first_relevant_rank,
    }


def main():
    print("\n" + "=" * 60)
    print("EVALUASI RETRIEVAL SYSTEM")
    print("=" * 60)

    print("\nMemuat komponen...")
    embedding_model = HuggingFaceEmbeddings(**build_embedding_kwargs())

    if not VECTOR_DB_DIR.exists():
        raise FileNotFoundError("Folder vectordb belum ada. Jalankan ingest.py terlebih dahulu.")

    active_collection_name = resolve_collection_name()
    db = Chroma(
        persist_directory=str(VECTOR_DB_DIR),
        embedding_function=embedding_model,
        collection_name=active_collection_name,
    )

    print(f"Collection: {active_collection_name}")
    print(f"Model embedding: {EMBEDDING_MODEL}")
    print(f"Total chunks: {db._collection.count()}")

    print("\n" + "=" * 60)
    print("MENJALANKAN EVALUASI")
    print("=" * 60)

    all_metrics = []
    top_k = 5

    for i, (query, expected_types, keywords) in enumerate(TEST_QUERIES, 1):
        print(f"\n[Query {i}/{len(TEST_QUERIES)}]")
        print(f"Q: {query}")

        search_filter = detect_document_filter(query)
        results = hybrid_search(db, query=query, k=top_k, search_filter=search_filter)
        metrics = calculate_metrics(results, expected_types, keywords, top_k)
        all_metrics.append(metrics)

        print(f"  Precision@{top_k}: {metrics['precision_at_k']:.2%}")
        print(f"  Keyword Match Rate: {metrics['keyword_match_rate']:.2%}")
        print(f"  MRR: {metrics['mrr']:.4f}")
        print(f"  Relevant docs found: {metrics['relevant_count']}/{len(results)}")

        if metrics["first_relevant_rank"]:
            print(f"  First relevant at rank: {metrics['first_relevant_rank']}")
        else:
            print("  No relevant document found")

        print("\n  Top 2 Results:")
        for rank, (doc, score) in enumerate(results[:2], 1):
            doc_type = doc.metadata.get("document_type", "N/A")
            source = doc.metadata.get("source_file", "N/A")
            print(f"    [{rank}] {doc_type} | {source} (score: {score:.4f})")
            print(f"        {doc.page_content[:120]}...")

    print("\n\n" + "=" * 60)
    print("RINGKASAN EVALUASI")
    print("=" * 60)

    avg_precision = np.mean([m["precision_at_k"] for m in all_metrics])
    avg_keyword_match = np.mean([m["keyword_match_rate"] for m in all_metrics])
    avg_mrr = np.mean([m["mrr"] for m in all_metrics])
    hit_rate = np.mean([m["mrr"] > 0 for m in all_metrics])
    total_relevant_found = sum(m["relevant_count"] for m in all_metrics)
    total_expected = len(TEST_QUERIES) * top_k
    overall_score = (avg_precision + avg_keyword_match + min(avg_mrr, 1.0)) / 3

    print(f"\nMETRICS KESELURUHAN (Top-{top_k}):")
    print(f"   Average Precision@{top_k}: {avg_precision:.2%}")
    print(f"   Average Keyword Match Rate: {avg_keyword_match:.2%}")
    print(f"   Mean Reciprocal Rank (MRR): {avg_mrr:.4f}")
    print(f"   Total Relevant Found: {total_relevant_found}/{total_expected}")
    print(f"   Hit Rate: {hit_rate:.0%} (query punya hasil relevan)")
    print(f"\nOVERALL RETRIEVAL SCORE: {overall_score:.2%}")

    if overall_score >= 0.8:
        print("   Retrieval system BAGUS!")
        print("   Sistem sudah mampu menemukan dokumen relevan dengan akurat.")
    elif overall_score >= 0.6:
        print("   Retrieval system CUKUP")
        print("   Ada ruang untuk improvement dalam menemukan dokumen relevan.")
    else:
        print("   Retrieval system BURUK")
        print("   Sistem masih kesulitan menemukan dokumen relevan.")

    print("\n\nANALISIS PER-QUERY:")
    print(f"{'Query':<40} {'Precision':<12} {'Keyword Match':<15} {'MRR':<10}")
    print("-" * 77)

    for i, (query, _, _) in enumerate(TEST_QUERIES):
        metrics = all_metrics[i]
        print(
            f"{query[:38]:<40} "
            f"{metrics['precision_at_k']:<12.2%} "
            f"{metrics['keyword_match_rate']:<15.2%} "
            f"{metrics['mrr']:<10.4f}"
        )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
