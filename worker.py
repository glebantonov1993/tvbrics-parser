import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import gspread
import os
import json
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
# LANGUAGE DETECTOR
# =========================
def detect_lang(url):
    if "/en/" in url:
        return "en"
    if "/cn/" in url:
        return "cn"
    if "/pt/" in url:
        return "pt"
    if "/es/" in url:
        return "es"
    if "/ar/" in url:
        return "ar"
    return "ru"


# =========================
# PARTNERS (оставил как у тебя)
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

    # AA = status (26 индекс если считать с 0)
    status = row[26] if len(row) > 26 else ""

    if not url or status == "DONE":
        continue

    print("Парсим:", url)

    date, title, links, partners_found = parse(url)

    language = detect_lang(url)

    # =========================
    # BUILD ROW
    # =========================
    row_data = []

    row_data.append("")       # A timestamp (пока пусто)
    row_data.append(url)      # B
    row_data.append(date)     # C
    row_data.append(title)    # D

    for idx in range(MAX_LINKS):
        link = links[idx] if idx < len(links) else ""
        partner = partners_found[idx] if idx < len(partners_found) else ""

        row_data.append(link)
        row_data.append(partner)

    # добиваем до AB (28 колонок)
    while len(row_data) < 27:
        row_data.append("")

    # AB = language
    row_data.append(language)

    # AA = DONE (но он у тебя ДО AB — поэтому пишем через фикс позицию)
    row_data[26] = "DONE"

    # =========================
    # SINGLE WRITE
    # =========================
    worksheet.update(f"A{i}:AB{i}", [row_data])

    print("OK:", i, language)
