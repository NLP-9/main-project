import math
import os
import re
from collections import Counter

from langchain_core.documents import Document


os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

STOPWORDS = {
    "apa",
    "itu",
    "dan",
    "yang",
    "dalam",
    "di",
    "ke",
    "dari",
    "untuk",
    "pada",
    "bagaimana",
    "jelaskan",
    "saja",
    "bisa",
    "menjadi",
}

QUERY_EXPANSIONS = {
    "uud": ["undang undang dasar", "konstitusi", "dasar negara", "u.u.d"],
    "tap": ["ketetapan", "mpr", "majelis permusyawaratan rakyat"],
    "mpr": ["majelis permusyawaratan rakyat", "ketetapan"],
    "amandemen": ["perubahan", "mengubah", "diubah"],
    "perubahan": ["amandemen", "mengubah", "diubah"],
    "presiden": ["calon presiden", "wakil presiden", "warga negara indonesia"],
    "pancasila": ["ideologi", "dasar negara", "nilai"],
    "pilar": ["empat pilar", "pancasila", "uud", "nkri", "bhinneka tunggal ika"],
    "bhinneka": ["bhinneka tunggal ika", "persatuan", "keragaman"],
    "nkri": ["negara kesatuan republik indonesia"],
    "hak": ["hak warga negara", "kewajiban", "warga negara"],
    "kewajiban": ["kewajiban warga negara", "hak", "warga negara"],
    "pemerintahan": ["pemerintah", "sistem pemerintahan", "lembaga negara"],
}


def build_embedding_kwargs():
    offline = (
        os.environ.get("HF_HUB_OFFLINE") == "1"
        or os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    )
    return {
        "model_name": EMBEDDING_MODEL,
        "model_kwargs": {"local_files_only": offline},
        "encode_kwargs": {"normalize_embeddings": True},
    }


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text):
    return [
        token
        for token in normalize_text(text).split()
        if len(token) > 2 and token not in STOPWORDS
    ]


def expand_query(query):
    additions = []
    normalized_query = normalize_text(query)

    for token in tokenize(query):
        additions.extend(QUERY_EXPANSIONS.get(token, []))

    if "empat pilar" in normalized_query:
        additions.extend(["pancasila", "uud 1945", "nkri", "bhinneka tunggal ika"])
    if "warga negara" in normalized_query:
        additions.extend(["hak warga negara", "kewajiban warga negara"])

    unique_additions = []
    seen = set()
    for addition in additions:
        if addition not in seen and addition not in normalized_query:
            unique_additions.append(addition)
            seen.add(addition)

    return " ".join([query, *unique_additions]).strip()


def detect_document_filter(query):
    normalized_query = normalize_text(query)

    if re.search(r"\buud\b|undang undang dasar", normalized_query):
        return {"document_type": "UUD"}
    if re.search(r"\btap\b|ketetapan mpr", normalized_query):
        return {"document_type": "TAP_MPR"}
    if "empat pilar" in normalized_query or re.search(r"\bpilar\b", normalized_query):
        return {"document_type": "EMPAT_PILAR"}
    if re.search(r"\bpresiden\b|wakil presiden|calon presiden", normalized_query):
        return {"document_type": "UUD"}
    if re.search(r"\bpancasila\b|\bbhinneka\b|\bnkri\b", normalized_query):
        return {"document_type": "EMPAT_PILAR"}

    return None


def _candidate_key(doc):
    metadata = doc.metadata
    return (
        metadata.get("source_file", ""),
        metadata.get("page_number", ""),
        metadata.get("chunk_id", ""),
    )


def _semantic_similarity(distance):
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + max(float(distance), 0.0))


def _phrase_score(expanded_query, content):
    score = 0.0
    normalized_content = normalize_text(content)
    normalized_query = normalize_text(expanded_query)

    for phrase in QUERY_EXPANSIONS.values():
        for item in phrase:
            if item in normalized_query and normalize_text(item) in normalized_content:
                score += 0.35

    for item in ["uud 1945", "tap mpr", "empat pilar", "bhinneka tunggal ika", "warga negara"]:
        if item in normalized_query and item in normalized_content:
            score += 0.6

    return score


def _lexical_score(query_tokens, expanded_query, content):
    doc_tokens = tokenize(content)
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_counts = Counter(doc_tokens)
    doc_length = len(doc_tokens)
    overlap = 0.0

    for token in query_tokens:
        frequency = doc_counts.get(token, 0)
        if frequency:
            overlap += 1.0 + math.log1p(frequency)

    coverage = overlap / len(query_tokens)
    density = overlap / math.sqrt(doc_length)
    return coverage + density + _phrase_score(expanded_query, content)


def _normalize_scores(candidates, score_key):
    values = [candidate[score_key] for candidate in candidates.values()]
    max_value = max(values) if values else 0.0
    if max_value <= 0:
        return

    for candidate in candidates.values():
        candidate[f"{score_key}_norm"] = candidate[score_key] / max_value


def _collection_documents(db, where=None):
    kwargs = {"include": ["documents", "metadatas"]}
    if where:
        kwargs["where"] = where

    raw = db._collection.get(**kwargs)
    documents = raw.get("documents") or []
    metadatas = raw.get("metadatas") or []

    for content, metadata in zip(documents, metadatas):
        yield Document(page_content=content or "", metadata=metadata or {})


def hybrid_search(db, query, k=5, search_filter=None, semantic_k=60, lexical_k=80):
    expanded_query = expand_query(query)
    query_tokens = tokenize(expanded_query)
    candidates = {}

    semantic_results = db.similarity_search_with_score(
        query=expanded_query,
        k=max(k, semantic_k),
        filter=search_filter,
    )

    for rank, (doc, distance) in enumerate(semantic_results, start=1):
        key = _candidate_key(doc)
        candidates[key] = {
            "doc": doc,
            "semantic": _semantic_similarity(distance),
            "lexical": 0.0,
            "rank_bonus": 1.0 / rank,
        }

    lexical_results = []
    for doc in _collection_documents(db, where=search_filter):
        score = _lexical_score(query_tokens, expanded_query, doc.page_content)
        if score > 0:
            lexical_results.append((doc, score))

    lexical_results.sort(key=lambda item: item[1], reverse=True)

    for doc, score in lexical_results[: max(k, lexical_k)]:
        key = _candidate_key(doc)
        if key not in candidates:
            candidates[key] = {
                "doc": doc,
                "semantic": 0.0,
                "lexical": 0.0,
                "rank_bonus": 0.0,
            }
        candidates[key]["lexical"] = max(candidates[key]["lexical"], score)

    _normalize_scores(candidates, "semantic")
    _normalize_scores(candidates, "lexical")

    ranked = []
    for candidate in candidates.values():
        semantic = candidate.get("semantic_norm", 0.0)
        lexical = candidate.get("lexical_norm", 0.0)
        score = (0.55 * semantic) + (0.40 * lexical) + (0.05 * candidate["rank_bonus"])
        ranked.append((candidate["doc"], score))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:k]
