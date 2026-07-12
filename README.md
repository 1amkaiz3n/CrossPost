# CrossPost

**Self-hosted social media publisher** — upload konten sekali, publikasikan ke banyak platform secara otomatis.

> ⚠️ **PERINGATAN KEAMANAN**
>
> Project ini hanya cocok untuk **penggunaan lokal / development**. Tidak ada autentikasi pengguna, enkripsi data, atau proteksi akses yang memadai. **Jangan deploy ke publik** — credential API, token OAuth, dan data Anda bisa bocor. Gunakan hanya di localhost atau jaringan lokal yang aman.

---

## Fitur

### 📤 Multi-Platform Upload
Upload video dan gambar, lalu publikasikan ke berbagai platform sosial media sekaligus:

| Platform | Video | Gambar |
|----------|-------|--------|
| YouTube | ✅ | ❌ |
| Facebook (Page) | ✅ | ✅ |
| Instagram (Reels/Post) | ✅ | ✅ |
| LinkedIn | ✅ | ✅ |
| Threads | ✅ | ✅ |

### 🔗 OAuth Integration
Hubungkan akun platform sosial media melalui OAuth 2.0:
- Google / YouTube
- Meta (Facebook + Instagram)
- Threads
- LinkedIn

### 📅 Content Scheduling
Jadwalkan posting kapan saja. Konten akan otomatis dipublikasikan sesuai jadwal.

### 📊 Analytics & Statistik
Pantau performa konten dari semua platform dalam satu dashboard:
- Total views, likes, comments
- Breakdown per platform
- Grafik time-series
- Insights waktu terbaik posting

### 🔄 Background Sync
Sistem secara otomatis menyinkronkan statistik dan konten terbaru dari setiap platform secara berkala.

### 📁 File-Based Storage
Tidak perlu database server — semua data disimpan dalam file JSON. Cocok untuk self-hosted.

### 🎨 Dashboard UI
Antarmuka web modern dengan Tailwind CSS, mendukung tema terang dan gelap.

---

## Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Backend | Python 3.12 + FastAPI |
| ASGI Server | Uvicorn |
| Templating | Jinja2 |
| HTTP Client | httpx (async) |
| Frontend | Tailwind CSS + Font Awesome |
| Storage | JSON files |

---

## Cara Install

### 1. Clone repository

```bash
git clone https://github.com/username/crosspost.git
cd crosspost
```

### 2. Buat virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate     # Windows
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn jinja2 httpx python-dotenv python-multipart
```

### 4. Konfigurasi

Salin `.env.example` menjadi `.env` dan isi credential API masing-masing platform:

```bash
cp .env.example .env
```

### 5. Jalankan

```bash
uvicorn crosspost.main:app --host 0.0.0.0 --port 8000
```

Akses di `http://localhost:8000`

---

## Struktur Project

```
crosspost/
├── main.py                 # Entry point FastAPI
├── config.py               # Konfigurasi dari .env
├── app/
│   ├── oauth/              # OAuth flows per platform
│   ├── routers/            # API endpoints
│   ├── services/           # Business logic & integrasi
│   ├── utils/              # Utility (JSON DB, logger, validator)
│   ├── static/             # Aset statis (logo, dll)
│   └── templates/          # HTML Jinja2 templates
├── database/               # Data JSON (di-generate otomatis)
└── uploads/                # File media yang diupload
```

---

## Lisensi

MIT
