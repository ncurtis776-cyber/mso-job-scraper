import requests
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf

# =========================
# ✅ GOOGLE SHEETS SETUP
# =========================

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open("Cannabis MSO Intelligence Dashboard").worksheet("Jobs")
financials_sheet = client.open("Cannabis MSO Intelligence Dashboard").worksheet("Financials")

# =========================
# ✅ COMPANY SOURCES (GREENHOUSE)
# =========================

companies = [
    {"name": "Curaleaf", "url": "https://boards.greenhouse.io/embed/job_board?for=curaleaf"},
    {"name": "Cresco Labs", "url": "https://boards.greenhouse.io/embed/job_board?for=crescolabs"},
    {"name": "Green Thumb Industries", "url": "https://boards.greenhouse.io/embed/job_board?for=gtigrows"}
]

jobs = []
seen_jobs = set()

# =========================
# ✅ GREENHOUSE SCRAPER
# =========================

for company in companies:
    try:
        response = requests.get(company["url"])
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a"):
            text = link.text.strip()
            href = link.get("href")

            if href and "/jobs/" in href and text:
                lower_text = text.lower()

                if any(x in lower_text for x in ["director", "operations", "project"]):

                    if href.startswith("/"):
                        href = "https://boards.greenhouse.io" + href

                    job_key = (company["name"], text)

                    if job_key not in seen_jobs:
                        seen_jobs.add(job_key)

                        jobs.append([
                            company["name"],
                            text,
                            "Relevant Role",
                            "Unknown",
                            datetime.today().strftime('%Y-%m-%d'),
                            href
                        ])

    except Exception as e:
        print(f"Error scraping {company['name']}: {e}")

# =========================
# ✅ NUGWORK SCRAPER
# =========================

try:
    url = "https://nugwork.net"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    for link in soup.find_all("a"):
        text = link.text.strip()
        href = link.get("href")

        if text and href:
            lower_text = text.lower()

            if any(x in lower_text for x in ["director", "operations", "project"]):

                job_key = ("NugWork", text)

                if job_key not in seen_jobs:
                    seen_jobs.add(job_key)

                    if href.startswith("/"):
                        href = "https://nugwork.net" + href

                    jobs.append([
                        "Various (NugWork)",
                        text,
                        "Job Board",
                        "Unknown",
                        datetime.today().strftime('%Y-%m-%d'),
                        href
                    ])

except Exception as e:
    print("Error scraping NugWork:", e)

# =========================
# ✅ WRITE JOBS TO SHEET
# =========================

sheet.resize(rows=1)

if jobs:
    sheet.append_rows(jobs)

print("✅ Jobs updated:", len(jobs))

# =========================
# ✅ FINANCIALS SCRAPER (ALL MSOs)
# =========================

tickers = {
    "Curaleaf": "CURLF",
    "Cresco Labs": "CRLBF",
    "Green Thumb Industries": "GTBIF",
    "Trulieve": "TCNNF",
    "Verano": "VRNOF",
    "Ayr Wellness": "AYRWF",
    "Jushi": "JUSHF",
    "TerrAscend": "TRSSF",
    "Columbia Care": "CCHWF"
}

financials_data = []

for company, ticker in tickers.items():
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        revenue = info.get("totalRevenue", "N/A")
        ebitda = info.get("ebitda", "N/A")
        net_income = info.get("netIncomeToCommon", "N/A")
        cash = info.get("totalCash", "N/A")

        financials_data.append([
            company,
            revenue,
            ebitda,
            net_income,
            cash,
            datetime.today().strftime('%Y-%m-%d')
        ])

    except Exception as e:
        print(f"Error fetching {company}: {e}")

# =========================
# ✅ WRITE FINANCIALS TO SHEET
# =========================

financials_sheet.resize(rows=1)

if financials_data:
    financials_sheet.append_rows(financials_data)

print("✅ Financials updated:", len(financials_data))
