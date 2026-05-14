# main-project
Sistem Penilai Otomatis Lomba Cerdas Cermat Berbasis RAG (Retrieval-Augmented Generation) untuk Mitigasi Human Error dan Bias Penjurian

# Setup Project

## 1. Clone Repository

```bash
git clone https://github.com/NLP-9/main-project.git
cd main-project
```

## 2. Install Dependency

```bash
pip install -r requirements.txt
```

## 3. Jalankan Ingest

Script ini digunakan untuk membuat vector database dari data pada folder `Data`.

```bash
python ingest.py
```

## 4. Retrieval Test (Opsional)

Digunakan untuk testing semantic retrieval.

```bash
python retrieval_test.py
```

# Catatan

Folder berikut tidak disertakan karena merupakan hasil generate lokal:

```plaintext
__pycache__/
vectordb/
```

Jika vector database belum ada, jalankan kembali:

```bash
python ingest.py
```