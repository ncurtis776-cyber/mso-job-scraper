import requests
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import yfinance as yf

print("START FULL SYSTEM")

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

SHEET_URL = "https://docs.google.com/spreadsheets/d/1FkEqxI_ZhpdaUD1AxyV_oGTW3mHXo-sBb4FKGSZ8hD0"

jobs_sheet = client.open_by_url(SHEET_URL).worksheet("Jobs")
financials_sheet = client.open_by_url(SHEET_URL).worksheet("Financials")

headers = {"User-Agent": "Mozilla/5.0"}

# =========================
# ✅ JOB SOURCES
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
# ✅ GREENHOUSE
# =========================
for company in companies:
    try:
        res = requests.get(company["url"], headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        for link in soup.find_all("a"):
            raw = link.text.strip()
            href = link.get("href")

            if not raw or not href or "/jobs/" not in href:
                continue

            # ✅ split location cleanly
            parts = raw.split(" - ")
            title = parts[0]
            location = parts[-1] if len(parts) > 1 else "Unknown"

            lt = title.lower()

            if not any(x in lt for x in ["director", "vp", "head", "operations", "strategy", "project"]):
                continue

            if href.startswith("/"):
                href = "https://boards.greenhouse.io" + href

            if title in seen:
                continue

            seen.add(title)

            jobs.append([
                company["name"],
                title,
                "Relevant Role",
                location,
                datetime.today().strftime('%Y-%m-%d'),
                href
            ])
    except:
        pass

# =========================
# ✅ NUGWORK (CLEAN)
# =========================
try:
    res = requests.get("https://nugwork.net/jobs", headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    for link in soup.find_all("a"):
        title = link.get_text(strip=True)
        href = link.get("href")

        if not title or not href:
            continue

        if href.startswith("/"):
            href = "https://nugwork.net" + href

        if "/jobs/" not in href:
            continue

        lt = title.lower()

        if not any(x in lt for x in ["director", "operations", "project"]):
            continue

        if title in seen:
            continue

        seen.add(title)

        jobs.append([
            "Various (NugWork)",
            title,
            "Job Board",
            "Unknown",
            datetime.today().strftime('%Y-%m-%d'),
            href
        ])
except:
    pass

# =========================
# ✅ INDEED
# =========================
try:
    res = requests.get("https://www.indeed.com/jobs?q=cannabis+director+operations", headers=headers)
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
except:
    pass

print("JOBS:", len(jobs))

jobs_sheet.resize(rows=1)
if jobs:
    jobs_sheet.append_rows(jobs)

# =========================
# ✅ FINANCIALS (IMPROVED FALLBACK)
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

        revenue = info.get("totalRevenue")
        ebitda = info.get("ebitda")
        net_income = info.get("netIncomeToCommon")
        cash = info.get("totalCash")

        # ✅ fallback if missing
        if revenue is None:
            revenue = "Missing"
        if ebitda is None:
            ebitda = "Missing"
        if net_income is None:
            net_income = "Missing"
        if cash is None:
            cash = "Missing"

        financials.append([
            name,
            revenue,
            ebitda,
            net_income,
            cash,
            datetime.today().strftime('%Y-%m-%d')
        ])
    except:
        pass

print("FIN:", len(financials))

financials_sheet.resize(rows=1)
if financials:
    financials_sheet.append_rows(financials)

print("✅ SYSTEM COMPLETE")
