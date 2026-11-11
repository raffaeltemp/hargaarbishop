import os
import re
import sys
import requests

api_key = os.environ.get("GEMINI_API_KEY")
title = os.environ.get("ISSUE_TITLE", "")
body = os.environ.get("ISSUE_BODY", "")
prompt = f"{title}\n{body}".strip()

if not api_key:
    print("Error: GEMINI_API_KEY belum diset di GitHub Secrets!")
    sys.exit(1)

if not os.path.exists("index.html"):
    print("Error: index.html tidak ditemukan!")
    sys.exit(1)

with open("index.html", "r", encoding="utf-8") as f:
    current_html = f.read()

# Langsung tembak model aktif tanpa muter-muter
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
headers = {"Content-Type": "application/json"}

system_instruction = (
    "Kamu adalah web developer frontend untuk ARBI SHOP. Tugasmu memodifikasi index.html sesuai instruksi.\n"
    "ATURAN AGAR SANGAT CEPAT:\n"
    "DILARANG MENGETIK ULANG SELURUH FILE HTML!\n"
    "Kembalikan HANYA blok penggantian (search & replace) dengan format persis seperti ini:\n"
    "<<<<<<< SEARCH\n"
    "[potongan kode persis yang ingin diganti dari file asli]\n"
    "=======\n"
    "[kode baru penggantinya]\n"
    ">>>>>>>\n\n"
    "Kamu boleh membuat lebih dari satu blok SEARCH/REPLACE jika ada beberapa bagian berbeda yang diubah.\n"
    "Dilarang menambahkan teks pengantar, salam, atau penjelasan apa pun."
)

payload = {
    "contents": [{
        "parts": [{"text": f"FILE index.html SAAT INI:\n{current_html}\n\nPERINTAH:\n{prompt}"}]
    }],
    "systemInstruction": {"parts": [{"text": system_instruction}]},
    "generationConfig": {"temperature": 0.1}
}

print("--> Menghubungi Gemini 3.8-flash (Mode Cepat Search & Replace)...")
try:
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
except Exception as e:
    print(f"Koneksi timeout/error: {e}")
    sys.exit(1)

if resp.status_code != 200:
    print(f"Error Gemini API (HTTP {resp.status_code}): {resp.text}")
    sys.exit(1)

result = resp.json()
ai_output = result["candidates"][0]["content"]["parts"][0]["text"].strip()

# Bersihkan format backticks jika ada
ai_output = re.sub(r"^```[a-zA-Z]*\n", "", ai_output)
ai_output = re.sub(r"\n```$", "", ai_output).strip()

# Eksekusi blok SEARCH & REPLACE
pattern = r"<<<<<<< SEARCH\r?\n(.*?)\r?\n=======\r?\n(.*?)\r?\n>>>>>>>"
matches = list(re.finditer(pattern, ai_output, re.DOTALL))

if matches:
    new_html = current_html
    replaced_count = 0
    for match in matches:
        search_text = match.group(1)
        replace_text = match.group(2)
        if search_text in new_html:
            new_html = new_html.replace(search_text, replace_text, 1)
            replaced_count += 1
        else:
            # Toleransi newline Windows/Linux
            norm_search = search_text.replace("\r\n", "\n")
            norm_current = new_html.replace("\r\n", "\n")
            if norm_search in norm_current:
                new_html = norm_current.replace(norm_search, replace_text.replace("\r\n", "\n"), 1)
                replaced_count += 1
            else:
                print(f"Peringatan: Blok kode berikut tidak cocok:\n{search_text[:60]}...")

    if replaced_count > 0:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(new_html)
        print(f"Sukses! {replaced_count} bagian berhasil diperbarui secara instan!")
        sys.exit(0)

# Fallback jika sewaktu-waktu AI tetap mengirim full HTML
if "<!DOCTYPE html>" in ai_output and "</html>" in ai_output.lower():
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(ai_output)
    print("Sukses memperbarui file index.html secara penuh!")
    sys.exit(0)

print("Format output AI tidak dapat diterapkan:")
print(ai_output[:200])
sys.exit(1)
