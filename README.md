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

Pastikan setelah clone repository, folder berikut ada:

```plaintext
vectordb/
```

## 4. Retrieval Test

Digunakan untuk testing semantic retrieval dari vector database yang sudah tersedia.

```bash
python retrieval_test.py
```

## 5. Jalankan Ingest Ulang Jika Diperlukan

Script `ingest.py` hanya perlu dijalankan jika isi folder `Data` berubah atau ingin membuat ulang vector database.

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

```bash
cd smartjuri-frontend
npm i
npm lucide-react
npm run dev
```

Buka localhost:3000
