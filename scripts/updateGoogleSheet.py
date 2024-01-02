import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import json
import logging
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("debug.log"),
                              logging.StreamHandler()])
logging.info("Script started")

# Function to load a JSON file and return the data
def load_json_file(file_path):
    logging.info(f"Loading JSON data from {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except Exception as e:
        logging.error(f"Error loading JSON file at {file_path}: {e}")
        return None
    

# Load the JSON data with error handling
def load_data():
    crafting_data_path = '../data/craftingDataFormat.json'
    nft_data_path = '../data/galaxyNFTsData.json'
    crafting_data = load_json_file(crafting_data_path)
    nft_data = load_json_file(nft_data_path)

    if crafting_data is None or nft_data is None:
        logging.error("Failed to load one or more JSON files. Exiting.")
        exit(1)

    return crafting_data, nft_data

# Parse the crafting data into a searchable format
def parse_crafting_data(crafting_data, nft_data):
    mint_to_name = {nft['mint']: nft['name'] for nft in nft_data}
    parsed_data = {}
    for item in crafting_data:
        item_name = mint_to_name.get(item['key'], item['data']['namespace'])
        parsed_data[item_name] = item
    return parsed_data

# Google Sheets integration functions
def auth_gspread():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(os.getenv('GOOGLE_CREDENTIALS_FILE'), scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logging.error(f"Failed to authenticate with Google Sheets: {e}")
        exit(1)

def get_worksheet(client, sheet_title):
    try:
        spreadsheet = client.open_by_key(os.getenv('SPREADSHEET_ID'))
        return spreadsheet.worksheet(sheet_title)
    except Exception as e:
        logging.error(f"Failed to access worksheet {sheet_title}: {e}")
        return None

def fetch_data_from_sheet(worksheet, data_range):
    try:
        return worksheet.get(data_range)
    except Exception as e:
        logging.error(f"Failed to fetch data from sheet: {e}")
        return None

def find_matching_recipes(crafting_requests, parsed_crafting_data):
    matched_recipes = []
    for item_name, quantity in crafting_requests:
        # Convert request item name to lower case for case-insensitive comparison
        item_name_lower = item_name.lower()
        
        # Find the matching recipe with case-insensitive key
        matched_recipe = next((value for key, value in parsed_crafting_data.items() if key.lower() == item_name_lower), None)

        if matched_recipe:
            matched_recipes.append((item_name, quantity, matched_recipe))
            logging.info(f"Match found: Item '{item_name}', Quantity '{quantity}', Recipe: {matched_recipe}")
        else:
            logging.info(f"No match found for item '{item_name}'")
    return matched_recipes

def post_matched_recipes_to_sheet(worksheet, matched_recipes):
    for index, (item_name, quantity, recipe) in enumerate(matched_recipes, start=1):
        try:
            worksheet.update(range_name=f'A{index}', values=[[recipe['data']['namespace']]])
            worksheet.update(range_name=f'B{index}', values=[[quantity]])
            logging.info(f"Posted recipe for '{item_name}' to the sheet at row {index}")
        except Exception as e:
            logging.error(f"Failed to update sheet for {item_name}: {e}")

def main():
    # Load data from JSON files
    crafting_data, nft_data = load_data()

    # Parse the crafting data
    parsed_crafting_data = parse_crafting_data(crafting_data, nft_data)
    logging.info("Crafting data parsed successfully")

    # Initialize the Google Sheets client
    client = auth_gspread()
    logging.info("Authenticated with Google Sheets successfully")

    # Fetch crafting requests data
    crafting_requests_worksheet = get_worksheet(client, os.getenv('CRAFTING_DATA_FECTH_SHEET'))
    if crafting_requests_worksheet is not None:
        crafting_requests_data = fetch_data_from_sheet(crafting_requests_worksheet, os.getenv('CRAFTING_DATA_FECTH_RANGE'))
        crafting_requests = [[row[0], int(row[1])] for row in crafting_requests_data if len(row) >= 2]
        logging.info(f"Fetched {len(crafting_requests)} crafting requests")

        # Find and post matched recipes
        matched_recipes = find_matching_recipes(crafting_requests, parsed_crafting_data)
        results_worksheet = get_worksheet(client, os.getenv('CRAFTING_RESULTS_SHEET'))
        if results_worksheet is not None:
            post_matched_recipes_to_sheet(results_worksheet, matched_recipes)
            logging.info("Matched recipes posted successfully")

if __name__ == "__main__":
    main()
