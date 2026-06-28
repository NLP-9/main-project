import math
import os
import re
from collections import Counter

from langchain_core.documents import Document


os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# ==================================================
# MODEL EMBEDDING
# ==================================================

# Rekomendasi untuk RAG / QA bahasa Indonesia
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"

# Alternatif kalau ingin balik ke model lama:
# EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# Alternatif Indonesia-specific:
# EMBEDDING_MODEL = "firqaaa/indo-sentence-bert-base"
# EMBEDDING_MODEL = "LazarusNLP/simcse-indobert-base"


# ==================================================
# STOPWORDS DAN QUERY EXPANSION
# ==================================================

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
    "adalah",
    "dengan",
    "sebagai",
    "atau",
    "serta",
}

QUERY_EXPANSIONS = {
    "uud": ["undang undang dasar", "konstitusi", "dasar negara", "uud 1945"],
    "tap": ["ketetapan", "mpr", "majelis permusyawaratan rakyat", "tap mpr"],
    "mpr": ["majelis permusyawaratan rakyat", "ketetapan"],
    "amandemen": ["perubahan", "mengubah", "diubah"],
    "perubahan": ["amandemen", "mengubah", "diubah"],
    "presiden": ["calon presiden", "wakil presiden", "warga negara indonesia"],
    "wakil": ["wakil presiden", "presiden"],
    "pancasila": ["ideologi", "dasar negara", "nilai pancasila"],
    "pilar": ["empat pilar", "pancasila", "uud 1945", "nkri", "bhinneka tunggal ika"],
    "bhinneka": ["bhinneka tunggal ika", "persatuan", "keragaman"],
    "nkri": ["negara kesatuan republik indonesia", "negara kesatuan"],
    "hak": ["hak warga negara", "kewajiban", "warga negara"],
    "kewajiban": ["kewajiban warga negara", "hak", "warga negara"],
    "pemerintahan": ["pemerintah", "sistem pemerintahan", "lembaga negara"],
    "pasal": ["uud 1945", "undang undang dasar"],
}


# ==================================================
# KONFIGURASI EMBEDDING
# ==================================================

def uses_e5_model() -> bool:
    return EMBEDDING_MODEL.startswith("intfloat/multilingual-e5")


def build_embedding_kwargs():
    """
    Konfigurasi model embedding.
    Jika menggunakan E5, normalize_embeddings=True tetap disarankan.
    """

    offline = (
        os.environ.get("HF_HUB_OFFLINE") == "1"
        or os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    )

    model_kwargs = {
        "device": os.environ.get("EMBEDDING_DEVICE", "cpu")
    }

    if offline:
        model_kwargs["local_files_only"] = True

    return {
        "model_name": EMBEDDING_MODEL,
        "model_kwargs": model_kwargs,
        "encode_kwargs": {
            "normalize_embeddings": True
        },
    }


def format_document_for_embedding(text: str) -> str:
    """
    Format dokumen sebelum dimasukkan ke vector database.
    Untuk model E5, dokumen sebaiknya diawali dengan 'passage:'.
    """

    text = text.strip()

    if uses_e5_model():
        return f"passage: {text}"

    return text


def format_query_for_embedding(query: str) -> str:
    """
    Format query sebelum similarity search.
    Untuk model E5, query sebaiknya diawali dengan 'query:'.
    """

    query = query.strip()

    if uses_e5_model():
        return f"query: {query}"

    return query


# ==================================================
# TEXT NORMALIZATION
# ==================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def tokenize(text: str):
    return [
        token
        for token in normalize_text(text).split()
        if len(token) > 2 and token not in STOPWORDS
    ]


# ==================================================
# QUERY EXPANSION
# ==================================================

def expand_query(query: str) -> str:
    """
    Menambahkan sinonim atau istilah terkait agar retrieval lebih kuat.
    Contoh:
    - UUD -> undang undang dasar, konstitusi
    - TAP -> ketetapan, MPR
    - pilar -> pancasila, uud, nkri, bhinneka
    """

    additions = []
    normalized_query = normalize_text(query)

    for token in tokenize(query):
        additions.extend(QUERY_EXPANSIONS.get(token, []))

    if "empat pilar" in normalized_query:
        additions.extend([
            "pancasila",
            "uud 1945",
            "nkri",
            "bhinneka tunggal ika",
        ])

    if "warga negara" in normalized_query:
        additions.extend([
            "hak warga negara",
            "kewajiban warga negara",
        ])

    if "undang undang dasar" in normalized_query:
        additions.extend([
            "uud 1945",
            "konstitusi",
        ])

    unique_additions = []
    seen = set()

    for addition in additions:
        normalized_addition = normalize_text(addition)

        if normalized_addition not in seen and normalized_addition not in normalized_query:
            unique_additions.append(addition)
            seen.add(normalized_addition)

    return " ".join([query, *unique_additions]).strip()


# ==================================================
# FILTER DOKUMEN
# ==================================================

def detect_document_filter(query: str):
    """
    Mendeteksi filter dokumen berdasarkan isi pertanyaan.
    Ini membantu agar pertanyaan tentang UUD tidak terlalu banyak mengambil
    dokumen Empat Pilar, dan sebaliknya.
    """

    normalized_query = normalize_text(query)

    if re.search(r"\buud\b|undang undang dasar|pasal", normalized_query):
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


# ==================================================
# HELPER SCORING
# ==================================================

def _candidate_key(doc: Document):
    metadata = doc.metadata

    return (
        metadata.get("source_file", ""),
        metadata.get("page_number", ""),
        metadata.get("chunk_id", ""),
    )


def _semantic_similarity(distance):
    """
    Chroma biasanya mengembalikan distance.
    Semakin kecil distance, semakin mirip.
    Fungsi ini mengubah distance menjadi skor similarity.
    """

    if distance is None:
        return 0.0

    distance = max(float(distance), 0.0)

    return 1.0 / (1.0 + distance)


def _phrase_score(expanded_query: str, content: str):
    score = 0.0

    normalized_content = normalize_text(content)
    normalized_query = normalize_text(expanded_query)

    for phrase_list in QUERY_EXPANSIONS.values():
        for item in phrase_list:
            normalized_item = normalize_text(item)

            if normalized_item in normalized_query and normalized_item in normalized_content:
                score += 0.35

    important_phrases = [
        "uud 1945",
        "tap mpr",
        "empat pilar",
        "bhinneka tunggal ika",
        "warga negara",
        "hak warga negara",
        "kewajiban warga negara",
        "majelis permusyawaratan rakyat",
        "negara kesatuan republik indonesia",
    ]

    for item in important_phrases:
        normalized_item = normalize_text(item)

        if normalized_item in normalized_query and normalized_item in normalized_content:
            score += 0.6

    return score


def _lexical_score(query_tokens, expanded_query: str, content: str):
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


def _normalize_scores(candidates, score_key: str):
    values = [candidate[score_key] for candidate in candidates.values()]
    max_value = max(values) if values else 0.0

    if max_value <= 0:
        return

    for candidate in candidates.values():
        candidate[f"{score_key}_norm"] = candidate[score_key] / max_value


def _collection_documents(db, where=None):
    """
    Mengambil semua dokumen dari collection Chroma untuk lexical search.
    Catatan:
    - db._collection adalah internal Chroma object.
    - Ini masih umum dipakai untuk kebutuhan custom hybrid retrieval sederhana.
    """

    kwargs = {
        "include": ["documents", "metadatas"]
    }

    if where:
        kwargs["where"] = where

    raw = db._collection.get(**kwargs)

    documents = raw.get("documents") or []
    metadatas = raw.get("metadatas") or []

    for content, metadata in zip(documents, metadatas):
        yield Document(
            page_content=content or "",
            metadata=metadata or {}
        )


# ==================================================
# HYBRID SEARCH
# ==================================================

def hybrid_search(
    db,
    query: str,
    k: int = 5,
    search_filter=None,
    semantic_k: int = 60,
    lexical_k: int = 80,
    auto_filter: bool = True,
):
    """
    Hybrid search:
    1. Semantic search dari embedding Chroma
    2. Lexical search berbasis token overlap
    3. Gabungan skor semantic + lexical + rank bonus

    Cocok untuk dokumen:
    - UUD
    - TAP MPR
    - Empat Pilar
    - Contoh soal kewarganegaraan
    """

    expanded_query = expand_query(query)
    query_tokens = tokenize(expanded_query)

    if search_filter is None and auto_filter:
        search_filter = detect_document_filter(query)

    candidates = {}

    # ==============================
    # 1. Semantic Search
    # ==============================

    semantic_query = format_query_for_embedding(expanded_query)

    semantic_results = db.similarity_search_with_score(
        query=semantic_query,
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

    # ==============================
    # 2. Lexical Search
    # ==============================

    lexical_results = []

    for doc in _collection_documents(db, where=search_filter):
        score = _lexical_score(
            query_tokens=query_tokens,
            expanded_query=expanded_query,
            content=doc.page_content,
        )

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

        candidates[key]["lexical"] = max(
            candidates[key]["lexical"],
            score
        )

    # Kalau filter terlalu ketat dan tidak ada hasil, ulang tanpa filter
    if not candidates and search_filter is not None and auto_filter:
        return hybrid_search(
            db=db,
            query=query,
            k=k,
            search_filter=None,
            semantic_k=semantic_k,
            lexical_k=lexical_k,
            auto_filter=False,
        )

    # ==============================
    # 3. Normalisasi dan Ranking
    # ==============================

    _normalize_scores(candidates, "semantic")
    _normalize_scores(candidates, "lexical")

    ranked = []

    for candidate in candidates.values():
        semantic = candidate.get("semantic_norm", 0.0)
        lexical = candidate.get("lexical_norm", 0.0)
        rank_bonus = candidate.get("rank_bonus", 0.0)

        final_score = (
            0.55 * semantic
            + 0.40 * lexical
            + 0.05 * rank_bonus
        )

        ranked.append((candidate["doc"], final_score))

    ranked.sort(key=lambda item: item[1], reverse=True)

    return ranked[:k]