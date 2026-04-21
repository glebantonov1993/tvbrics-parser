import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import gspread
import os
import json
from google.oauth2.service_account import Credentials

# =========================
# GOOGLE AUTH (GitHub Secret)
# =========================
creds_json = json.loads(os.environ["GOOGLE_CREDS"])
creds = Credentials.from_service_account_info(creds_json)

gc = gspread.authorize(creds)

# =========================
# GOOGLE SHEET
# =========================
SHEET_ID = "1Dv0dSEoTHN3ri7CITXjZE7kOw-QU5ri9jLpcG8xApCo"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.sheet1


# =========================
# ПАРТНЁРЫ
# =========================
partners = {
    "vision360.bo": "Visión 360",
    "cgtn.com": "CGTN",
    "elbalad.news": "Sada El-Balad",
    "vnanet.vn": "Vietnam News Agency (VNA)",
    "news.cgtn.com": "CGTN",
    "antaranews.com": "ANTARA",
    "en.antaranews.com": "ANTARA",
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
# MAIN RUN (ONE PASS)
# =========================
rows = worksheet.get_all_values()

for i, row in enumerate(rows[1:], start=2):

    url = row[1]
    status = row[6] if len(row) > 6 else ""

    if not url or status == "DONE":
        continue

    print("Парсим:", url)

    date, title, links, partners_found = parse(url)

    worksheet.update_cell(i, 3, date)
    worksheet.update_cell(i, 4, title)
    worksheet.update_cell(i, 5, "\n".join(links))
    worksheet.update_cell(i, 6, "\n".join(partners_found))
    worksheet.update_cell(i, 7, "DONE")
