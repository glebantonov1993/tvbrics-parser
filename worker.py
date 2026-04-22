

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
# SHEETS
# =========================
SHEET_ID = "1Dv0dSEoTHN3ri7CITXjZE7kOw-QU5ri9jLpcG8xApCo"
sh = gc.open_by_key(SHEET_ID)

queue_ws = sh.worksheet("RAW_DATA")
output_ws = sh.worksheet("CN_VIEW")
log_ws = sh.worksheet("LOGS")

# =========================
# LOCK (FIXED)
# =========================
LOCK_CELL = "Z1"

def acquire_lock():
    value = queue_ws.acell(LOCK_CELL).value
    if value == "TRUE":
        return False

    queue_ws.update(LOCK_CELL, [["TRUE"]])   # 🔥 FIX
    return True

def release_lock():
    queue_ws.update(LOCK_CELL, [["FALSE"]])  # 🔥 FIX

# =========================
# PARTNERS (O(1))
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

# =========================
# LANGUAGE
# =========================
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

# =========================
# MONTH
# =========================
def parse_month(date_str):
    try:
        return datetime.strptime(date_str, "%d.%m.%Y").month
    except:
        return ""

# =========================
# PARTNER MATCH
# =========================
def get_partner(url):
    domain = urlparse(url).netloc.lower()
    for d, name in PARTNERS.items():
        if domain.endswith(d):
            return name
    return ""

# =========================
# FETCH
# =========================
def fetch(url):
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if r.status_code == 200:
            return r.text
    except:
        return None
    return None

# =========================
# PARSE
# =========================
def parse(url):
    html = fetch(url)
    if not html:
        raise Exception("Fetch failed")

    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("h1")
    title = title.get_text(strip=True) if title else ""

    date = soup.find("span")
    date = date.get_text(strip=True) if date else ""

    links = []
    partners = []
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
            partners.append(partner)

        if len(links) >= 10:
            break

    return date, title, links, partners

# =========================
# LOG
# =========================
def log(url, status, msg=""):
    log_ws.append_row([
        datetime.now().isoformat(),
        url,
        status,
        msg
    ])

# =========================
# TASKS
# =========================
def get_tasks(limit=30):
    rows = queue_ws.get_all_values()
    tasks = []

    for i, row in enumerate(rows[1:], start=2):
        url = row[1] if len(row) > 1 else ""
        status = row[2] if len(row) > 2 else "NEW"

        if status == "NEW":
            tasks.append((i, url))

        if len(tasks) >= limit:
            break

    return tasks

# =========================
# STATUS UPDATE
# =========================
def set_status(row, status, error=""):
    queue_ws.update(f"C{row}", [[status]])  # FIX
    queue_ws.update(f"D{row}", [[error]])   # FIX

# =========================
# OUTPUT
# =========================
def write_output(url, date, title, links, partners_list, lang, month):
    row = [
        url,
        date,
        title
    ]

    for i in range(10):
        row.append(links[i] if i < len(links) else "")
        row.append(partners_list[i] if i < len(partners_list) else "")

    row.append(lang)
    row.append(month)

    output_ws.append_row(row)

# =========================
# MAIN RUNNER
# =========================
def run():
    if not acquire_lock():
        print("Already running")
        return

    try:
        tasks = get_tasks()
        print(f"Tasks: {len(tasks)}")

        for row, url in tasks:
            try:
                set_status(row, "PROCESSING")

                date, title, links, partners_list = parse(url)

                lang = get_language(url)
                month = parse_month(date)

                write_output(url, date, title, links, partners_list, lang, month)

                set_status(row, "DONE")
                log(url, "DONE")

            except Exception as e:
                set_status(row, "FAILED", str(e))
                log(url, "FAILED", str(e))

                time.sleep(2)

    finally:
        release_lock()

# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    run()
