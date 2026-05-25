from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from retrieval_core import (
    EMBEDDING_MODEL,
    build_embedding_kwargs,
)

VECTOR_DB_DIR = Path("vectordb")

COLLECTION_NAME = "dokumen_kewarganegaraan"


def load_questions(limit=10):

    embedding_model = HuggingFaceEmbeddings(
        **build_embedding_kwargs()
    )

    db = Chroma(
        persist_directory=str(VECTOR_DB_DIR),
        embedding_function=embedding_model,
        collection_name=COLLECTION_NAME
    )

    raw = db._collection.get(
        limit=limit,
        include=["documents", "metadatas"]
    )

    questions = []

    for doc, meta in zip(
        raw["documents"],
        raw["metadatas"]
    ):

        preview = doc[:250]

        questions.append({

            "question":
                f"Jelaskan isi dokumen berikut:\n{preview[:150]}",

            "answer":
                preview,

            "doc_type":
                meta.get("document_type", "UNKNOWN"),

            "min_score": 7
        })

    return questions