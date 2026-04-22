import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import gspread
import os
import json
import time
import sys
from datetime import datetime
from google.oauth2.service_account import Credentials

# =========================
# AUTH
# =========================
creds_json = json.loads(os.environ["GOOGLE_CREDS"])

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    creds_json,
    scopes=SCOPES
)

gc = gspread.authorize(creds)

# =========================
# SHEET
# =========================
SHEET_ID = "1Dv0dSEoTHN3ri7CITXjZE7kOw-QU5ri9jLpcG8xApCo"
worksheet = gc.open_by_key(SHEET_ID).sheet1

# =========================
# PARTNERS
# =========================
partners = {
    "vision360.bo": "Visión 360",
    "cgtn.com": "CGTN",
    "news9live.com": "News9",
    "alalam.ir": "Alalam News Network",
    "inform.kz": "МИА Казинформ",
    "aninews.in": "ANI",
    "elbalad.news": "Sada El-Balad",
    "vnanet.vn": "Vietnam News Agency (VNA)",
    "news.by": "Белтелерадиокомпания",
    "volga24.tv": "Волга 24",
    "utrk.kg": "НТРК КР",
    "nournews.ir": "Nour News",
    "akchabar.kg": "Акчабар",
    "tvri.go.id": "TVRI",
    "thediplomaticsociety.co.za": "The Diplomatic Society",
    "boliviatv.bo": "BOLIVIA TV",
    "brasildefato.com.br": "Brasil de Fato",
    "thaipbs.or.th": "Thai PBS",
    "grupormultimedio.com": "Diario la R",
    "elmaipo.cl": "El Maipo",
    "tabnak.ir": "Tabnak",
    "bernama.com": "Bernama",
    "canal6tv.com": "Canal 6 Tv",
    "nannews.ng": "News Agency of Nigeria",
    "tv9.com": "TV9",
    "elbaladtv.net": "Sada El Balad",
    "globaltimes.cn": "Global Times",
    "herald.co.zw": "The Herald",
    "mena.org.eg": "MENA",
    "belta.by": "БелТА",
    "wam.ae": "WAM",
    "elciudadano.com": "El Ciudadano",
    "cronicadigital.cl": "Crónica Digital",
    "irna.ir": "IRNA",
    "mehrnews.com": "Mehr Media Group",
    "chinadaily.com.cn": "China Daily",
    "news.cn": "СИНЬХУА Новости",
    "people.com.cn": "Жэньминь жибао",
    "prensa-latina.cu": "Prensa Latina",
    "brasil247.com": "Brasil 247",
    "telesurtv.net": "teleSUR",
    "china.com": "China.com"
}

partners = {k.lower(): v for k, v in partners.items()}

# =========================
# HELPERS
# =========================
def get_partner(url):
    domain = urlparse(url).netloc.lower()
    for d, name in partners.items():
        if domain.endswith(d):
            return name
    return ""

def get_language(url):
    if "tvbrics.com/en/" in url:
        return "en"
    if "tvbrics.com/cn/" in url:
        return "cn"
    if "tvbrics.com/pt/" in url:
        return "pt"
    if "tvbrics.com/es/" in url:
        return "es"
    if "tvbrics.com/ar/" in url:
        return "ar"
    return "ru"

def parse_month(date_str):
    import re
    if not date_str:
        return ""

    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", date_str)
    if m:
        return int(m.group(2))

    return ""

# =========================
# FETCH
# =========================
def fetch(url):
    for _ in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code == 200:
                return r.text
        except:
            time.sleep(1)
    return None

# =========================
# PARSE PAGE
# =========================
def parse(url):
    html = fetch(url)

    if not html:
        print("[WARN] site not reachable:", url)
        return "", "", [], []

    soup = BeautifulSoup(html, "html.parser")

    date_tag = soup.find("span", class_="data_row__date")
    date = date_tag.get_text(strip=True) if date_tag else ""

    title_tag = soup.find("h1", class_="news-detail__name")
    title = title_tag.get_text(strip=True) if title_tag else ""

    links, partners_found, seen = [], [], set()

    for a in soup.find_all("a", href=True):
        link = urljoin(url, a["href"])

        if "tvbrics.com" in link:
            continue

        if link in seen:
            continue

        partner = get_partner(link)

        if partner:
            seen.add(link)
            links.append(link)
            partners_found.append(partner)

        if len(links) >= 10:
            break

    return date, title, links, partners_found

# =========================
# PROCESS ROW
# =========================
def process_row(row_number: int):

    row = worksheet.row_values(row_number)

    if len(row) < 2 or not row[1]:
        print("[SKIP] empty row/url")
        return

    # защита от повторной обработки
    if len(row) > 26 and row[26] == "DONE":
        print("[SKIP] already done")
        return

    url = row[1]

    print(f"[INFO] processing row={row_number} url={url}")

    date, title, links, partners_found = parse(url)

    TOTAL_COLS = 29
    MAX_LINKS = 10

    row_data = [""] * TOTAL_COLS

    row_data[0] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_data[1] = url
    row_data[2] = date
    row_data[3] = title

    for i in range(MAX_LINKS):
        row_data[4 + i * 2] = links[i] if i < len(links) else ""
        row_data[5 + i * 2] = partners_found[i] if i < len(partners_found) else ""

    row_data[26] = "DONE"
    row_data[27] = get_language(url)
    row_data[28] = parse_month(date)

    worksheet.update(f"A{row_number}:AC{row_number}", [row_data])

    print(f"[SUCCESS] row {row_number} done")

# =========================
# ENTRY POINT (GITHUB ACTIONS)
# =========================
if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("[ERROR] row number not provided")
        sys.exit(1)

    try:
        row_number = int(sys.argv[1])
        process_row(row_number)
    except Exception as e:
        print("[FATAL ERROR]", str(e))
        sys.exit(1)
