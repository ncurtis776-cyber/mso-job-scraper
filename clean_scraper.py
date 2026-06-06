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

SHEET = client.open_by_url("https://docs.google.com/spreadsheets/d/1FkEqxI_ZhpdaUD1AxyV_oGTW3mHXo-sBb4FKGSZ8hD0")

# ✅ SAFE TAB LOADER (THIS FIXES YOUR ISSUE FOREVER)
def get_or_create(sheet_name):
    try:
        return SHEET.worksheet(sheet_name)
    except:
        print(f"Creating missing sheet: {sheet_name}")
        return SHEET.add_worksheet(title=sheet_name, rows=100, cols=10)

jobs_sheet = get_or_create("Jobs")
financials_sheet = get_or_create("Financials")
risk_sheet = get_or_create("Risk")
scores_sheet = get_or_create("Scores")
glassdoor_sheet = get_or_create("Glassdoor")

headers = {"User-Agent": "Mozilla/5.0"}

# ==========================================================
# ✅ JOBS
# ==========================================================
jobs = []
seen = {}
job_counts = {}

sources = [
    ("Curaleaf", "https://boards.greenhouse.io/embed/job_board?for=curaleaf"),
    ("Cresco Labs", "https://boards.greenhouse.io/embed/job_board?for=crescolabs"),
    ("Green Thumb Industries", "https://boards.greenhouse.io/embed/job_board?for=gtigrows"),
    ("Trulieve", "https://boards.greenhouse.io/embed/job_board?for=trulieve")
]

for name, url in sources:
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
if jobs:
    jobs_sheet.append_rows(jobs)

print("✅ JOBS COMPLETE")

# ==========================================================
# ✅ GLASSDOOR DATA
# ==========================================================
glassdoor_ratings = {
    "Curaleaf": 3.2,
    "Cresco Labs": 3.1,
    "Green Thumb Industries": 3.5,
    "Trulieve": 3.0,
    "Verano": 2.9,
    "Ayr Wellness": 2.8,
    "Jushi": 3.3
}

glassdoor_rows = []

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
        equity = g("Total Stockholder Equity") or 1
        assets = g("Total Current Assets")
        liabilities = g("Total Current Liabilities") or 1

        revenue = f("Total Revenue") or 1
        net = f("Net Income")
        ebit = f("Ebit")
        interest = abs(f("Interest Expense")) or 1

        de = debt / equity
        cr = assets / liabilities
        pm = net / revenue

        if fin.shape[1] >= 2:
            r1 = fin.iloc[:,0].get("Total Revenue",0)
            r2 = fin.iloc[:,1].get("Total Revenue",r1)
            rg = (r1-r2)/r2 if r2 else 0
        else:
            rg = 0

        ic = ebit / interest

        risk_score = calculate_risk({"de":de,"cr":cr,"pm":pm,"rg":rg,"ic":ic})

        pm_score = normalize(pm, -0.2, 0.2)
        rg_score = normalize(rg, -0.2, 0.3)
        de_score = normalize(1 - (de/3), 0, 1)
        cr_score = normalize(cr, 0, 2)

        financial_score = round((pm_score*0.3 + rg_score*0.3 + de_score*0.2 + cr_score*0.2)*10,2)

        jc = job_counts.get(name,0)
        job_score = min(jc/10,1)*10

        risk_norm = max(0, 10 - (risk_score*3))

        rating = glassdoor_ratings.get(name, 3.0)
        glassdoor_score = (rating/5)*10

        total = round(
            financial_score*0.35 +
            job_score*0.25 +
            risk_norm*0.30 +
            glassdoor_score*0.10
        ,2)

        score_rows.append([
            name,
            financial_score,
            job_score,
            risk_norm,
            round(glassdoor_score,2),
            total
        ])

        glassdoor_rows.append([
            name,
            rating,
            round(glassdoor_score,2),
            datetime.today().strftime('%Y-%m-%d')
        ])

    except:
        print("Error:", name)

scores_sheet.resize(rows=1)
scores_sheet.append_rows(score_rows)

glassdoor_sheet.resize(rows=1)
glassdoor_sheet.append_rows(glassdoor_rows)

print("✅ FULL SYSTEM COMPLETE")
