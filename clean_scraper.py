import requests
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os, json
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
scores_sheet = client.open_by_url(SHEET_URL).worksheet("Scores")

headers = {"User-Agent": "Mozilla/5.0"}

# ==========================================================
# ✅ JOBS
# ==========================================================
jobs = []
seen = {}
job_counts = {}

greenhouse_sources = [
    ("Curaleaf", "https://boards.greenhouse.io/embed/job_board?for=curaleaf"),
    ("Cresco Labs", "https://boards.greenhouse.io/embed/job_board?for=crescolabs"),
    ("Green Thumb Industries", "https://boards.greenhouse.io/embed/job_board?for=gtigrows"),
    ("Trulieve", "https://boards.greenhouse.io/embed/job_board?for=trulieve")
]

for name, url in greenhouse_sources:
    job_counts[name] = 0

    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        for link in soup.find_all("a"):
            raw = link.text.strip()
            href = link.get("href")

            if not raw or not href or "/jobs/" not in href:
                continue

            title = raw.split(" - ")[0]

            if not any(x in title.lower() for x in ["director","vp","operations"]):
                continue

            if href.startswith("/"):
                href = "https://boards.greenhouse.io" + href

            key = name + title
            if key in seen:
                continue

            seen[key] = True
            job_counts[name] += 1

            jobs.append([
                name, title, "Relevant", "Unknown",
                datetime.today().strftime('%Y-%m-%d'), href
            ])
    except:
        pass

jobs_sheet.resize(rows=1)
jobs_sheet.append_rows(jobs)

print("✅ JOBS COMPLETE")

# ==========================================================
# ✅ FINANCIALS + RISK + SCORES
# ==========================================================

tickers = {
    "Curaleaf": "CURLF",
    "Cresco Labs": "CRLBF",
    "Green Thumb Industries": "GTBIF",
    "Trulieve": "TCNNF",
    "Verano": "VRNOF",
    "Ayr Wellness": "AYRWF",
    "Jushi": "JUSHF"
}

financials = []
risk_rows = []
score_rows = []

# =========================
# ✅ FUNCTIONS
# =========================

def calculate_risk(d):
    return round(
        d["de"]*0.3 +
        (1-d["cr"])*0.2 +
        abs(d["pm"])*0.2 +
        max(-d["rg"],0)*0.2 +
        (1/d["ic"] if d["ic"] else 1)*0.1
    ,2)

def classify(x):
    return "High" if x > 2 else "Medium" if x > 1 else "Low"

def normalize(val, low, high):
    return max(0, min((val - low) / (high - low), 1))

# =========================
# ✅ LOOP
# =========================

for name, ticker in tickers.items():
    try:
        stock = yf.Ticker(ticker)

        bs = stock.balance_sheet
        fin = stock.financials

        latest_bs = bs.iloc[:,0] if not bs.empty else {}
        latest_fin = fin.iloc[:,0] if not fin.empty else {}

        def g(x): return float(latest_bs.get(x,0))
        def f(x): return float(latest_fin.get(x,0))

        debt = g("Total Debt")
        equity = g("Total Stockholder Equity")
        assets = g("Total Current Assets")
        liabilities = g("Total Current Liabilities")

        revenue = f("Total Revenue")
        net = f("Net Income")
        ebit = f("Ebit")
        interest = abs(f("Interest Expense"))

        # ✅ fallback fixes
        equity = equity if equity else 1
        liabilities = liabilities if liabilities else 1
        revenue = revenue if revenue else 1
        interest = interest if interest else 1

        # ✅ ratios
        de = debt / equity
        cr = assets / liabilities
        pm = net / revenue

        # ✅ growth
        if fin.shape[1] >= 2:
            r1 = fin.iloc[:,0].get("Total Revenue",0)
            r2 = fin.iloc[:,1].get("Total Revenue",r1)
            rg = (r1-r2)/r2 if r2 else 0
        else:
            rg = 0

        ic = ebit / interest

        # ✅ RISK
        risk_score = calculate_risk({"de":de,"cr":cr,"pm":pm,"rg":rg,"ic":ic})
        risk_level = classify(risk_score)

        # ✅ FINANCIAL SCORE (0–10)
        pm_score = normalize(pm, -0.2, 0.2)
        rg_score = normalize(rg, -0.2, 0.3)
        de_score = normalize(1 - (de/3), 0, 1)
        cr_score = normalize(cr, 0, 2)

        financial_score = round(
            (pm_score*0.3 + rg_score*0.3 + de_score*0.2 + cr_score*0.2) * 10, 2
        )

        # ✅ JOB SCORE
        jc = job_counts.get(name, 0)
        job_score = min(jc / 10, 1) * 10

        # ✅ RISK NORMALIZED
        risk_norm = max(0, 10 - (risk_score * 3))

        # ✅ TOTAL SCORE
        total_score = round(
            financial_score * 0.35 +
            job_score * 0.25 +
            risk_norm * 0.40,
        2)

        # ✅ STORE TABLES
        financials.append([
            name,
            f"{round(revenue/1e6,1)}M",
            f"{round(ebit/1e6,1)}M",
            f"{round(net/1e6,1)}M",
            datetime.today().strftime('%Y-%m-%d')
        ])

        risk_rows.append([
            name, ticker,
            round(de,2),
            round(cr,2),
            f"{round(pm*100,1)}%",
            f"{round(rg*100,1)}%",
            risk_score,
            risk_level,
            "Yahoo",
            datetime.today().strftime('%Y-%m-%d')
        ])

        score_rows.append([
            name,
            financial_score,
            round(job_score,2),
            round(risk_norm,2),
            "N/A",   # Glassdoor placeholder
            total_score
        ])

    except Exception as e:
        print("Error:", name)

# =========================
# ✅ WRITE EVERYTHING
# =========================

financials_sheet.resize(rows=1)
financials_sheet.append_rows(financials)

risk_sheet.resize(rows=1)
risk_sheet.append_rows(risk_rows)

scores_sheet.resize(rows=1)
scores_sheet.append_rows(score_rows)

print("✅ FULL SYSTEM COMPLETE")
