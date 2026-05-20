"""
evaluate_llm.py  —  Evaluasi LLM End-to-End SmartJuri-AI
Anggota 3: AI Evaluator & Technical Writer

Pastikan backend sudah jalan dulu:
    python main.py

Lalu jalankan:
    python evaluate_llm.py

Output: hasil di terminal + file evaluate_llm_results.json
"""

import json
import time
import requests
from pathlib import Path

# ==============================================================
# KONFIGURASI
# ==============================================================
API_URL    = "http://localhost:8000/api/evaluate"
OUTPUT_FILE = Path("evaluate_llm_results.json")

# ==============================================================
# TEST SET — pasangan pertanyaan + kunci jawaban benar
# serta variasi jawaban peserta untuk menguji fairness model
# ==============================================================
TEST_SET = [
    # --- Kasus 1: Jawaban benar persis ---
    {
        "id": 1,
        "kategori": "jawaban_benar_persis",
        "pertanyaan": "Siapakah yang berwenang mengubah dan menetapkan Undang-Undang Dasar?",
        "kunci_jawaban_expected": "MPR berwenang mengubah dan menetapkan UUD",
        "nama_kontestan": "Tim A",
        "jawaban_kontestan": "Majelis Permusyawaratan Rakyat berwenang mengubah dan menetapkan Undang-Undang Dasar.",
        "skor_expected_min": 8,
    },
    # --- Kasus 2: Jawaban benar tapi pakai singkatan ---
    {
        "id": 2,
        "kategori": "beda_redaksi_singkatan",
        "pertanyaan": "Siapakah yang berwenang mengubah dan menetapkan Undang-Undang Dasar?",
        "kunci_jawaban_expected": "MPR berwenang mengubah dan menetapkan UUD",
        "nama_kontestan": "Tim B",
        "jawaban_kontestan": "MPR",
        "skor_expected_min": 8,  # sesuai aturan prompt: singkatan = skor maksimal
    },
    # --- Kasus 3: Jawaban salah total ---
    {
        "id": 3,
        "kategori": "jawaban_salah_total",
        "pertanyaan": "Siapakah yang berwenang mengubah dan menetapkan Undang-Undang Dasar?",
        "kunci_jawaban_expected": "MPR berwenang mengubah dan menetapkan UUD",
        "nama_kontestan": "Tim C",
        "jawaban_kontestan": "Presiden Republik Indonesia",
        "skor_expected_max": 3,
    },
    # --- Kasus 4: Jawaban benar beda redaksi (parafrase) ---
    {
        "id": 4,
        "kategori": "beda_redaksi_parafrase",
        "pertanyaan": "Apa isi Pasal 34 UUD 1945 tentang fakir miskin?",
        "kunci_jawaban_expected": "Fakir miskin dan anak-anak terlantar dipelihara oleh negara",
        "nama_kontestan": "Tim A",
        "jawaban_kontestan": "Negara wajib memelihara dan menjamin kehidupan warga yang miskin dan anak yang tidak memiliki orang tua.",
        "skor_expected_min": 7,
    },
    # --- Kasus 5: Jawaban benar tapi tidak lengkap ---
    {
        "id": 5,
        "kategori": "jawaban_tidak_lengkap",
        "pertanyaan": "Sebutkan tiga sila terakhir Pancasila!",
        "kunci_jawaban_expected": "Persatuan Indonesia, Kerakyatan yang dipimpin hikmat kebijaksanaan, Keadilan sosial",
        "nama_kontestan": "Tim B",
        "jawaban_kontestan": "Persatuan Indonesia",
        "skor_expected_max": 6,
    },
    # --- Kasus 6: Jawaban benar dengan konteks berbeda ---
    {
        "id": 6,
        "kategori": "jawaban_benar_konteks_lain",
        "pertanyaan": "Apa makna Bhinneka Tunggal Ika?",
        "kunci_jawaban_expected": "Berbeda-beda tetapi tetap satu",
        "nama_kontestan": "Tim C",
        "jawaban_kontestan": "Walaupun berbeda-beda suku, agama, dan budaya, bangsa Indonesia tetap satu kesatuan.",
        "skor_expected_min": 8,
    },
    # --- Kasus 7: Jawaban kosong ---
    {
        "id": 7,
        "kategori": "jawaban_kosong",
        "pertanyaan": "Apa yang dimaksud dengan kedaulatan rakyat?",
        "kunci_jawaban_expected": "Kedaulatan berada di tangan rakyat",
        "nama_kontestan": "Tim A",
        "jawaban_kontestan": "Tidak tahu",
        "skor_expected_max": 2,
    },
    # --- Kasus 8: Jawaban benar persis dengan nomor pasal ---
    {
        "id": 8,
        "kategori": "jawaban_benar_dengan_pasal",
        "pertanyaan": "Negara Indonesia adalah negara kesatuan yang berbentuk apa?",
        "kunci_jawaban_expected": "Republik, sesuai Pasal 1 ayat 1 UUD 1945",
        "nama_kontestan": "Tim B",
        "jawaban_kontestan": "Republik",
        "skor_expected_min": 8,
    },
    # --- Kasus 9: Jawaban ambigu ---
    {
        "id": 9,
        "kategori": "jawaban_ambigu",
        "pertanyaan": "Berapa kali UUD 1945 telah diamandemen?",
        "kunci_jawaban_expected": "Empat kali",
        "nama_kontestan": "Tim C",
        "jawaban_kontestan": "Sudah beberapa kali dilakukan perubahan oleh MPR.",
        "skor_expected_max": 6,
    },
    # --- Kasus 10: Jawaban benar tapi typo ---
    {
        "id": 10,
        "kategori": "toleransi_typo",
        "pertanyaan": "Apa semboyan negara Indonesia?",
        "kunci_jawaban_expected": "Bhinneka Tunggal Ika",
        "nama_kontestan": "Tim A",
        "jawaban_kontestan": "Bhineka Tunggal Ika",  # typo: satu 'n'
        "skor_expected_min": 8,
    },

    {
        "id": 11,
        "kategori": "retrieval_failure_case",
        "pertanyaan": "Bagaimana bunyi Pasal 18A UUD 1945?",
        "kunci_jawaban_expected": "Hubungan wewenang antara pemerintah pusat dan daerah diatur dengan undang-undang...",
        "nama_kontestan": "Tim A",
        "jawaban_kontestan": "Hubungan wewenang antara pemerintah pusat dan pemerintahan daerah diatur dengan undang-undang.",
        "skor_expected_min": 8,
    }
]

# ==============================================================
# HELPER: kirim request ke API
# ==============================================================
def call_api(pertanyaan, nama_kontestan, jawaban_kontestan):
    payload = {
        "pertanyaan": pertanyaan,
        "nama_kontestan": nama_kontestan,
        "jawaban_kontestan": jawaban_kontestan,
    }
    start = time.time()
    resp = requests.post(API_URL, json=payload, timeout=60)
    elapsed = time.time() - start
    resp.raise_for_status()
    return resp.json(), elapsed

# ==============================================================
# HELPER: cek apakah skor sesuai ekspektasi
# ==============================================================
def check_score(result_skor, item):
    exp_min = item.get("skor_expected_min")
    exp_max = item.get("skor_expected_max")
    if exp_min is not None and exp_max is not None:
        return exp_min <= result_skor <= exp_max
    if exp_min is not None:
        return result_skor >= exp_min
    if exp_max is not None:
        return result_skor <= exp_max
    return True

def label_expected(item):
    exp_min = item.get("skor_expected_min")
    exp_max = item.get("skor_expected_max")
    if exp_min is not None and exp_max is None:
        return f">= {exp_min}"
    if exp_max is not None and exp_min is None:
        return f"<= {exp_max}"
    return f"{exp_min}–{exp_max}"

# ==============================================================
# MAIN
# ==============================================================
def main():
    print("=" * 60)
    print("EVALUASI LLM END-TO-END - SmartJuri-AI")
    print(f"Endpoint : {API_URL}")
    print(f"Jumlah kasus: {len(TEST_SET)}")
    print("=" * 60)

    # Cek koneksi dulu
    try:
        requests.get("http://localhost:8000/docs", timeout=5)
        print("[OK] Backend terhubung\n")
    except Exception:
        print("[ERROR] Backend tidak bisa diakses!")
        print("  Pastikan python main.py sudah dijalankan.")
        return

    per_case_results = []
    passed = 0
    total_skor = 0
    total_latency = 0

    for item in TEST_SET:
        qid  = item["id"]
        cat  = item["kategori"]
        print(f"[{qid:02d}] [{cat}]")
        print(f"      Jawaban peserta: \"{item['jawaban_kontestan'][:60]}\"")

        try:
            result, elapsed = call_api(
                item["pertanyaan"],
                item["nama_kontestan"],
                item["jawaban_kontestan"],
            )

            skor   = result.get("skor", -1)
            alasan = result.get("alasan", "")
            kunci  = result.get("kunci_jawaban", "")
            sumber = result.get("sumber_dokumen", "")

            ok = check_score(skor, item)
            if ok:
                passed += 1
                status = "PASS"
            else:
                status = "FAIL"

            total_skor += skor
            total_latency += elapsed

            print(f"      Skor LLM  : {skor}/10  (ekspektasi {label_expected(item)}) → {status}")
            print(f"      Sumber    : {sumber}")
            print(f"      Alasan    : {alasan[:100]}...")
            print(f"      Latency   : {elapsed:.2f}s\n")

            per_case_results.append({
                "id": qid,
                "kategori": cat,
                "pertanyaan": item["pertanyaan"],
                "jawaban_kontestan": item["jawaban_kontestan"],
                "kunci_jawaban_llm": kunci,
                "sumber_dokumen": sumber,
                "skor_llm": skor,
                "skor_expected": label_expected(item),
                "alasan": alasan,
                "latency_s": round(elapsed, 3),
                "status": status,
            })

        except Exception as e:
            print(f"      [ERROR] {e}\n")
            per_case_results.append({
                "id": qid,
                "kategori": cat,
                "pertanyaan": item["pertanyaan"],
                "jawaban_kontestan": item["jawaban_kontestan"],
                "error": str(e),
                "status": "ERROR",
            })

    # ===========================================================
    # RINGKASAN
    # ===========================================================
    n = len(TEST_SET)
    accuracy = passed / n
    avg_skor = total_skor / n
    avg_latency = total_latency / n

    # Hitung per kategori
    cat_results = {}
    for r in per_case_results:
        c = r["kategori"]
        if c not in cat_results:
            cat_results[c] = {"pass": 0, "total": 0}
        cat_results[c]["total"] += 1
        if r.get("status") == "PASS":
            cat_results[c]["pass"] += 1

    print("=" * 60)
    print("RINGKASAN EVALUASI LLM")
    print("=" * 60)
    print(f"  Akurasi penilaian : {passed}/{n} ({accuracy*100:.0f}%)")
    print(f"  Rata-rata skor    : {avg_skor:.1f}/10")
    print(f"  Rata-rata latency : {avg_latency:.2f}s")
    print()
    print("  Per kategori:")
    for cat, v in cat_results.items():
        pct = v['pass']/v['total']*100
        print(f"    {cat:<30} {v['pass']}/{v['total']} ({pct:.0f}%)")

    print()
    if accuracy >= 0.8:
        verdict = "BAIK - LLM menilai jawaban secara konsisten dan adil"
    elif accuracy >= 0.6:
        verdict = "CUKUP - Ada beberapa kasus penilaian yang perlu diperbaiki"
    else:
        verdict = "KURANG - Prompt engineering perlu direvisi ulang"
    print(f"  Verdict: {verdict}")
    print("=" * 60)

    # Simpan JSON
    output = {
        "summary": {
            "model_llm": "llama-3.3-70b-versatile (via Groq)",
            "model_embedding": "paraphrase-multilingual-MiniLM-L12-v2",
            "n_cases": n,
            "passed": passed,
            "accuracy": round(accuracy, 4),
            "avg_skor_llm": round(avg_skor, 2),
            "avg_latency_s": round(avg_latency, 2),
            "per_kategori": cat_results,
            "verdict": verdict,
        },
        "per_case": per_case_results,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nHasil detail tersimpan di: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()