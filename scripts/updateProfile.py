import requests
import json
import os
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import warnings

# DeprecationWarning: [Deprecated][in version 6.0.0]: Method signature's arguments 'range_name' and 'values' will change their order. We recommend using named arguments for minimal impact. In addition, the argument 'values' will be mandatory of type: 'List[List]'. (ex) Worksheet.update(values = [[]], range_name=) sheet.update(range_name, values)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("debug.log"),
                              logging.StreamHandler()])
logging.info("Script started")

# Load environment variables
load_dotenv()

# Global variables for sheet titles and ranges
PLAYER_PROFILE_SHEET = os.getenv('PLAYER_PROFILE_SHEET')
PLAYER_PROFILE_RANGE = os.getenv('PLAYER_PROFILE_RANGE')
ACCOUNT_DATA_FETCH_SHEET = os.getenv('ACCOUNT_DATA_FETCH_SHEET')
ACCOUNT_DATA_FETCH_RANGE = os.getenv('ACCOUNT_DATA_FETCH_RANGE')
NODE_RPC_HOST = os.getenv('NODE_RPC_HOST')
WALLET_LOOKUP_KEY = os.getenv('WALLET_LOOKUP_KEY')
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
GALAXY_NFTS_DATA = os.getenv('GALAXY_NFTS_DATA')

def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


# Function to authenticate with Google Sheets
def auth_gspread():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logging.error(f"Failed to authenticate with Google Sheets: {e}")
        exit(1)


# Function to get worksheet
def get_worksheet(client, sheet_title):
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        return spreadsheet.worksheet(sheet_title)
    except Exception as e:
        logging.error(f"Failed to access worksheet {sheet_title}: {e}")
        return None
    

def fetch_blockchain_data(wallet_address):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [wallet_address, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}]
    }
    response = requests.post(NODE_RPC_HOST, headers={'Content-Type': 'application/json'}, json=payload)
    data = response.json()
    return {account['account']['data']['parsed']['info']['mint']: account['account']['data']['parsed']['info']['tokenAmount']['uiAmountString'] for account in data['result']['value']} if data else {}


def compare_and_merge_data(blockchain_data, nft_data):
    unknown_counter = 1  # Initialize a counter for unknown items
    merged_data = {}

    for mint_address, amount in blockchain_data.items():
        # Check if the mint_address exists in nft_data
        if mint_address in nft_data:
            name = nft_data[mint_address]
        else:
            name = f"Unknown Item {unknown_counter}"
            unknown_counter += 1  # Increment the counter for the next unknown item

        merged_data[name] = amount

    return merged_data


def post_to_google_sheets(data, sheet, range_name):
    # Filter out items with "Unknown Item" in their name
    filtered_data = {name: amount for name, amount in data.items() if not name.startswith("Unknown Item")}

    # Sort filtered data dictionary alphabetically by keys (names) and convert to list of lists
    sorted_data = sorted(filtered_data.items())
    values = [[name, amount] for name, amount in sorted_data]

    # Clear existing data in the specified range
    sheet.batch_clear([range_name])

    # Update the Google Sheets worksheet with new sorted and filtered data
    if values:
        sheet.update(range_name, values)
    else:
        logging.info("No data to update in Google Sheets.")


def convert_nft_data_to_dict(nft_list):
    nft_dict = {}
    for item in nft_list:
        mint_address = item['mint']  # Corrected key for mint address
        name = item['name']  # Key for name
        nft_dict[mint_address] = name
    return nft_dict


#def print_keys_of_first_item(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        if isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, dict):
                print("Keys in the first item:", first_item.keys())
            else:
                print("The first item in the list is not a dictionary.")
        else:
            print("The JSON file does not contain a list or is empty.")

# Call this function with the path to your JSON file
#print_keys_of_first_item(GALAXY_NFTS_DATA)


def main():
    # Load NFT data
    nft_data = convert_nft_data_to_dict(load_json_file(GALAXY_NFTS_DATA))

    # Authenticate with Google Sheets
    client = auth_gspread()
    player_profile_sheet = get_worksheet(client, PLAYER_PROFILE_SHEET)

    # Fetch wallet address directly from cell B3
    wallet_address = player_profile_sheet.acell(WALLET_LOOKUP_KEY).value

    # Fetch blockchain data
    blockchain_data = fetch_blockchain_data(wallet_address)
    #logging.info(f"Blockchain data: {blockchain_data}")

    # Compare and merge data
    final_data = compare_and_merge_data(blockchain_data, nft_data)

    # Post to Google Sheets
    account_resources_sheet = get_worksheet(client, ACCOUNT_DATA_FETCH_SHEET)
    post_to_google_sheets(final_data, account_resources_sheet, ACCOUNT_DATA_FETCH_RANGE)
    logging.info("Successfully updated Google Sheets.")

if __name__ == "__main__":
    main()
