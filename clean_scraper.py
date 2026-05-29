import gspread
from google.oauth2.service_account import Credentials
import os
import json

print("START TEST")

# ✅ Make sure secret exists
if "GOOGLE_CREDS" not in os.environ:
    raise Exception("GOOGLE_CREDS missing")

# ✅ Load credentials
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

print("✅ AUTH WORKED")

# ✅ Use direct sheet URL (no chance of wrong file)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1FkEqxI_ZhpdaUD1AxyV_oGTW3mHXo-sBb4FKGSZ8hD0").worksheet("Jobs")

print("✅ SHEET CONNECTED")

# ✅ FORCE WRITE
sheet.append_row(["TEST SUCCESS", "If you see this, it works"])

print("✅ WRITE COMPLETE")
