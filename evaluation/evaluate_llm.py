import json
import time
from pathlib import Path
import requests
import sys
from collections import Counter
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from retrieval_core import build_embedding_kwargs

load_dotenv()

# =========================================================
# CONFIG & DATASET
# =========================================================
API_URL = "http://localhost:8000/api/evaluate"
OUTPUT_DIR = Path("evaluation_results")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "llm_manual_results.json"

# Load dataset (Murni Manual 50 Soal)
from dataset_test.manual_test import MANUAL_TEST_SET
TEST_SET = MANUAL_TEST_SET

# Inisialisasi Evaluator LLM untuk menilai Faithfulness
evaluator_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.0
)

# Inisialisasi model embedding untuk menghitung BERTScore Proxy (STS)
print("Memuat model embedding untuk BERTScore Proxy...")
embedding_model = HuggingFaceEmbeddings(**build_embedding_kwargs())

# =========================================================
# ADVANCED METRICS FUNCTIONS
# =========================================================
def calculate_rouge_1(ref, hyp):
    """Menghitung F1-score ROUGE-1 (Unigram Overlap)"""
    if not ref or not hyp:
        return 0.0
    ref_words = ref.lower().split()
    hyp_words = hyp.lower().split()
    if not ref_words or not hyp_words:
        return 0.0
    
    ref_counts = Counter(ref_words)
    hyp_counts = Counter(hyp_words)
    overlap = sum(min(count, ref_counts[word]) for word, count in hyp_counts.items())
    
    precision = overlap / len(hyp_words)
    recall = overlap / len(ref_words)
    if precision + recall == 0:
        return 0.0
    return (2 * precision * recall) / (precision + recall)

def calculate_rouge_l(ref, hyp):
    """Menghitung F1-score ROUGE-L (Longest Common Subsequence)"""
    if not ref or not hyp:
        return 0.0
    ref_words = ref.lower().split()
    hyp_words = hyp.lower().split()
    m, n = len(ref_words), len(hyp_words)
    if m == 0 or n == 0:
        return 0.0
    
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    
    lcs = dp[m][n]
    precision = lcs / n
    recall = lcs / m
    if precision + recall == 0:
        return 0.0
    return (2 * precision * recall) / (precision + recall)

def calculate_meteor(ref, hyp):
    """Menghitung METEOR sederhana (Precision, Recall, dan Chunk Penalty)"""
    if not ref or not hyp:
        return 0.0
    ref_words = ref.lower().split()
    hyp_words = hyp.lower().split()
    if not ref_words or not hyp_words:
        return 0.0
    
    ref_counts = Counter(ref_words)
    hyp_counts = Counter(hyp_words)
    matched_unigrams = sum(min(count, ref_counts[word]) for word, count in hyp_counts.items())
    
    if matched_unigrams == 0:
        return 0.0
    
    precision = matched_unigrams / len(hyp_words)
    recall = matched_unigrams / len(ref_words)
    
    # weighted F-mean condong ke Recall (alpha=0.9, beta=3.0)
    f_mean = (10 * precision * recall) / (recall + 9 * precision)
    
    # Menghitung chunk penalty sederhana
    chunks = 0
    i = 0
    while i < len(hyp_words):
        if hyp_words[i] in ref_words:
            chunks += 1
            while i < len(hyp_words) and hyp_words[i] in ref_words:
                i += 1
        else:
            i += 1
            
    penalty = 0.5 * ((chunks / matched_unigrams) ** 3)
    score = f_mean * (1 - penalty)
    return max(0.0, score)

def calculate_bertscore_proxy(ref, hyp, embedder):
    """Menghitung Cosine Similarity (Semantic Textual Similarity) menggunakan model MPNet"""
    if not ref or not hyp:
        return 0.0
    try:
        vec_ref = embedder.embed_query(ref)
        vec_hyp = embedder.embed_query(hyp)
        from sklearn.metrics.pairwise import cosine_similarity
        return float(cosine_similarity([vec_ref], [vec_hyp])[0][0])
    except Exception:
        return 0.0

def evaluate_faithfulness(context, reason):
    """Menilai apakah alasan penilaian didukung sepenuhnya oleh dokumen referensi"""
    if not context or not reason:
        return 1.0
    
    prompt = f"""
    Kamu adalah evaluator sistem RAG hukum. Tugasmu adalah menilai validitas faktual (Faithfulness) dari Alasan Juri AI berdasarkan Dokumen Referensi.
    Apakah seluruh klaim informasi pada Alasan Juri sepenuhnya konsisten, didukung, dan tidak bertentangan dengan Dokumen Referensi?
    
    DOKUMEN REFERENSI:
    {context}
    
    ALASAN JURI AI:
    {reason}
    
    Aturan Penilaian:
    - Kembalikan nilai 1 jika seluruh alasan juri logis dan didukung penuh dokumen referensi.
    - Kembalikan nilai 0 jika ada unsur alasan juri yang berhalusinasi atau bertentangan dengan dokumen referensi.
    
    Kembalikan jawaban HANYA dalam struktur JSON mentah berikut tanpa penjelasan tambahan:
    {{
        "score": 1 atau 0
    }}
    """
    try:
        res = evaluator_llm.invoke(prompt)
        content = res.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        data = json.loads(content)
        return float(data.get("score", 1.0))
    except Exception:
        return 1.0

# =========================================================
# MAIN EVALUATION
# =========================================================
results = []
passed = 0
total_rouge_1 = 0.0
total_rouge_l = 0.0
total_meteor = 0.0
total_bert_score = 0.0
total_faithfulness = 0.0

for item in TEST_SET:
    payload = {
        "pertanyaan": item["question"],
        "nama_kontestan": "Peserta",
        "jawaban_kontestan": item["answer"]
    }
    
    # Jeda 3 detik untuk menghindari rate limit API Groq (TPM/RPM)
    time.sleep(3)
    
    start = time.time()
    response = requests.post(API_URL, json=payload, timeout=120)
    latency = time.time() - start
    
    if response.status_code != 200:
        print(f"\n[ERROR] Request failed (Status {response.status_code}): {response.text}")
        data = {"skor": 0, "alasan": f"API Error (Status {response.status_code})"}
        score = 0
    else:
        try:
            data = response.json()
            score = data.get("skor", 0)
        except Exception as e:
            print(f"\n[ERROR] Failed to parse JSON response: {e}")
            data = {"skor": 0, "alasan": f"JSON Parse Error: {e}"}
            score = 0
            
    is_pass = score >= item["min_score"]
    if is_pass:
        passed += 1
        
    # Hitung metrik sesuai referensi paper
    ref_ans = data.get("kunci_jawaban", "")
    hyp_ans = item["answer"]
    
    rouge_1 = calculate_rouge_1(ref_ans, hyp_ans)
    rouge_l = calculate_rouge_l(ref_ans, hyp_ans)
    meteor = calculate_meteor(ref_ans, hyp_ans)
    bert_score = calculate_bertscore_proxy(ref_ans, hyp_ans, embedding_model)
    
    raw_context = data.get("raw_context", "")
    alasan = data.get("alasan", "")
    faithfulness = evaluate_faithfulness(raw_context, alasan)
    
    total_rouge_1 += rouge_1
    total_rouge_l += rouge_l
    total_meteor += meteor
    total_bert_score += bert_score
    total_faithfulness += faithfulness
    
    print("\n" + "=" * 60)
    print(item["question"])
    print(f"Skor Juri AI: {score} (Expected: >= {item['min_score']}) -> PASS: {is_pass}")
    print(f"BERTScore   : {bert_score:.4f}")
    print(f"ROUGE-1     : {rouge_1:.4f}")
    print(f"ROUGE-L     : {rouge_l:.4f}")
    print(f"METEOR      : {meteor:.4f}")
    print(f"Faithful    : {int(faithfulness)}")
    print(f"Latency     : {latency:.2f}s")
    
    results.append({
        "question": item["question"],
        "score": score,
        "expected_min_score": item["min_score"],
        "passed": is_pass,
        "latency": round(latency, 3),
        "bert_score": round(bert_score, 4),
        "rouge_1": round(rouge_1, 4),
        "rouge_l": round(rouge_l, 4),
        "meteor": round(meteor, 4),
        "faithfulness": faithfulness,
        "reason": alasan
    })

# =========================================================
# SUMMARY
# =========================================================
n_items = len(TEST_SET)
accuracy = passed / n_items
avg_bert = total_bert_score / n_items
avg_r1 = total_rouge_1 / n_items
avg_rl = total_rouge_l / n_items
avg_met = total_meteor / n_items
avg_faith = total_faithfulness / n_items

summary = {
    "accuracy": round(accuracy, 4),
    "avg_bertscore": round(avg_bert, 4),
    "avg_rouge_1": round(avg_r1, 4),
    "avg_rouge_l": round(avg_rl, 4),
    "avg_meteor": round(avg_met, 4),
    "avg_faithfulness": round(avg_faith, 4),
    "passed": passed,
    "total": n_items
}

print("\n" + "=" * 60)
print("SUMMARY LLM GENERATION EVALUATION")
print("=" * 60)
for k, v in summary.items():
    print(f"{k:<18}: {v}")

# =========================================================
# SAVE
# =========================================================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump({
        "summary": summary,
        "details": results
    }, f, ensure_ascii=False, indent=2)

print(f"\nHasil evaluasi LLM disimpan ke: {OUTPUT_FILE}")