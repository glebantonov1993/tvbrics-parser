import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import gspread
import os
import json
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
# PARTNERS
# =========================
partners = {
    "vision360.bo": "Visión 360",
    "cgtn.com": "CGTN",
    "news9live.com": "News9",
    "alalam.ir": "Alalam News Network",
    "inform.kz ": "Kazinform ",
    "aninews.in": "ANI ",
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
    "inform.kz": "МИА Казинформ",
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


# =========================
# LANGUAGE DETECTION
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
# MONTH PARSER
# =========================
def parse_month(date_str):
    if not date_str:
        return ""

    import re

    # Китай / араб / любые с 年月
    m = re.search(r"(\d{2,4})年(\d{1,2})月", date_str)
    if m:
        return int(m.group(2))

    # Обычный формат 27.03.26
    try:
        dt = datetime.strptime(date_str, "%d.%m.%y")
        return dt.month
    except:
        pass

    return ""

# =========================
# PARTNER MATCH
# =========================
def get_partner(url):
    domain = urlparse(url).netloc.lower()
    for d, name in partners.items():
        if d in domain:
            return name
    return ""

# =========================
# PARSE PAGE
# =========================
def parse(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    except Exception:
        return "", "", [], []

    soup = BeautifulSoup(r.text, "html.parser")

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
# MAIN
# =========================
# =========================
# MAIN
# =========================
rows = worksheet.get_all_values()

MAX_LINKS = 10
TOTAL_COLS = 29  # A–AC

for i, row in enumerate(rows[1:], start=2):

    url = row[1]
    status = row[26] if len(row) > 26 else ""  # AA

    if not url or status == "DONE":
        continue

    print("Парсим:", url)

    date, title, links, partners_found = parse(url)

    language = get_language(url)
    month = parse_month(date)

    # =========================
    # 🧠 BUILD ROW (СТРОГО 29 КОЛОНОК)
    # =========================
    row_data = [""] * TOTAL_COLS

    # базовые
    row_data[0] = ""          # A timestamp
    row_data[1] = url         # B
    row_data[2] = date        # C
    row_data[3] = title       # D

    # ссылки + партнёры (E–X)
    for idx in range(MAX_LINKS):
        link = links[idx] if idx < len(links) else ""
        partner = partners_found[idx] if idx < len(partners_found) else ""

        col_link = 4 + idx * 2       # E=4
        col_partner = 5 + idx * 2    # F=5

        row_data[col_link] = link
        row_data[col_partner] = partner

    # AA статус
    row_data[26] = "DONE"

    # AB язык
    row_data[27] = language

    # AC месяц
    row_data[28] = month

    # =========================
    # ⚡ ОДНА ЗАПИСЬ
    # =========================
    worksheet.update(
        range_name=f"A{i}:AC{i}",
        values=[row_data]
    )

    print("OK:", i)
