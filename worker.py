import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import gspread
import os
import json
from datetime import datetime
import re
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
    "cgtn.com": "CGTN",
    "aninews.in": "ANI",
    "vnanet.vn": "VNA",
    "elmaipo.cl": "El Maipo",
    "inform.kz": "Kazinform",
    "china.com": "China.com",
    "chinadaily.com.cn": "China Daily",
    "telesurtv.net": "teleSUR",
    "irna.ir": "IRNA"
}

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
# DATE EXTRACTION (ВАЖНО)
# =========================
def extract_date_any(soup):
    text = soup.get_text(" ", strip=True)

    # 1. CN / JP / AR format
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if m:
        y, mo, d = map(int, m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"

    # 2. EU format 27.03.26
    m = re.search(r"\b(\d{2})\.(\d{2})\.(\d{2})\b", text)
    if m:
        return datetime.strptime(m.group(0), "%d.%m.%y").strftime("%Y-%m-%d")

    # 3. ISO fallback
    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if m:
        return m.group(0)

    return ""

def parse_month(date_str):
    if not date_str:
        return ""
    try:
        return int(date_str.split("-")[1])
    except:
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
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    except:
        return "", "", [], []

    soup = BeautifulSoup(r.text, "html.parser")

    # title
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # date from HTML (если есть)
    date_tag = soup.find("span")
    date = date_tag.get_text(strip=True) if date_tag else ""

    # fallback extraction
    if not date:
        date = extract_date_any(soup)

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
TOTAL_COLS = 29

for i, row in enumerate(rows[1:], start=2):

    url = row[1]
    status = row[26] if len(row) > 26 else ""

    if not url or status == "DONE":
        continue

    print("Парсим:", url)

    date, title, links, partners_found = parse(url)

    month = parse_month(date)
    language = get_language(url)

    row_data = [""] * TOTAL_COLS

    # base
    row_data[1] = url
    row_data[2] = date
    row_data[3] = title

    # links
    for idx in range(MAX_LINKS):
        row_data[4 + idx * 2] = links[idx] if idx < len(links) else ""
        row_data[5 + idx * 2] = partners_found[idx] if idx < len(partners_found) else ""

    row_data[26] = "DONE"
    row_data[27] = language
    row_data[28] = month

    worksheet.update(f"A{i}:AC{i}", [row_data])

    print("OK:", i)
