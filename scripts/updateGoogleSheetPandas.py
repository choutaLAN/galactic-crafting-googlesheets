import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import json
import logging
import pandas as pd

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("debug.log"),
                              logging.StreamHandler()])
logging.info("Script started")

def load_json_to_dataframe(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            df = pd.json_normalize(data)
            return df
    except Exception as e:
        logging.error(f"Error loading JSON file at {file_path}: {e}")
        return pd.DataFrame()

def load_data():
    crafting_data_path = '../data/craftingDataFormat.json'
    nft_data_path = '../data/galaxyNFTsData.json'
    
    crafting_data_df = load_json_to_dataframe(crafting_data_path)
    nft_data_df = load_json_to_dataframe(nft_data_path)

    if crafting_data_df.empty or nft_data_df.empty:
        logging.error("Failed to load one or more JSON files. Exiting.")
        exit(1)

    return crafting_data_df, nft_data_df

def find_matching_recipes(crafting_requests, crafting_data_df, nft_data_df):
    matched_recipes = []

    for item_name, request_quantity in crafting_requests:
        recipe_df = crafting_data_df[crafting_data_df['data.namespace'].str.lower() == item_name.lower()]
        if not recipe_df.empty:
            recipe = recipe_df.iloc[0]
            total_ingredients = {}
            for ingredient in recipe['ingredients']:
                name = nft_data_df.loc[nft_data_df['mint'] == ingredient['mint'], 'name'].values[0]
                amount = int(ingredient['amount']) * request_quantity
                total_ingredients[name] = total_ingredients.get(name, 0) + amount
            matched_recipes.append((item_name, total_ingredients))

    return matched_recipes

def prepare_for_batch_update(matched_recipes):
    cell_values = [['INGREDIENT', 'AMOUNT']]
    for item_name, ingredients in matched_recipes:
        for name, amount in ingredients.items():
            cell_values.append([name, amount])
    return cell_values

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

def main():
    crafting_data_df, nft_data_df = load_data()
    client = auth_gspread()

    crafting_requests_worksheet = get_worksheet(client, os.getenv('CRAFTING_DATA_FECTH_SHEET'))
    if crafting_requests_worksheet is not None:
        crafting_requests_data = fetch_data_from_sheet(crafting_requests_worksheet, os.getenv('CRAFTING_DATA_FECTH_RANGE'))
        crafting_requests = [[row[0], int(row[1])] for row in crafting_requests_data if len(row) >= 2]

        matched_recipes = find_matching_recipes(crafting_requests, crafting_data_df, nft_data_df)
        cell_values = prepare_for_batch_update(matched_recipes)

        results_worksheet = get_worksheet(client, os.getenv('CRAFTING_RESULTS_SHEET'))
        if results_worksheet is not None:
            results_worksheet.clear()
            logging.info("Worksheet cleared of old data.")
            results_worksheet.update('A1:B' + str(len(cell_values)), cell_values)
            logging.info("Batch update completed for all ingredients and quantities.")
    else:
        logging.info("Could not fetch crafting requests data")

if __name__ == "__main__":
    main()
