import requests
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import yfinance as yf

print("START SYSTEM")

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
# ✅ ALL MAJOR MSOs
# =========================
mso_companies = [
    {"name": "Curaleaf"},
    {"name": "Cresco Labs"},
    {"name": "Green Thumb Industries"},
    {"name": "Trulieve"},
    {"name": "Verano"},
    {"name": "Ayr Wellness"},
    {"name": "Jushi"},
    {"name": "TerrAscend"},
    {"name": "Columbia Care"}
]

jobs = []
seen = set()

# =========================
# ✅ GREENHOUSE (PRIMARY)
# =========================
greenhouse_sources = [
    ("Curaleaf", "https://boards.greenhouse.io/embed/job_board?for=curaleaf"),
    ("Cresco Labs", "https://boards.greenhouse.io/embed/job_board?for=crescolabs"),
    ("Green Thumb Industries", "https://boards.greenhouse.io/embed/job_board?for=gtigrows"),
    ("Trulieve", "https://boards.greenhouse.io/embed/job_board?for=trulieve"),
    ("TerrAscend", "https://boards.greenhouse.io/embed/job_board?for=terrascend"),
]

for name, url in greenhouse_sources:
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        for link in soup.find_all("a"):
            raw = link.text.strip()
            href = link.get("href")

            if not raw or not href or "/jobs/" not in href:
                continue

            parts = raw.split(" - ")
            title = parts[0]
            location = parts[-1] if len(parts) > 1 else "Unknown"

            if not any(x in title.lower() for x in ["director","vp","head","operations","strategy"]):
                continue

            if href.startswith("/"):
                href = "https://boards.greenhouse.io" + href

            if title in seen:
                continue

            seen.add(title)

            jobs.append([
                name, title, "Relevant Role",
                location, datetime.today().strftime('%Y-%m-%d'), href
            ])
    except:
        pass

# =========================
# ✅ NUGWORK
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

        if not any(x in title.lower() for x in ["director","operations"]):
            continue

        if title in seen:
            continue

        seen.add(title)

        jobs.append([
            "Various (NugWork)", title, "Job Board",
            "Unknown", datetime.today().strftime('%Y-%m-%d'), href
        ])
except:
    pass

# =========================
# ✅ INDEED (WIDE NET)
# =========================
try:
    res = requests.get("https://www.indeed.com/jobs?q=cannabis+director+operations", headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    for link in soup.find_all("a"):
        text = link.get_text(strip=True)

        if text and ("director" in text.lower() or "operations" in text.lower()):
            jobs.append([
                "Indeed",
                text,
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
# ✅ FINANCIALS (HYBRID)
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
            info.get("totalRevenue", "Missing"),
            info.get("ebitda", "Missing"),
            info.get("netIncomeToCommon", "Missing"),
            info.get("totalCash", "Missing"),
            datetime.today().strftime('%Y-%m-%d')
        ])
    except:
        financials.append([
            name, "Missing", "Missing", "Missing", "Missing",
            datetime.today().strftime('%Y-%m-%d')
        ])

print("FINANCIALS:", len(financials))

financials_sheet.resize(rows=1)
financials_sheet.append_rows(financials)

print("✅ SYSTEM COMPLETE")
