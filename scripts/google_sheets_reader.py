import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")

def read_sheet():
    # Define scope for accessing Google Sheets and Drive
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    # ✅ Load credentials from correct path
    creds = ServiceAccountCredentials.from_json_keyfile_name("config/credentials.json", scope)

    # Authorize client
    client = gspread.authorize(creds)

    # Open spreadsheet and first sheet
    sheet = client.open(SPREADSHEET_NAME).sheet1

    # Fetch all rows as a list of dictionaries
    data = sheet.get_all_records()

    # Return it as a DataFrame
    return pd.DataFrame(data)