from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

from retrieval_core import EMBEDDING_MODEL, build_embedding_kwargs, hybrid_search

load_dotenv()

app = FastAPI(title="SmartJuri-AI API Engine")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COLLECTION_NAME = "dokumen_kewarganegaraan"

embedding_models = HuggingFaceEmbeddings(**build_embedding_kwargs())

db = Chroma(
    persist_directory="vectordb",
    embedding_function=embedding_models,
    collection_name=COLLECTION_NAME
)

llm = ChatGroq(
    model="llama-3.3-70b-versatile", 
    temperature=0.1
)

class EvaluationRequest(BaseModel):
    pertanyaan: str
    nama_kontestan: str
    jawaban_kontestan: str

@app.post("/api/evaluate")
async def evaluate_answer(req: EvaluationRequest):
    if not req.pertanyaan or not req.jawaban_kontestan:
        raise HTTPException(status_code=400, detail="Pertanyaan dan jawaban wajib diisi")
    
    try:
        # 1. RAG Retrieval hybrid agar istilah hukum persis dan makna semantik sama-sama terambil
        docs = [doc for doc, _ in hybrid_search(db, req.pertanyaan, k=4)]
        context_text = "\n\n".join([
            f"[Sumber: {doc.metadata['source_file']} hal. {doc.metadata['page_number']}]\n{doc.page_content}" 
            for doc in docs
        ])
        
        # 2. Prompt Engineering
        system_prompt = f"""
        Kamu adalah Dewan Juri Cerdas Cermat Empat Pilar MPR RI yang objektif dan adil.
        Tugasmu adalah menilai jawaban dari SATU kontestan bernama {req.nama_kontestan} berdasarkan dokumen referensi.

        DOKUMEN REFERENSI (Kebenaran Mutlak):
        {context_text}

        PERTANYAAN LOMBA:
        {req.pertanyaan}

        JAWABAN {req.nama_kontestan}:
        {req.jawaban_kontestan}

        ATURAN PENILAIAN:
        1. Rumuskan KUNCI JAWABAN yang benar secara eksplisit berdasarkan dokumen referensi beserta pasal/sumbernya.
        2. Berikan SKOR angka bulat dari 0 sampai 10 berdasarkan KEMIRIPAN MAKNA (Semantic Similarity).
        3. Jika maknanya sama namun beda redaksi kata/singkatan (misal "DPD" vs "Dewan Perwakilan Daerah"), wajib beri skor maksimal (10).
        4. Jika jawaban salah total atau tidak nyambung, beri skor 0.
        5. Berikan penjelasan alasan penilaian yang singkat dan transparan.

        FORMAT OUTPUT (Wajib kembalikan dalam struktur JSON mentah seperti ini tanpa ada teks tambahan lain):
        {{
            "kunci_jawaban": "isi kunci jawaban resmi",
            "sumber_dokumen": "nama file dan halaman",
            "skor": 10,
            "alasan": "penjelasan evaluasi juri AI"
        }}
        """
        
        response = llm.invoke(system_prompt)
        
        # Output cleaning untuk parsing ke JSON
        import json
        clean_content = response.content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content.split("```json")[1].split("```")[0].strip()
        elif clean_content.startswith("```"):
            clean_content = clean_content.split("```")[1].split("```")[0].strip()
            
        result_json = json.loads(clean_content)
        result_json["raw_context"] = context_text
        
        return result_json
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
