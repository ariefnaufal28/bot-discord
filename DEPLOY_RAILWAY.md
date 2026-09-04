# Deploy Bot Discord ke Railway (Gratis $5 Kredit, ~30 Hari)

Railway gak butuh kartu kredit buat mulai. Kamu dapat $5 kredit gratis yang biasanya
cukup buat bot ringan jalan 24/7 selama beberapa minggu. Cocok buat testing dulu.

**Catatan penting**: setelah kredit $5 habis, Railway akan minta upgrade ke plan berbayar
(mulai $5/bulan) supaya bot tetap jalan. Jadi ini solusi sementara, bukan permanen.

---

## 1. Siapkan kode di GitHub (wajib untuk Railway)

Railway deploy dari repo GitHub. Kalau belum punya akun GitHub, daftar dulu di https://github.com (gratis).

### Upload folder bot ke GitHub
1. Buat repository baru di GitHub → beri nama misal `discord-bot` → set **Private** (biar token aman) → **Create repository**
2. Di komputer kamu, masuk ke folder `discord-bot` hasil extract zip tadi, lalu jalankan:

```bash
cd discord-bot
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME_KAMU/discord-bot.git
git push -u origin main
```

**PENTING**: Jangan pernah commit file `.env` (isi token asli) ke GitHub! Buat file `.gitignore` dulu:

```bash
echo ".env" > .gitignore
echo "venv/" >> .gitignore
git add .gitignore
git commit -m "Add gitignore"
git push
```

Kalau kamu sudah terlanjur commit `.env`, hapus dulu dari repo sebelum lanjut (atau buat repo baru).

---

## 2. Daftar & Buat Project di Railway

1. Buka https://railway.app → **Login** pakai akun GitHub kamu (paling gampang, otomatis connect)
2. Klik **New Project** → pilih **Deploy from GitHub repo**
3. Pilih repo `discord-bot` yang tadi di-push
4. Railway otomatis detect ini project Python dan mulai build

---

## 3. Set Environment Variables (Token)

1. Di dashboard project, klik service bot kamu
2. Masuk tab **Variables**
3. Tambahkan tiga variable:
   - `DISCORD_TOKEN` → isi token bot Discord asli
   - `GROQ_API_KEY` → isi API key Groq asli
   - `TAVILY_API_KEY` → isi API key Tavily (untuk fitur web search real-time)
4. Klik **Add** untuk masing-masing, Railway otomatis redeploy setelah variable ditambahkan

### Cara dapat API key Tavily (gratis, 1.000 pencarian/bulan)
1. Buka https://tavily.com → **Sign Up** (bisa pakai Google/GitHub, tanpa kartu kredit)
2. Setelah login, API key otomatis muncul di dashboard (format: `tvly-xxxxx`)
3. Copy key itu, tempel ke Variables Railway sebagai `TAVILY_API_KEY`

---

## 4. Pastikan Start Command Benar

Railway biasanya otomatis baca file `Procfile` yang isinya:
```
worker: python bot.py
```

Kalau Railway malah nyoba jalanin sebagai **web service** (nunggu port HTTP, biasanya bikin bot gagal start), cek:
1. Masuk tab **Settings** di service kamu
2. Scroll ke **Deploy** → **Custom Start Command**
3. Isi manual: `python bot.py`

---

## 5. Cek Log & Pastikan Bot Online

1. Klik tab **Deployments** → klik deployment yang aktif
2. Lihat **Logs** — kalau muncul `✅ Bot aktif sebagai ...` berarti sukses
3. Cek juga di Discord, status bot kamu harus jadi **Online**

---

## 6. Update Kode di Masa Depan

Setiap kali kamu push perubahan ke GitHub, Railway **otomatis redeploy**:
```bash
git add .
git commit -m "update bot"
git push
```

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| Build gagal, gak kedetect Python | Pastikan ada `requirements.txt` di root folder repo |
| Bot crash langsung setelah start | Cek Logs, biasanya karena `DISCORD_TOKEN`/`GROQ_API_KEY` belum diisi di Variables |
| Railway coba jalanin sebagai web server | Set Custom Start Command manual: `python bot.py` |
| Kredit $5 habis | Bot akan berhenti; upgrade ke Hobby plan ($5/bulan) atau pindah ke hosting gratis lain (Oracle Cloud) |
| `Application failed to respond` | Ini normal untuk bot Discord (bukan web app) — abaikan kalau bot tetap online di Discord, atau set service type ke "Worker" bukan "Web" di Settings |

---

## Cek Sisa Kredit

Buka https://railway.app/account/usage untuk lihat sisa kredit $5 kamu dan estimasi kapan habis.

---

## Rencana Jangka Panjang

Karena Railway ini sifatnya sementara (kredit terbatas), begitu urusan kartu debit BCA
kamu selesai (aktifkan transaksi online di CS BCA), pertimbangkan pindah ke **Oracle Cloud
Free Tier** yang gratis permanen — panduannya ada di file `DEPLOY.md`.
