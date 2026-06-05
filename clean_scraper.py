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
# ✅ JOB COLLECTION
# =========================
jobs = []
seen = set()

# =========================
# ✅ GREENHOUSE COMPANIES
# =========================
greenhouse_companies = [
    {"name": "Curaleaf", "url": "https://boards.greenhouse.io/embed/job_board?for=curaleaf"},
    {"name": "Cresco Labs", "url": "https://boards.greenhouse.io/embed/job_board?for=crescolabs"},
    {"name": "Green Thumb Industries", "url": "https://boards.greenhouse.io/embed/job_board?for=gtigrows"},
    {"name": "Trulieve", "url": "https://boards.greenhouse.io/embed/job_board?for=trulieve"},
    {"name": "TerrAscend", "url": "https://boards.greenhouse.io/embed/job_board?for=terrascend"},
]

for company in greenhouse_companies:
    try:
        res = requests.get(company["url"], headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        for link in soup.find_all("a"):
            raw = link.text.strip()
            href = link.get("href")

            if not raw or not href or "/jobs/" not in href:
                continue

            parts = raw.split(" - ")
            title = parts[0]
            location = parts[-1] if len(parts) > 1 else "Unknown"

            if not any(x in title.lower() for x in ["director","vp","operations","strategy","project"]):
                continue

            if href.startswith("/"):
                href = "https://boards.greenhouse.io" + href

            if title in seen:
                continue

            seen.add(title)

            jobs.append([
                company["name"], title, "Relevant Role",
                location, datetime.today().strftime('%Y-%m-%d'), href
            ])
    except:
        pass

# =========================
# ✅ DIRECT CAREERS PAGE SCRAPERS (NEW)
# =========================

careers_sites = [
    {"name": "Verano", "url": "https://www.verano.com/careers/"},
    {"name": "Ayr Wellness", "url": "https://ayrwellness.com/careers/"},
    {"name": "Jushi", "url": "https://jushico.com/careers/"}
]

for company in careers_sites:
    try:
        res = requests.get(company["url"], headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        for link in soup.find_all("a"):
            text = link.get_text(strip=True)
            href = link.get("href")

            if not text or not href:
                continue

            if any(x in text.lower() for x in ["director","operations","manager","vp"]):

                if text in seen:
                    continue

                seen.add(text)

                jobs.append([
                    company["name"],
                    text,
                    "Company Site",
                    "Unknown",
                    datetime.today().strftime('%Y-%m-%d'),
                    href if href.startswith("http") else company["url"]
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

        if not any(x in title.lower() for x in ["director","operations","project"]):
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
    res = requests.get("https://www.indeed.com/jobs?q=cannabis+operations+director", headers=headers)
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

# =========================
# ✅ WRITE JOBS
# =========================
jobs_sheet.resize(rows=1)
if jobs:
    jobs_sheet.append_rows(jobs)

print("✅ JOBS COMPLETE:", len(jobs))

# =========================
# ✅ FINANCIALS (HYBRID)
# =========================

tickers = {
    "Curaleaf": "CURLF",
    "Cresco Labs": "CRLBF",
    "Green Thumb Industries": "GTBIF",
    "Trulieve": "TCNNF"
}

financials = []

for name, ticker in tickers.items():
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        financials.append([
            name,
            info.get("totalRevenue","Missing"),
            info.get("ebitda","Missing"),
            info.get("netIncomeToCommon","Missing"),
            info.get("totalCash","Missing"),
            datetime.today().strftime('%Y-%m-%d')
        ])
    except:
        pass

# =========================
# ✅ INVESTOR PAGES (NEW)
# =========================

investor_pages = [
    {"name": "Curaleaf", "url": "https://ir.curaleaf.com/"},
    {"name": "Trulieve", "url": "https://investors.trulieve.com/"}
]

for company in investor_pages:
    try:
        res = requests.get(company["url"], headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        text = soup.get_text()

        # ✅ crude extraction example
        if "revenue" in text.lower():
            financials.append([
                company["name"],
                "From Investor Page",
                "See IR",
                "See IR",
                "See IR",
                datetime.today().strftime('%Y-%m-%d')
            ])
    except:
        pass

# =========================
# ✅ WRITE FINANCIALS
# =========================
financials_sheet.resize(rows=1)

if financials:
    financials_sheet.append_rows(financials)

print("✅ FINANCIALS COMPLETE:", len(financials))
