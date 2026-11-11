import os
import sys
import time
import requests

api_key = os.environ.get("GEMINI_API_KEY")
title = os.environ.get("ISSUE_TITLE", "")
body = os.environ.get("ISSUE_BODY", "")
prompt = f"{title}\n{body}".strip()

if not api_key:
    print("Error: GEMINI_API_KEY belum diset di GitHub Secrets!")
    sys.exit(1)

if not os.path.exists("index.html"):
    print("Error: File index.html tidak ditemukan!")
    sys.exit(1)

with open("index.html", "r", encoding="utf-8") as f:
    current_html = f.read()

# Model fallback jika salah satu overload (503) atau deprecated (404)
models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-3.8-flash"]
headers = {"Content-Type": "application/json"}

system_instruction = (
    "Kamu adalah web developer frontend profesional untuk ARBI SHOP. "
    "Tugasmu memodifikasi kode index.html sesuai instruksi permintaan.\n"
    "ATURAN WAJIB:\n"
    "1. Kembalikan HANYA kode HTML utuh dari <!DOCTYPE html> sampai </html>.\n"
    "2. DILARANG menambahkan markdown backticks seperti ```html atau ```.\n"
    "3. DILARANG menambahkan teks pengantar/penutup apa pun.\n"
    "4. Pertahankan semua fitur JS, styling Tailwind, QRIS, link WA, dan modal agar tetap berfungsi normal."
)

payload = {
    "contents": [{"parts": [{"text": f"KODE SAAT INI:\n{current_html}\n\nPERINTAH REVISI:\n{prompt}"}]}],
    "systemInstruction": {"parts": [{"text": system_instruction}]},
    "generationConfig": {"temperature": 0.2}
}

res_data = None
for model in models:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    print(f"--> Menghubungi model: {model}...")
    
    success = False
    for attempt in range(1, 4):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                res_data = resp.json()
                success = True
                print(f"Sukses diproses oleh {model}!")
                break
            elif resp.status_code in [500, 502, 503, 504]:
                print(f"Server sibuk (HTTP {resp.status_code}). Percobaan {attempt}/3, menunggu 4 detik...")
                time.sleep(4)
            elif resp.status_code == 404:
                print(f"Model {model} tidak tersedia (404), beralih ke model lain...")
                break
            else:
                print(f"HTTP {resp.status_code}: {resp.text}")
                break
        except Exception as e:
            print(f"Koneksi timeout/error: {e}. Menunggu 3 detik...")
            time.sleep(3)

    if success:
        break

if not res_data or "candidates" not in res_data:
    print("Error: Semua model Gemini gagal merespons.")
    sys.exit(1)

new_code = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()

# Bersihkan markdown formatting
if new_code.startswith("```html"):
    new_code = new_code[7:]
elif new_code.startswith("```"):
    new_code = new_code[3:]
if new_code.endswith("```"):
    new_code = new_code[:-3]
new_code = new_code.strip()

if "<!DOCTYPE html>" in new_code and "</html>" in new_code.lower():
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(new_code)
    print("index.html sukses diperbarui!")
else:
    print("Error: Output AI tidak valid atau terpotong.")
    sys.exit(1)
