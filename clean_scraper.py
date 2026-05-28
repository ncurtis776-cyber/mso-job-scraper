import requests
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os
import json

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ✅ LOAD CREDS FROM GITHUB SECRET (NOT FILE)
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1FkEqxI_ZhpdaUD1AxyV_oGTW3mHXo-sBb4FKGSZ8hD0").worksheet("Jobs")

companies = [
    {"name": "Curaleaf", "url": "https://boards.greenhouse.io/embed/job_board?for=curaleaf"},
    {"name": "Cresco Labs", "url": "https://boards.greenhouse.io/embed/job_board?for=crescolabs"},
    {"name": "Green Thumb Industries", "url": "https://boards.greenhouse.io/embed/job_board?for=gtigrows"}
]

jobs = []

for company in companies:
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

                jobs.append([
                    company["name"],
                    text,
                    "Relevant Role",
                    "Unknown",
                    datetime.today().strftime('%Y-%m-%d'),
                    href
                ])

sheet.resize(rows=1)

if jobs:
    sheet.append_rows(jobs)

print("SUCCESS - Jobs added:", len(jobs))
