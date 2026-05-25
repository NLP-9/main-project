import math
from sklearn.metrics.pairwise import cosine_similarity


# =========================================================
# HIT RATE
# =========================================================
def hit_rate(results, expected_doc_type, k):
    for doc, _ in results[:k]:
        if doc.metadata.get("document_type") == expected_doc_type:
            return 1
    return 0

# =========================================================
# RECIPROCAL RANK
# =========================================================
def reciprocal_rank(results, expected_doc_type):
    for rank, (doc, _) in enumerate(results, start=1):
        if doc.metadata.get("document_type") == expected_doc_type:
            return 1.0 / rank
    return 0.0

# =========================================================
# NDCG
# =========================================================
def ndcg(results, expected_doc_type, k):
    gains = []
    for doc, _ in results[:k]:
        relevance = (
            1 if doc.metadata.get("document_type") == expected_doc_type else 0
        )
        gains.append(relevance)
    dcg = sum(
        g / math.log2(i + 2)
        for i, g in enumerate(gains)
    )
    ideal = sorted(gains, reverse=True)
    idcg = sum(
        g / math.log2(i + 2)
        for i, g in enumerate(ideal)
    )
    if idcg == 0:
        return 0.0
    return dcg / idcg

# =========================================================
# PRECISION@K
# =========================================================
def precision_at_k(results, expected_doc_type, k):
    relevant = 0
    for doc, _ in results[:k]:
        if doc.metadata.get("document_type") == expected_doc_type:
            relevant += 1
    return relevant / k

# =========================================================
# RECALL@K
# =========================================================
def recall_at_k(results, expected_doc_type, k):
    relevant = 0
    for doc, _ in results[:k]:
        if doc.metadata.get("document_type") == expected_doc_type:
            relevant += 1
    return min(relevant, 1)

# =========================================================
# SEMANTIC SIMILARITY
# =========================================================
def semantic_similarity(embedder, text_a, text_b):
    vec_a = embedder.embed_query(text_a)
    vec_b = embedder.embed_query(text_b)
    return float(
        cosine_similarity([vec_a], [vec_b])[0][0]
    )