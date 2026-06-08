import requests
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os, json
import yfinance as yf

print("START FINAL SYSTEM")

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

sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1FkEqxI_ZhpdaUD1AxyV_oGTW3mHXo-sBb4FKGSZ8hD0")

jobs_sheet = sheet.worksheet("Jobs")
scores_sheet = sheet.worksheet("Scores")
financials_sheet = sheet.worksheet("Financials")

headers = {"User-Agent": "Mozilla/5.0"}

# ==========================================================
# ✅ JOBS (EXPANDED + FIXED)
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

# ✅ GREENHOUSE (keeps MSOs but now flexible)
for name, url in sources:
    try:
        soup = BeautifulSoup(requests.get(url, headers=headers).text, "html.parser")

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

            # ✅ FIXED COUNTING (was static before)
            job_counts[name] = job_counts.get(name, 0) + 1

            jobs.append([
                name, title, "Relevant", "Unknown",
                datetime.today().strftime('%Y-%m-%d'), href
            ])
    except:
        pass


# ==========================================================
# ✅ MarijuanaJobs
# ==========================================================
try:
    res = requests.get("https://www.marijuanajobscannabiscareers.com/job-search", headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    for link in soup.find_all("a"):
        title = link.get_text(strip=True)
        href = link.get("href")

        if not title or not href:
            continue

        if "job" not in href.lower():
            continue

        if not any(x in title.lower() for x in ["director","vp","operations"]):
            continue

        if href.startswith("/"):
            href = "https://www.marijuanajobscannabiscareers.com" + href

        key = "MJ" + title
        if key in seen:
            continue

        seen[key] = True

        # ✅ try to extract company
        company = "Unknown"
        if " at " in title.lower():
            parts = title.split(" at ")
            if len(parts) > 1:
                company = parts[-1].strip()

        job_counts[company] = job_counts.get(company, 0) + 1

        jobs.append([
            company,
            title,
            "Job Board",
            "Unknown",
            datetime.today().strftime('%Y-%m-%d'),
            href
        ])
except:
    pass


# ==========================================================
# ✅ Inweed
# ==========================================================
try:
    res = requests.get("https://jobsinweed.com/", headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    for link in soup.find_all("a"):
        title = link.get_text(strip=True)
        href = link.get("href")

        if not title or not href:
            continue

        if len(title) < 10:
            continue

        if not any(x in title.lower() for x in ["director","vp","manager","operations"]):
            continue

        if href.startswith("/"):
            href = "https://jobsinweed.com" + href

        key = "IW" + title
        if key in seen:
            continue

        seen[key] = True

        # ✅ optional company extraction
        company = "Unknown"
        if " at " in title.lower():
            parts = title.split(" at ")
            if len(parts) > 1:
                company = parts[-1].strip()

        job_counts[company] = job_counts.get(company, 0) + 1

        jobs.append([
            company,
            title,
            "Job Board",
            "Unknown",
            datetime.today().strftime('%Y-%m-%d'),
            href
        ])
except:
    pass


# ✅ WRITE JOBS
jobs_sheet.resize(rows=1)
jobs_sheet.append_rows(jobs)

# ==========================================================
# ✅ REST OF SYSTEM (UNCHANGED)
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

def financial_label(x):
    if x >= 8: return "Strong"
    elif x >= 5: return "Stable"
    else: return "Weak"

def job_label(x):
    if x >= 8: return "Aggressive"
    elif x >= 5: return "Moderate"
    else: return "Low"

def risk_label(x):
    if x >= 7: return "Low"
    elif x >= 4: return "Moderate"
    else: return "High"

def overall_label(x):
    if x >= 8: return "Strong Opportunity"
    elif x >= 6: return "Growth – Watch"
    elif x >= 4: return "Mixed"
    else: return "High Risk"

tickers = {
    "Curaleaf": "CURLF",
    "Cresco Labs": "CRLBF",
    "Green Thumb Industries": "GTBIF",
    "Trulieve": "TCNNF",
    "Verano": "VRNOF",
    "Ayr Wellness": "AYRWF",
    "Jushi": "JUSHF"
}

score_rows = []
financial_rows = []

def calc_risk(d):
    return round(
        d["de"]*0.3 +
        (1-d["cr"])*0.2 +
        abs(d["pm"])*0.2 +
        max(-d["rg"],0)*0.2 +
        (1/d["ic"] if d["ic"] else 1)*0.1
    ,2)

def normalize(v, low, high):
    return max(0, min((v - low)/(high-low),1))

for name, ticker in tickers.items():
    try:
        s = yf.Ticker(ticker)

        bs = s.balance_sheet
        fin = s.financials

        bs = bs.iloc[:,0] if not bs.empty else {}
        fin = fin.iloc[:,0] if not fin.empty else {}

        g = lambda x: float(bs.get(x,0))
        f = lambda x: float(fin.get(x,0))

        debt = g("Total Debt")
        equity = g("Total Stockholder Equity") or 1
        assets = g("Total Current Assets")
        liab = g("Total Current Liabilities") or 1

        rev = f("Total Revenue") or 1
        net = f("Net Income")
        ebit = f("Ebit")
        interest = abs(f("Interest Expense")) or 1

        try:
            ebitda = s.info.get("ebitda", None)
        except:
            ebitda = None

        if not ebitda:
            depreciation = f("Depreciation")
            ebitda = ebit + depreciation

        financial_rows.append([
            name,
            f"{round(rev/1e6,1)}M",
            f"{round(ebitda/1e6,1)}M",
            f"{round(net/1e6,1)}M",
            datetime.today().strftime('%Y-%m-%d')
        ])

        de = debt/equity
        cr = assets/liab
        pm = net/rev
        ic = ebit/interest

        rg = 0

        risk = calc_risk({"de":de,"cr":cr,"pm":pm,"rg":rg,"ic":ic})
        risk_norm = max(0,10-(risk*3))

        pm_s = normalize(pm,-0.2,0.2)
        rg_s = normalize(rg,-0.2,0.3)
        de_s = normalize(1-(de/3),0,1)
        cr_s = normalize(cr,0,2)

        financial_score = round((pm_s*0.3 + rg_s*0.3 + de_s*0.2 + cr_s*0.2)*10,2)

        job_score = min(job_counts.get(name,0)/10,1)*10

        rating = glassdoor_ratings.get(name,3.0)
        glass_score = round((rating/5)*10,2)

        total = round(
            financial_score*0.35 +
            job_score*0.25 +
            risk_norm*0.30 +
            glass_score*0.10
        ,2)

        score_rows.append([
            name,
            financial_score,
            round(job_score,2),
            round(risk_norm,2),
            glass_score,
            total,
            financial_label(financial_score),
            job_label(job_score),
            risk_label(risk_norm),
            overall_label(total)
        ])

    except:
        print("Error:", name)

scores_sheet.resize(rows=1)
scores_sheet.append_rows(score_rows)

financials_sheet.resize(rows=1)
financials_sheet.append_rows(financial_rows)

print("✅ FINAL SYSTEM COMPLETE")
