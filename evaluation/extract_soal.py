"""
extract_soal.py — Ekstrak soal & jawaban dari PDF untuk evaluasi LLM
Jalankan: python extract_soal.py
Output  : soal_jawaban_extracted.txt (preview isi PDF)
"""

from pathlib import Path
import sys

# Cari file PDF di folder Data
SEARCH_PATHS = [
    Path("Data/Contoh Soal/soal_jawaban_4_pilar_kebangsaan.pdf"),
    Path("Data/Contoh Soal/Soal_Jawaban_LCC_4_Pilar_Kebangsaan.pdf"),
]

pdf_path = None
for p in SEARCH_PATHS:
    if p.exists():
        pdf_path = p
        break

if not pdf_path:
    # Cari semua PDF di folder Contoh Soal
    contoh_soal_dir = Path("Data/Contoh Soal")
    if contoh_soal_dir.exists():
        pdfs = list(contoh_soal_dir.glob("*.pdf"))
        print(f"PDF ditemukan di folder Contoh Soal:")
        for p in pdfs:
            print(f"  - {p}")
        if pdfs:
            pdf_path = pdfs[0]
            print(f"\nMenggunakan: {pdf_path}\n")
    if not pdf_path:
        print("[ERROR] File PDF tidak ditemukan!")
        sys.exit(1)

print(f"Membaca: {pdf_path}")
print("=" * 60)

try:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Jumlah halaman: {len(pdf.pages)}\n")
        full_text = ""
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                full_text += f"\n--- HALAMAN {i+1} ---\n{text}"

    # Simpan ke txt
    out = Path("soal_jawaban_extracted.txt")
    out.write_text(full_text, encoding="utf-8")
    print(full_text[:3000])  # preview 3000 karakter pertama
    print(f"\n... (lihat soal_jawaban_extracted.txt untuk teks lengkap)")
    print(f"\nBerhasil! Total karakter: {len(full_text)}")

except ImportError:
    print("pdfplumber belum terinstall, mencoba pypdf...")
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        print(f"Jumlah halaman: {len(reader.pages)}\n")
        full_text = ""
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text += f"\n--- HALAMAN {i+1} ---\n{text}"
        out = Path("soal_jawaban_extracted.txt")
        out.write_text(full_text, encoding="utf-8")
        print(full_text[:3000])
        print(f"\n... (lihat soal_jawaban_extracted.txt untuk teks lengkap)")
        print(f"\nBerhasil! Total karakter: {len(full_text)}")
    except ImportError:
        print("Install dulu: pip install pdfplumber")