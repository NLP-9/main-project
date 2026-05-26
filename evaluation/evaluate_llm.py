import argparse
import json
import time
from pathlib import Path

import requests

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

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
# CONFIG
# =========================================================

API_URL = "http://localhost:8000/api/evaluate"

OUTPUT_DIR = Path("evaluation_results")

OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / f"llm_{args.mode}_results.json"

# =========================================================
# MAIN EVALUATION
# =========================================================

results = []

passed = 0

for item in TEST_SET:

    payload = {

        "pertanyaan": item["question"],

        "nama_kontestan": "Peserta",

        "jawaban_kontestan": item["answer"]
    }

    start = time.time()

    response = requests.post(
        API_URL,
        json=payload,
        timeout=120
    )

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

    print("\n" + "=" * 60)

    print(item["question"])

    print(f"Skor      : {score}")

    print(f"Expected  : >= {item['min_score']}")

    print(f"PASS      : {is_pass}")

    print(f"Latency   : {latency:.2f}s")

    results.append({

        "question": item["question"],

        "score": score,

        "expected_min_score": item["min_score"],

        "passed": is_pass,

        "latency": round(latency, 3),

        "reason": data.get("alasan", "")
    })

# =========================================================
# SUMMARY
# =========================================================

accuracy = passed / len(TEST_SET)

summary = {

    "mode": args.mode,

    "accuracy": round(accuracy, 4),

    "passed": passed,

    "total": len(TEST_SET)
}

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

for k, v in summary.items():

    print(f"{k:<15}: {v}")

# =========================================================
# SAVE
# =========================================================

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    json.dump({

        "summary": summary,

        "details": results

    }, f, ensure_ascii=False, indent=2)

print(f"\nHasil disimpan ke: {OUTPUT_FILE}")