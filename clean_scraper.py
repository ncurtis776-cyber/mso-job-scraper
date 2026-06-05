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
risk_sheet = client.open_by_url(SHEET_URL).worksheet("Risk")

headers = {"User-Agent": "Mozilla/5.0"}

# ==========================================================
# ✅ JOBS SECTION (UNCHANGED LOGIC)
# ==========================================================

jobs = []
seen = set()

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

# NugWork
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

# Indeed
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

jobs_sheet.resize(rows=1)
if jobs:
    jobs_sheet.append_rows(jobs)

print("✅ JOBS COMPLETE:", len(jobs))

# ==========================================================
# ✅ FINANCIALS + RISK (COMBINED)
# ==========================================================

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
risk_rows = []

# =========================
# ✅ RISK FUNCTIONS
# =========================
def calculate_risk(data):
    debt_risk = min(data["de"] / 2.0, 3.0)
    liquidity_risk = max(1.5 - data["cr"], 0)
    margin_risk = max(0.2 - data["pm"], 0) * 5
    growth_risk = max(0.0 - data["rg"], 0) * 10
    interest_risk = max(3.0 - data["ic"], 0)

    return round(
        0.30 * debt_risk +
        0.20 * liquidity_risk +
        0.20 * margin_risk +
        0.15 * growth_risk +
        0.15 * interest_risk, 2)

def classify(score):
    if score < 1.5:
        return "Low"
    elif score < 3:
        return "Medium"
    else:
        return "High"

# =========================
# ✅ LOOP
# =========================

for name, ticker in tickers.items():
    try:
        stock = yf.Ticker(ticker)

        bs = stock.balance_sheet
        fin = stock.financials

        latest_bs = bs.iloc[:, 0] if not bs.empty else None
        latest_fin = fin.iloc[:, 0] if not fin.empty else None

        def gbs(x): return float(latest_bs.get(x, 0)) if latest_bs is not None else 0
        def gfin(x): return float(latest_fin.get(x, 0)) if latest_fin is not None else 0

        total_debt = gbs("Total Debt")
        equity = gbs("Total Stockholder Equity")
        current_assets = gbs("Total Current Assets")
        current_liabilities = gbs("Total Current Liabilities")
        revenue = gfin("Total Revenue")
        net_income = gfin("Net Income")
        ebit = gfin("Ebit")
        interest = abs(gfin("Interest Expense"))

        if fin.shape[1] >= 2:
            rev_now = fin.iloc[:, 0].get("Total Revenue", 0)
            rev_prev = fin.iloc[:, 1].get("Total Revenue", 0)
            growth = (rev_now - rev_prev) / rev_prev if rev_prev else 0
        else:
            growth = 0

        # ✅ store financials (your table)
        financials.append([
            name,
            revenue if revenue else "Missing",
            ebit if ebit else "Missing",
            net_income if net_income else "Missing",
            gbs("Total Cash"),
            datetime.today().strftime('%Y-%m-%d')
        ])

        # ✅ risk inputs
        data = {
            "de": (total_debt / equity) if equity else 0,
            "cr": (current_assets / current_liabilities) if current_liabilities else 0,
            "pm": (net_income / revenue) if revenue else 0,
            "rg": growth,
            "ic": (ebit / interest) if interest else 0
        }

        score = calculate_risk(data)
        level = classify(score)

        risk_rows.append([
            name, ticker,
            round(data["de"],2),
            round(data["cr"],2),
            round(data["pm"],2),
            round(data["rg"],2),
            round(data["ic"],2),
            score, level,
            "Yahoo",
            datetime.today().strftime('%Y-%m-%d')
        ])

    except:
        pass

# =========================
# ✅ WRITE TABLES
# =========================

financials_sheet.resize(rows=1)
financials_sheet.append_rows(financials)

risk_sheet.resize(rows=1)
risk_sheet.append_rows(risk_rows)

print("✅ SYSTEM COMPLETE")
