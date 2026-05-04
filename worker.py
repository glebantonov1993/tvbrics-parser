import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import gspread
import os
import json
import time
import re
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
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.sheet1

# =========================
# DATE NORMALIZER
# =========================
def normalize_date(date_str):
    if not date_str:
        return ""

    m = re.search(r"(\d{2,4})年(\d{1,2})月(\d{1,2})日", date_str)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        if year < 100:
            year += 2000
        try:
            dt = datetime(year, month, day)
            return dt.strftime("%d.%m.%y")
        except:
            return date_str

    try:
        dt = datetime.strptime(date_str, "%d.%m.%y")
        return dt.strftime("%d.%m.%y")
    except:
        return date_str

# =========================
# PARTNERS
# =========================
partners = {
    "vision360.bo": "Visión 360",
    "fanamc.com": "Fana Media Corporation",
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


partners = {k.lower(): v for k, v in partners.items()}

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
    try:
        dt = datetime.strptime(date_str, "%d.%m.%y")
        return dt.month
    except:
        return ""

# =========================
# PARTNER MATCH
# =========================
def get_partner(url):
    domain = urlparse(url).netloc.lower()
    for d, name in partners.items():
        if domain.endswith(d):
            return name
    return ""

# =========================
# REQUEST
# =========================
def fetch(url, retries=3):
    for _ in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code == 200:
                return r.text
        except:
            pass
        time.sleep(1)
    return None

# =========================
# PARSE (🔥 ГЛАВНОЕ ИСПРАВЛЕНИЕ)
# =========================
def parse(url):
    html = fetch(url)

    if not html:
        return "", "", [], []

    soup = BeautifulSoup(html, "html.parser")

    # 🔥 НОВАЯ ЛОГИКА
    meta = soup.find("meta", property="og:title")

    raw_title = ""
    raw_date = ""

    if meta and meta.get("content"):
        content = meta["content"]

        # "Заголовок | TV BRICS, 03.05.26"
        parts = content.split("|")

        if len(parts) >= 2:
            raw_title = parts[0].strip()

            right = parts[1]
            date_match = re.search(r"\d{2}\.\d{2}\.\d{2}", right)
            if date_match:
                raw_date = date_match.group(0)

    title = raw_title
    date = normalize_date(raw_date)

    # =========================
    # LINKS
    # =========================
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
# MAIN
# =========================
rows = worksheet.get_all_values()

MAX_LINKS = 10
updates = []

for i, row in enumerate(rows[1:], start=2):

    uuid = row[0] if len(row) > 0 else ""
    url = row[1] if len(row) > 1 else ""
    status = row[26] if len(row) > 26 else ""

    if not uuid or not url or status == "DONE":
        continue

    print(f"[INFO] parsing row={i}")

    date, title, links, partners_found = parse(url)

    language = get_language(url)
    month = parse_month(date)

    row_data = [""] * 28

    row_data[0] = url
    row_data[1] = date
    row_data[2] = title

    for idx in range(MAX_LINKS):
        link = links[idx] if idx < len(links) else ""
        partner = partners_found[idx] if idx < len(partners_found) else ""

        row_data[3 + idx * 2] = link
        row_data[4 + idx * 2] = partner

    row_data[25] = "DONE"
    row_data[26] = language
    row_data[27] = month

    updates.append((i, row_data))

# =========================
# UPDATE
# =========================
if updates:
    print(f"[INFO] updating {len(updates)} rows")

    ranges = [
        {
            "range": f"B{row}:AC{row}",
            "values": [data]
        }
        for row, data in updates
    ]

    worksheet.batch_update(ranges)

    print("[SUCCESS]")
else:
    print("[INFO] nothing to update")
