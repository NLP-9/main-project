# main-project

Sistem Penilai Otomatis Lomba Cerdas Cermat Berbasis RAG (Retrieval-Augmented Generation) untuk Mitigasi Human Error dan Bias Penjurian.

# Setup Project

## 1. Clone Repository

```bash
git clone https://github.com/NLP-9/main-project.git
cd main-project
```

## 2. Buat venv (opsional) dan Install Dependency

```bash
(opsional) python -m venv venv
(opsional) venv/Scripts/activate
pip install -r requirements.txt
```

## 3. Vector Database

Folder `vectordb/` sudah disertakan di repository, jadi tidak perlu menjalankan proses ingest ulang untuk mulai mengembangkan project ini.

Vector database saat ini dibuat dengan konfigurasi retrieval terbaru:

- Model embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- Chunk size: `700`
- Chunk overlap: `140`
- Collection name: `dokumen_kewarganegaraan`
- Retrieval: hybrid search dari `retrieval_core.py` (semantic + keyword/phrase matching + query expansion)

Pastikan setelah clone repository, folder berikut ada:

```plaintext
vectordb/
|-- chroma.sqlite3
`-- <folder-index-aktif>/
```

## 4. Retrieval Test

Digunakan untuk testing hybrid retrieval dari vector database yang sudah tersedia.

```bash
python retrieval_test.py
```

## 5. Jalankan Ingest Ulang Jika Diperlukan

Script `ingest.py` hanya perlu dijalankan jika isi folder `Data` berubah atau ingin membuat ulang vector database.

Jika model embedding belum ada di cache lokal, proses pertama kali bisa mengunduh model dari HuggingFace. Jika ingin menjalankan mode offline setelah model tersedia, set environment variable `HF_HUB_OFFLINE=1` dan `TRANSFORMERS_OFFLINE=1`.

Data yang digunakan berasal dari folder:

```plaintext
Data/
|-- Contoh Soal/
|-- Empat Pilar MPR RI/
|-- TAP MPR/
`-- UUD/
```

Untuk membuat ulang `vectordb/`, jalankan:

```bash
python ingest.py
```

## 6. Jalankan Backend: main.py

```bash
python main.py
```

Buka localhost:8000/docs

## 7. Jalankan Frontend

Buka terminal baru (ctrl + shift + 5)
deactivate venv dulu kalo tadi pake venv

ketik aja deactivate

```bash
cd smartjuri-frontend
npm i
npm lucide-react
npm run dev
```

Buka localhost:3000
