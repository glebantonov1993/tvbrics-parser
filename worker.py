import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import gspread
import os
import json
from google.oauth2.service_account import Credentials

# =========================
# GOOGLE AUTH
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
    "elbalad.news": "Sada El-Balad",
    "vnanet.vn": "Vietnam News Agency (VNA)",
    "globaltimes.cn": "Global Times",
    "news.cn": "СИНЬХУА Новости",
    "telesurtv.net": "teleSUR"
}


def get_partner(url):
    domain = urlparse(url).netloc.lower()
    for d, name in partners.items():
        if d in domain:
            return name
    return "—"


def parse(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    except Exception as e:
        return "", str(e), [], []

    soup = BeautifulSoup(r.text, "html.parser")

    date_tag = soup.find("span", class_="data_row__date")
    date = date_tag.get_text(strip=True) if date_tag else ""

    title_tag = soup.find("h1", class_="news-detail__name")
    title = title_tag.get_text(strip=True) if title_tag else ""

    links_dict = {}

    for a in soup.find_all("a", href=True):
        link = urljoin(url, a["href"])

        if "tvbrics.com" in link:
            continue

        partner = get_partner(link)
        if partner != "—":
            links_dict[link] = partner

    return date, title, list(links_dict.keys()), list(links_dict.values())


# =========================
# MAIN
# =========================
rows = worksheet.get_all_values()

MAX_LINKS = 10

for i, row in enumerate(rows[1:], start=2):

    url = row[1]
    status = row[25] if len(row) > 25 else ""

    if not url or status == "DONE":
        continue

    print("Парсим:", url)

    date, title, links, partners_found = parse(url)

    # =========================
    # BUILD ROW
    # =========================
    row_data = []

    # A timestamp (пока пусто)
    row_data.append("")

    # B URL
    row_data.append(url)

    # C date
    row_data.append(date)

    # D title
    row_data.append(title)

    # LINKS + PARTNERS
    for idx in range(MAX_LINKS):
        link = links[idx] if idx < len(links) else ""
        partner = partners_found[idx] if idx < len(partners_found) else ""

        row_data.append(link)
        row_data.append(partner)

    # padding до Z
    while len(row_data) < 26:
        row_data.append("")

    # STATUS (Z)
    row_data.append("DONE")

    # =========================
    # SINGLE WRITE (FIX 429)
    # =========================
    worksheet.update(f"A{i}:AA{i}", [row_data])

    print("OK row:", i)
