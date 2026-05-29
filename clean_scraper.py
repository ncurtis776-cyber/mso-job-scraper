import requests
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# =========================
# ✅ GOOGLE SHEETS SETUP
# =========================

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open("Cannabis MSO Intelligence Dashboard").worksheet("Jobs")

# =========================
# ✅ COMPANY SOURCES (GREENHOUSE)
# =========================

companies = [
    {"name": "Curaleaf", "url": "https://boards.greenhouse.io/embed/job_board?for=curaleaf"},
    {"name": "Cresco Labs", "url": "https://boards.greenhouse.io/embed/job_board?for=crescolabs"},
    {"name": "Green Thumb Industries", "url": "https://boards.greenhouse.io/embed/job_board?for=gtigrows"}
]

jobs = []

# ✅ DEDUPLICATION SET
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

                if "director" in lower_text or "project" in lower_text or "operations" in lower_text:

                    if href.startswith("/"):
                        href = "https://boards.greenhouse.io" + href

                    # ✅ UNIQUE KEY
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
# ✅ NUGWORK SCRAPER (NEW SOURCE)
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

            # ✅ FILTER TARGET ROLES
            if "director" in lower_text or "operations" in lower_text or "project" in lower_text:

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
# ✅ WRITE TO GOOGLE SHEET
# =========================

sheet.resize(rows=1)

if jobs:
    sheet.append_rows(jobs)

print("✅ SUCCESS - Jobs added:", len(jobs))
