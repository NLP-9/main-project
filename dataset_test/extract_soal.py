"""
extract_soal.py — Extract soal & jawaban dari PDF LCC Empat Pilar
Jalankan: python extract_soal.py
Output  : auto_question.json
"""

import re
import json
from pathlib import Path
import pdfplumber

print("=" * 60)
print("EXTRACTING QUESTIONS FROM PDF")
print("=" * 60)

# Resolve paths relative to this file's location to prevent CWD dependency issues
current_dir = Path(__file__).parent.resolve()
pdf_folder = current_dir.parent / "Data" / "Contoh Soal"
pdf_files = sorted(set(pdf_folder.rglob("*.[pP][dD][fF]")))

# ──────────────────────────────────────────────────────────────
# HELPER
# ──────────────────────────────────────────────────────────────
def extract_pages(pdf_path):
    """Ekstrak teks per halaman, kembalikan list string."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text.strip())
    return pages

def clean_text(text):
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def clean_question(text):
    # Hapus nomor di depan (seperti 1. atau 1) )
    text = re.sub(r'^\d{1,3}[\.\)]\s*', '', text.strip())
    # Hapus simbol ✔ atau ? atau \u2714 di depan
    text = re.sub(r'^[✔\?\u2714]\s*', '', text.strip())
    # Hapus angka referensi trailing yang didahului titik atau ellipsis (seperti …1)
    text = re.sub(r'\s*[…\.]+\s*\d{1,3}$', '', text.strip())
    # Hapus whitespace berlebih
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_answer(text):
    text = re.sub(r'^\d{1,3}[\.\)]\s*', '', text.strip())
    text = re.sub(r'^[✔\?\u2714]\s*', '', text.strip())
    text = re.sub(r'\s*[…\.]+\s*\d{1,3}$', '', text.strip())
    text = text.strip('"').strip("'").strip()
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_valid(q, a, min_q=20, min_a=3):
    return len(q) >= min_q and len(a) >= min_a

# ──────────────────────────────────────────────────────────────
# PARSER 1: Format "Q1. pertanyaan \n n jawaban"
# soal_jawaban_4_pilar_kebangsaan.pdf
# ──────────────────────────────────────────────────────────────
def parse_format_q_n(full_text):
    results = []
    raw_blocks = re.split(r'(?=\nQ\d+\.)', '\n' + full_text)
    for block in raw_blocks:
        block = block.strip()
        if not re.match(r'^Q\d+\.', block):
            continue

        lines = block.split('\n')
        q_lines, a_lines = [], []
        in_answer = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(r'^Q\d+\.', stripped):
                q_lines.append(re.sub(r'^Q\d+\.\s*', '', stripped))
                in_answer = False
            elif re.match(r'^n\s+\S', stripped):
                a_lines.append(re.sub(r'^n\s+', '', stripped))
                in_answer = True
            elif in_answer:
                a_lines.append(stripped)
            else:
                q_lines.append(stripped)

        q = ' '.join(q_lines).strip()
        a = ' '.join(a_lines).strip()

        q_clean = clean_question(q)
        a_clean = clean_answer(a)

        if is_valid(q_clean, a_clean):
            results.append({"question": q_clean, "answer": a_clean})
    return results

# ──────────────────────────────────────────────────────────────
# PARSER 2: Format "1. pertanyaan \n Jawaban: jawaban" (dengan page cleaning)
# Kumpulan-Soal-Lomba-Cerdas-Cermat-LCC-4-Pilar-MPR-RI.pdf
# ──────────────────────────────────────────────────────────────
def extract_and_clean_pages_lcc_mpr(pdf_path):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            clean_lines = []
            for line in text.split('\n'):
                line_str = line.strip()
                if not line_str:
                    continue
                
                # Filter headers
                if re.match(r'^(kumpulan soal tanya jawab|lomba cerdas cermat|babak satu lawan satu|babak benar salah|babak topik kasus)', line_str, re.IGNORECASE):
                    continue
                if "empat pilar - mpr ri" in line_str.lower() or "empat pilar kehidupan berbangsa" in line_str.lower():
                    continue
                
                # Filter footnotes
                if re.match(r'^\d{1,3}\s*\(', line_str) or "LCC_4_Pilar" in line_str or "Tingkat_Nasional" in line_str or "Penyisihan" in line_str or "Semi_Final" in line_str or "LCC_4_Pilar_MPR_RI" in line_str:
                    continue
                
                # Filter page numbers (only digits)
                if re.match(r'^\d+$', line_str):
                    continue
                
                clean_lines.append(line_str)
            
            pages.append('\n'.join(clean_lines))
    return '\n'.join(pages)

def parse_format_number_a(full_text):
    results = []
    # Split per nomor soal
    blocks = re.split(r'\n(?=\d{1,3}[\.\)]\s)', full_text)
    for block in blocks:
        block = block.strip()
        if not re.match(r'^\d{1,3}[\.\)]', block):
            continue
        
        # Pisah di "A:" atau "Jawaban:"
        qa = re.split(r'\n(?:A|Jawaban):\s*', block, maxsplit=1, flags=re.IGNORECASE)
        if len(qa) != 2:
            continue
        
        q = clean_question(qa[0])
        a = clean_answer(qa[1])
        
        if is_valid(q, a):
            results.append({"question": q, "answer": a})
    return results

# ──────────────────────────────────────────────────────────────
# PARSER 3: Format Tabel dengan Kolom "Pertanyaan" & "Jawaban"
# Dataset_QA_LCC_MPR_RI_2024_2025.pdf
# ──────────────────────────────────────────────────────────────
def parse_format_table_dataset_qa(pdf_path):
    questions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue
            
            main_table = max(tables, key=len)
            current_q = None
            
            for row in main_table:
                if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                    continue
                
                row_str = " ".join([str(cell) for cell in row if cell]).lower()
                if "pertanyaan" in row_str and "jawaban" in row_str:
                    continue
                
                def get_clean_val(indices):
                    for idx in indices:
                        if idx < len(row) and row[idx] is not None:
                            val = str(row[idx]).strip()
                            if val:
                                return val
                    return ""
                
                no_val = ""
                for i in [0, 1, 2]:
                    if len(row) > i and row[i] is not None:
                        val = str(row[i]).strip()
                        if re.match(r'^\d+$', val):
                            no_val = val
                            break
                            
                kat_val = str(row[3]).strip() if len(row) > 3 and row[3] is not None else ""
                q_val = get_clean_val([6, 7, 8])
                a_val = get_clean_val([9, 10, 11])
                
                no_match = re.match(r'^(\d+)', no_val)
                if no_match:
                    q_num = no_match.group(1)
                    if current_q:
                        questions.append(current_q)
                    current_q = {
                        "no": q_num,
                        "question": q_val,
                        "answer": a_val,
                    }
                else:
                    if current_q:
                        if q_val:
                            current_q["question"] = (current_q["question"] + " " + q_val).strip()
                        if a_val:
                            current_q["answer"] = (current_q["answer"] + " " + a_val).strip()
                            
            if current_q:
                questions.append(current_q)
                
    unique_qs = []
    seen = set()
    for q in questions:
        q_num = int(q["no"])
        if q_num not in seen:
            seen.add(q_num)
            
            q_clean = clean_question(q["question"])
            a_clean = clean_answer(q["answer"])
            if is_valid(q_clean, a_clean):
                unique_qs.append({"question": q_clean, "answer": a_clean})
            
    return unique_qs

# ──────────────────────────────────────────────────────────────
# PARSER 4: Format Tabel dengan Kolom "SOAL" & "JAWABAN"
# Soal_Jawaban_LCC_4_Pilar_Kebangsaan.pdf
# ──────────────────────────────────────────────────────────────
def parse_format_table_lcc_4pilar(pdf_path):
    questions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue
                
            for t in tables:
                row_str_0 = " ".join([str(cell) for cell in t[0] if cell]).lower()
                if "52 soal" in row_str_0 or "lcc 4 pilar" in row_str_0:
                    continue
                    
                current_q = None
                for row in t:
                    if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                        continue
                        
                    row_str = " ".join([str(cell) for cell in row if cell]).lower()
                    if "soal" in row_str and "jawaban" in row_str:
                        continue
                        
                    no_val = ""
                    q_val = ""
                    a_val = ""
                    
                    for i in range(min(3, len(row))):
                        if row[i] is not None:
                            val = str(row[i]).strip()
                            if re.match(r'^\d+$', val):
                                no_val = val
                                break
                                
                    if len(row) >= 8:
                        for idx in [3, 4, 5]:
                            if row[idx] is not None:
                                val = str(row[idx]).strip()
                                if val:
                                    q_val = val
                                    break
                        for idx in [6, 7, 8]:
                            if row[idx] is not None:
                                val = str(row[idx]).strip()
                                if val:
                                    a_val = val
                                    break
                    else:
                        val_str = " ".join([str(cell) for cell in row if cell]).strip()
                        if val_str:
                            if val_str.startswith('?') or val_str.startswith('✔') or val_str.startswith('\u2714'):
                                a_val = val_str
                            else:
                                q_val = val_str
                                
                    if no_val:
                        if current_q:
                            questions.append(current_q)
                        current_q = {
                            "no": no_val,
                            "question": q_val,
                            "answer": a_val,
                        }
                    else:
                        if current_q:
                            if q_val:
                                current_q["question"] = (current_q["question"] + " " + q_val).strip()
                            if a_val:
                                current_q["answer"] = (current_q["answer"] + " " + a_val).strip()
                                
                if current_q:
                    questions.append(current_q)
                    
    unique_qs = []
    seen = set()
    for q in questions:
        q_num = int(q["no"])
        if q_num not in seen:
            seen.add(q_num)
            
            q_clean = clean_question(q["question"])
            a_clean = clean_answer(q["answer"])
            if is_valid(q_clean, a_clean):
                unique_qs.append({"question": q_clean, "answer": a_clean})
            
    return unique_qs

# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
all_questions = []

for pdf_file in pdf_files:
    print(f"\nProcessing: {pdf_file.name}")
    try:
        # Deteksi tipe parser yang sesuai berdasarkan nama file
        name_lower = pdf_file.name.lower()
        if "dataset_qa_lcc_mpr" in name_lower:
            extracted = parse_format_table_dataset_qa(pdf_file)
        elif "soal_jawaban_lcc_4_pilar_kebangsaan" in name_lower:
            extracted = parse_format_table_lcc_4pilar(pdf_file)
        elif "soal_jawaban_4_pilar_kebangsaan" in name_lower:
            pages = extract_pages(pdf_file)
            full_text = clean_text('\n'.join(pages))
            extracted = parse_format_q_n(full_text)
        elif "kumpulan-soal-lomba-cerdas-cermat-lcc" in name_lower:
            full_text = extract_and_clean_pages_lcc_mpr(pdf_file)
            extracted = parse_format_number_a(full_text)
        else:
            print(f"  Warning: Format file {pdf_file.name} tidak dikenal. Lewati.")
            continue

        print(f"  Berhasil extract: {len(extracted)} soal")
        for item in extracted:
            item["source"] = pdf_file.name
            item["doc_type"] = "CONTOH_SOAL"
            item["min_score"] = 7
        all_questions.extend(extracted)
    except Exception as e:
        import traceback
        print(f"  Error: {e}")
        traceback.print_exc()

# Hapus duplikat berdasarkan 100 karakter pertama dari pertanyaan
seen, unique = set(), []
for item in all_questions:
    key = item["question"].lower().strip()[:100]
    if key not in seen:
        seen.add(key)
        unique.append(item)

print("\n" + "=" * 60)
print(f"TOTAL SOAL BERSIH: {len(unique)}")
print("=" * 60)

from collections import Counter
sources = Counter(item["source"] for item in unique)
for src, count in sources.items():
    print(f"  {src}: {count} soal")

output_path = current_dir / "auto_question.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(unique, f, ensure_ascii=False, indent=2)
print(f"\nDataset saved to: {output_path}")

# Preview 2 soal per sumber
print("\nCONTOH DATA (2 soal per sumber):\n")
shown = {}
for item in unique:
    src = item["source"]
    if shown.get(src, 0) >= 2:
        continue
    print(f"Sumber : {src}")
    print(f"Q: {item['question']}")
    print(f"A: {item['answer']}")
    print("-" * 50)
    shown[src] = shown.get(src, 0) + 1