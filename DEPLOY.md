# Deploy Bot Discord ke Oracle Cloud Free Tier (Gratis Selamanya)

Oracle Cloud Free Tier ngasih VM gratis permanen (Always Free), bukan trial yang expired.
Spesifikasi cukup buat bot Discord + Groq API (yang berat ada di sisi Groq, bukan VM kamu).

---

## Bagian 1: Bikin Akun & VM di Oracle Cloud

### 1. Daftar akun
1. Buka https://signup.oraclecloud.com
2. Isi data diri, verifikasi email & nomor HP
3. Masukkan kartu kredit/debit untuk verifikasi identitas — **ini hanya verifikasi, tidak akan ditagih selama kamu pakai resource "Always Free"**
4. Pilih Home Region (pilih yang terdekat, misal Singapore/Tokyo untuk latency lebih baik ke Indonesia)

### 2. Buat instance VM (Compute Instance)
1. Login ke OCI Console → menu ☰ → **Compute** → **Instances**
2. Klik **Create Instance**
3. Isi:
   - **Name**: `discord-bot` (bebas)
   - **Image**: pilih **Canonical Ubuntu 22.04** (klik "Change Image" kalau default beda)
   - **Shape**: klik "Change Shape" → pilih **Ampere (ARM)** → `VM.Standard.A1.Flex` → set **1 OCPU, 6 GB RAM** (ini masuk kuota Always Free, generous banget buat bot ringan)
     - *Alternatif*: kalau ARM region kamu penuh/gak tersedia, bisa pakai shape AMD `VM.Standard.E2.1.Micro` (lebih kecil tapi tetap cukup)
4. **Add SSH keys**: pilih **Generate a key pair for me**, lalu **download private key** (`.key` file) — simpan baik-baik, ini buat login nanti
5. Biarkan setting jaringan default, klik **Create**
6. Tunggu status jadi **Running** (~1-2 menit), lalu catat **Public IP Address** instance-nya

### 3. Buka port (kalau nanti perlu, opsional untuk bot ini)
Bot Discord ini gak butuh port terbuka ke internet (dia yang connect keluar ke Discord, bukan sebaliknya), jadi bagian ini bisa dilewati.

---

## Bagian 2: Masuk ke VM via SSH

### Di Windows (pakai PowerShell atau WSL)
```powershell
# ubah permission key dulu kalau perlu, lalu:
ssh -i "path\ke\private-key.key" ubuntu@ALAMAT_IP_VM
```

### Di Mac/Linux
```bash
chmod 400 path/ke/private-key.key
ssh -i path/ke/private-key.key ubuntu@ALAMAT_IP_VM
```

Kalau berhasil, kamu akan masuk ke terminal Ubuntu di VM.

---

## Bagian 3: Setup Bot di VM

### 1. Install Python & Git
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git
```

### 2. Upload kode bot ke VM

Cara termudah: pakai `scp` dari komputer kamu (bukan dari dalam VM). Buka terminal baru di laptop kamu:

```bash
scp -i path/ke/private-key.key -r discord-bot ubuntu@ALAMAT_IP_VM:~/
```

Ini akan copy seluruh folder `discord-bot` (bot.py, requirements.txt, dll) ke home directory VM.

### 3. Setup virtual environment & install dependencies
Kembali ke terminal SSH yang connect ke VM:
```bash
cd ~/discord-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Isi file `.env`
```bash
cp .env.example .env
nano .env
```
Isi dengan token asli kamu:
```
DISCORD_TOKEN=token_bot_discord_asli
GROQ_API_KEY=api_key_groq_asli
```
Simpan dengan `Ctrl+O`, Enter, lalu keluar dengan `Ctrl+X`.

### 5. Test jalankan bot
```bash
python bot.py
```
Kalau muncul `✅ Bot aktif sebagai ...` berarti sukses. Tekan `Ctrl+C` untuk stop dulu (kita mau setup auto-run).

---

## Bagian 4: Bikin Bot Jalan 24/7 (Auto-Restart)

Supaya bot tetap jalan walau kamu logout SSH atau VM restart, pakai **systemd service**.

### 1. Buat file service
```bash
sudo nano /etc/systemd/system/discordbot.service
```

Isi dengan (sesuaikan path kalau beda):
```ini
[Unit]
Description=Discord Assistant Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/discord-bot
ExecStart=/home/ubuntu/discord-bot/venv/bin/python /home/ubuntu/discord-bot/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Simpan (`Ctrl+O`, Enter, `Ctrl+X`).

### 2. Aktifkan & jalankan service
```bash
sudo systemctl daemon-reload
sudo systemctl enable discordbot
sudo systemctl start discordbot
```

### 3. Cek status & log
```bash
# cek apakah jalan
sudo systemctl status discordbot

# lihat log real-time
sudo journalctl -u discordbot -f
```

Sekarang bot akan:
- Otomatis jalan setiap kali VM boot
- Otomatis restart kalau crash
- Tetap jalan walau kamu logout dari SSH

---

## Bagian 5: Update Kode di Masa Depan

Kalau kamu edit `bot.py` di laptop dan mau update ke VM:
```bash
# dari laptop
scp -i path/ke/private-key.key discord-bot/bot.py ubuntu@ALAMAT_IP_VM:~/discord-bot/

# lalu di VM, restart service
sudo systemctl restart discordbot
```

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `Permission denied (publickey)` saat SSH | Cek path private key & permission (`chmod 400`) |
| Bot gak muncul online di Discord | Cek `sudo journalctl -u discordbot -f` untuk lihat error |
| Error `Privileged intent` | Pastikan **Message Content Intent** sudah diaktifkan di Discord Developer Portal |
| VM lambat/region ARM habis kuota | Coba region lain saat create instance, atau pakai shape AMD Micro |
| Kena limit Groq API | Free tier Groq ada rate limit per menit — biasanya cukup untuk pemakaian personal |

---

## Ringkasan Biaya
- Oracle Cloud VM (Always Free tier): **Rp 0**
- Groq API: **Rp 0** (dalam batas free tier)
- Total: **Gratis selamanya**, selama tetap pakai resource dalam kuota Always Free.
