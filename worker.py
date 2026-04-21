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
    "globaltimes.cn": "Global Times",
    "antaranews.com": "ANTARA",
    "en.antaranews.com": "ANTARA",
    "cgtn.com": "CGTN",
    "news.cn": "Xinhua",
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

    try:
        # 27.03.26
        if "." in date_str:
            dt = datetime.strptime(date_str, "%d.%m.%y")
            return dt.month
    except:
        pass

    try:
        # 26年04月21日
        import re
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
        if m:
            return int(m.group(2))
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
rows = worksheet.get_all_values()

MAX_LINKS = 10

for i, row in enumerate(rows[1:], start=2):

    url = row[1]
    status = row[26] if len(row) > 26 else ""  # AA

    if not url or status == "DONE":
        continue

    print("Парсим:", url)

    date, title, links, partners_found = parse(url)

    language = get_language(url)
    month = parse_month(date)

    # base columns
    row_data = []
    row_data.append("")      # A timestamp (пока пусто)
    row_data.append(url)     # B
    row_data.append(date)    # C
    row_data.append(title)   # D

    # links
    for idx in range(MAX_LINKS):
        row_data.append(links[idx] if idx < len(links) else "")
        row_data.append(partners_found[idx] if idx < len(partners_found) else "")

    # padding to AA (27 cols)
    while len(row_data) < 27:
        row_data.append("")

    # AA status
    row_data.append("DONE")

    # AB language
    row_data.append(language)

    # AC month
    row_data.append(month)

    # batch write
    worksheet.update(f"A{i}:AC{i}", [row_data])

    print("OK:", i)
