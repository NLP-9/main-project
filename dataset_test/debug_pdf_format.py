"""
debug_table.py — Cek hasil extract_table() untuk Dataset_QA
Jalankan: python debug_table.py
"""
from pathlib import Path
import pdfplumber

pdf_path = Path("../Data/Contoh Soal/Dataset_QA_LCC_MPR_RI_2024_2025.pdf")

with pdfplumber.open(pdf_path) as pdf:
    print(f"Jumlah halaman: {len(pdf.pages)}\n")
    for i, page in enumerate(pdf.pages[:3]):
        print(f"=== HALAMAN {i+1} ===")

        # Coba extract_table default
        tables = page.extract_tables()
        print(f"Jumlah tabel (default): {len(tables)}")
        if tables:
            for t in tables[:1]:
                for row in t[:3]:
                    print(f"  ROW: {row}")
        print()

        # Coba dengan setting toleran
        tables2 = page.extract_tables(table_settings={
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "snap_tolerance": 5,
            "join_tolerance": 5,
        })
        print(f"Jumlah tabel (text strategy): {len(tables2)}")
        if tables2:
            for t in tables2[:1]:
                for row in t[:3]:
                    print(f"  ROW: {row}")
        print()

        # Coba extract_text_lines untuk lihat struktur
        print("Words per halaman (5 pertama):")
        words = page.extract_words()
        for w in words[:10]:
            print(f"  x0={w['x0']:.0f} top={w['top']:.0f} text={w['text']}")
        print()