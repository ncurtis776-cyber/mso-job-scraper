import requests
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import yfinance as yf

print("START FULL SCRIPT")

# =========================
# ✅ AUTH
# =========================
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

# ✅ SHEET CONNECTION
SHEET_URL = "https://docs.google.com/spreadsheets/d/1FkEqxI_ZhpdaUD1AxyV_oGTW3mHXo-sBb4FKGSZ8hD0"

jobs_sheet = client.open_by_url(SHEET_URL).worksheet("Jobs")
financials_sheet = client.open_by_url(SHEET_URL).worksheet("Financials")

print("✅ SHEET CONNECTED")

# =========================
# ✅ HEADERS
# =========================
headers = {"User-Agent": "Mozilla/5.0"}

# =========================
# ✅ EXPANDED MSO COMPANIES
# =========================
companies = [
    {"name": "Curaleaf", "url": "https://boards.greenhouse.io/embed/job_board?for=curaleaf"},
    {"name": "Cresco Labs", "url": "https://boards.greenhouse.io/embed/job_board?for=crescolabs"},
    {"name": "Green Thumb Industries", "url": "https://boards.greenhouse.io/embed/job_board?for=gtigrows"},
    {"name": "Trulieve", "url": "https://boards.greenhouse.io/embed/job_board?for=trulieve"},
    {"name": "TerrAscend", "url": "https://boards.greenhouse.io/embed/job_board?for=terrascend"},
    {"name": "Ayr Wellness", "url": "https://boards.greenhouse.io/embed/job_board?for=ayrwellness"}
]

jobs = []
seen = set()

# =========================
# ✅ GREENHOUSE SCRAPER
# =========================
for company in companies:
    try:
        res = requests.get(company["url"], headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        for link in soup.find_all("a"):
            title = link.text.strip()
            href = link.get("href")

            if href and "/jobs/" in href and title:
                lt = title.lower()

                if any(x in lt for x in ["director", "operations", "project"]):

                    if href.startswith("/"):
                        href = "https://boards.greenhouse.io" + href

                    key = title

                    if key not in seen:
                        seen.add(key)

                        jobs.append([
                            company["name"],
                            title,
                            "Relevant Role",
                            "Unknown",
                            datetime.today().strftime('%Y-%m-%d'),
                            href
                        ])
    except Exception as e:
        print("Error:", e)

# =========================
# ✅ NUGWORK SCRAPER
# =========================
try:
    res = requests.get("https://nugwork.net", headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    for link in soup.find_all("a"):
        title = link.text.strip()
        href = link.get("href")

        if title and href:
            lt = title.lower()

            if any(x in lt for x in ["director", "operations", "project"]):

                key = title

                if key not in seen:
                    seen.add(key)

                    if href.startswith("/"):
                        href = "https://nugwork.net" + href

                    jobs.append([
                        "Various (NugWork)",
                        title,
                        "Job Board",
                        "Unknown",
                        datetime.today().strftime('%Y-%m-%d'),
                        href
                    ])
except Exception as e:
    print("NugWork error:", e)

# =========================
# ✅ INDEED SCRAPER (NEW)
# =========================
try:
    url = "https://www.indeed.com/jobs?q=cannabis+director+operations"
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    for link in soup.find_all("a"):
        title = link.text.strip()

        if title and ("director" in title.lower() or "operations" in title.lower()):
            jobs.append([
                "Indeed",
                title,
                "Job Board",
                "Unknown",
                datetime.today().strftime('%Y-%m-%d'),
                "https://indeed.com"
            ])
except Exception as e:
    print("Indeed error:", e)

print("✅ JOBS FOUND:", len(jobs))

# =========================
# ✅ WRITE JOBS
# =========================
jobs_sheet.resize(rows=1)

if jobs:
    jobs_sheet.append_rows(jobs)

print("✅ JOBS WRITTEN")

# =========================
# ✅ FINANCIALS (UNCHANGED BASE)
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

financials = []

for name, ticker in tickers.items():
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        financials.append([
            name,
            info.get("totalRevenue", "N/A"),
            info.get("ebitda", "N/A"),
            info.get("netIncomeToCommon", "N/A"),
            info.get("totalCash", "N/A"),
            datetime.today().strftime('%Y-%m-%d')
        ])
    except Exception as e:
        print("Finance error:", e)

print("✅ FINANCIAL ROWS:", len(financials))

# =========================
# ✅ WRITE FINANCIALS
# =========================
financials_sheet.resize(rows=1)

if financials:
    financials_sheet.append_rows(financials)

print("✅ FINANCIALS WRITTEN")
