import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import gspread
import os
import json
import time
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
    "news.cgtn.com": "CGTN",
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
    "tap.info.tn": "Tunis Afrique Presse",
    "dailynewsegypt.com": "Daily News Egypt",
    "bricslat.com": "BRICSLat",
    "china.com": "China.com",
    "atnews.co.za": "African Times",
    "telesurtv.net": "teleSUR",
    "dknews.kz": "Деловой Казахстан",
    "info-rm.com": "Мордовия 24",
    "dbw.cn": "Дунбэйван",
    "ahorasanjuan.com": "Ahora San Juan",
    "prensa-latina.cu": "Prensa Latina",
    "brasil247.com": "Brasil 247",
    "zbc.co.zw": "Zimbabwe Broadcasting Corporation",
    "ians.in": "IANS",
    "todapalavra.info": "Toda Palavra",
    "chinadaily.com.cn": "China Daily",
    "iol.co.za": "Pretoria News",
    "itmexpo.ru": "Интурмаркет",
    "durbantv.net": "Durban TV",
    "trinitymirror.net": "Trinity Mirror",
    "metropoles.com": "Metropoles",
    "people.com.cn": "Жэньминь жибао",
    "news.cn": "СИНЬХУА Новости",
    "tvcultura.com.br": "TV CULTURA",
    "africannewsagency.com": "ANA"
}

partners = {k.strip().lower(): v.strip() for k, v in partners.items()}

# =========================
# LANGUAGE
# =========================
LANG_MAP = {
    "tvbrics.com/en/": "en",
    "tvbrics.com/cn/": "cn",
    "tvbrics.com/pt/": "pt",
    "tvbrics.com/es/": "es",
    "tvbrics.com/ar/": "ar",
    "tvbrics.com/": "ru",
}

def get_language(url):
    for k, v in LANG_MAP.items():
        if k in url:
            return v
    return "ru"

# =========================
# MONTH
# =========================
def parse_month(date_str):
    if not date_str:
        return ""

    import re

    m = re.search(r"(\d{2,4})年(\d{1,2})月", date_str)
    if m:
        return int(m.group(2))

    try:
        dt = datetime.strptime(date_str, "%d.%m.%y")
        return dt.month
    except:
        return ""

# =========================
# PARTNER MATCH
# =========================
def get_partner(url):
    domain = urlparse(url).netloc.lower().strip()
    for d, name in partners.items():
        if domain.endswith(d):
            return name
    return ""

# =========================
# FETCH WITH RETRY
# =========================
def fetch(url, retries=3, timeout=10):
    for _ in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
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
        return "Сайт не работает, попробуйте позже", "", [], []

    soup = BeautifulSoup(html, "html.parser")

    date_tag = soup.find("span", class_="data_row__date")
    date = date_tag.get_text(strip=True) if date_tag else ""

    title_tag = soup.find("h1", class_="news-detail__name")
    title = title_tag.get_text(strip=True) if title_tag else ""

    links = []
    partners_list = []
    seen = set()

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
            partners_list.append(partner)

        if len(links) >= 10:
            break

    return date, title, links, partners_list

# =========================
# MAIN (TRIGGER MODE)
# =========================

def process_row(row_number: int):

    row = worksheet.row_values(row_number)

    url = row[1] if len(row) > 1 else ""

    if not url:
        print("[SKIP] empty url")
        return

    print(f"[INFO] processing row={row_number} url={url}")

    date, title, links, partners_found = parse(url)

    language = get_language(url)
    month = parse_month(date)

    TOTAL_COLS = 29
    MAX_LINKS = 10

    row_data = [""] * TOTAL_COLS

    row_data[0] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_data[1] = url
    row_data[2] = date
    row_data[3] = title

    for idx in range(MAX_LINKS):
        row_data[4 + idx * 2] = links[idx] if idx < len(links) else ""
        row_data[5 + idx * 2] = partners_found[idx] if idx < len(partners_found) else ""

    row_data[26] = "DONE"
    row_data[27] = language
    row_data[28] = month

    worksheet.update(f"A{row_number}:AC{row_number}", [row_data])

    print(f"[SUCCESS] row {row_number} processed")

# =========================
# ENTRY POINT (FROM TRIGGER)
# =========================

if __name__ == "__main__":

    # 👇 сюда Google Sheets trigger должен передавать row number
    import sys

    if len(sys.argv) < 2:
        print("[ERROR] row number not provided")
        exit(1)

    row_number = int(sys.argv[1])

    process_row(row_number)


    print("[INFO] nothing to update")
