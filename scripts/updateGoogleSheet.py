import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()
# Now you can use os.getenv to access your variables
service_key_path = os.getenv('GOOGLE_CREDENTIALS_FILE')
spreadsheet_id = os.getenv('SPREADSHEET_ID')
spreadsheet_sheet = os.getenv('CRAFTING_RESULTS_SHEET')
spreadsheet_range = os.getenv('CRAFTING_RESULTS_RANGE')

# Set up the connection to Google Sheets
def auth_gspread():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    # Make sure to replace 'path/to/service_account.json' with the actual path to your downloaded service account credentials JSON file
    creds = ServiceAccountCredentials.from_json_keyfile_name(service_key_path, scope)
    client = gspread.authorize(creds)
    return client

# Write "Hello, World!" to cell A1 of the Google Sheet titled "RecipeCalcs"
def update_sheet(client, spreadsheet_id):
    # Opening the spreadsheet by ID
    spreadsheet = client.open_by_key(spreadsheet_id)
    # Select the specific worksheet by its title specified in .env
    worksheet = spreadsheet.worksheet(spreadsheet_sheet)

    # Clears the entire sheet
    worksheet.clear()
    
    # Update a cell in the selected worksheet
    worksheet.update(spreadsheet_range, 'Hello, World! I am a Python script test #2!')

def main():
    client = auth_gspread()
    update_sheet(client, spreadsheet_id)
    print("Updated the Google Sheet.")


if __name__ == "__main__":
    main()
