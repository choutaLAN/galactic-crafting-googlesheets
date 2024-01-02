import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import json
import logging
import pandas as pd

load_dotenv()
print(os.getenv('CRAFTING_DATA_FETCH_SHEET'))  # This should print the actual sheet name


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


def find_matching_recipes(crafting_requests, parsed_crafting_data, nft_data):
    # Debugging: Print out the parsed crafting data and mint to name dictionary
    print("Parsed Crafting Data: ", parsed_crafting_data)
    mint_to_name = {nft['mint']: nft['name'] for nft in nft_data}
    print("Mint to Name Dictionary: ", mint_to_name)

    # Convert NFT data to DataFrame for quick lookups
    nft_df = pd.DataFrame(nft_data)
    
    matched_recipes = []
    for item_name, request_quantity in crafting_requests:
        # Normalize the item name to match the parsed_crafting_data keys
        item_name_normalized = item_name.strip().title()

        # Debug print to check the normalized item name
        print(f"Normalized Item Name: '{item_name_normalized}'")

        matched_recipe = parsed_crafting_data.get(item_name_normalized)
        
        if matched_recipe and 'ingredients' in matched_recipe:
            ingredients_df = pd.DataFrame(matched_recipe['ingredients'])
            if not ingredients_df.empty:
                ingredients_df['total_quantity'] = ingredients_df['amount'].astype(int) * request_quantity
                
                merged_df = ingredients_df.merge(nft_df[['mint', 'name']], on='mint', how='left')
                merged_df['name'].fillna('Unknown Ingredient', inplace=True)
                
                consolidated_df = merged_df.groupby('name')['total_quantity'].sum().reset_index()
                ingredient_details = list(consolidated_df.itertuples(index=False, name=None))
                
                matched_recipes.append((item_name, request_quantity, matched_recipe, ingredient_details))
                logging.info(f"Matched recipe for '{item_name}' with ingredients.")
            else:
                logging.warning(f"Recipe found for '{item_name}' but no ingredients present.")
        else:
            logging.warning(f"No matched recipe found for '{item_name}'.")
    
    return matched_recipes



def post_ingredients_to_sheet(worksheet, matched_recipes):
    # Clear the worksheet of old data
    worksheet.clear()
    logging.info("Worksheet cleared of old data.")

    # Gather all ingredients into a list before using concat to avoid ValueError
    all_ingredients = [pd.DataFrame(data[3], columns=['name', 'total_quantity']) for data in matched_recipes if data[3]]

    # Check if we have any ingredients to process
    if all_ingredients:
        # Using pandas to consolidate ingredients
        consolidated_ingredients_df = pd.concat(all_ingredients)
        consolidated_ingredients = consolidated_ingredients_df.groupby('name', as_index=False).sum()

        # Convert the DataFrame to a list of lists to update the sheet in one batch
        cell_values = [['INGREDIENT', 'AMOUNT']] + consolidated_ingredients.values.tolist()

        # Update the sheet in one batch
        worksheet.update('A1:B' + str(len(cell_values)), cell_values)
        logging.info("Batch update completed for consolidated ingredients and quantities.")
    else:
        logging.info("No ingredients found to post to the sheet.")


def get_ingredient_details(ingredients, nft_data):
    ingredient_details = []
    mint_to_name = {nft['mint']: nft['name'] for nft in nft_data}
    for ingredient in ingredients:
        mint_address = ingredient['mint']
        quantity = ingredient['amount']
        name = mint_to_name.get(mint_address, "Unknown Ingredient")
        ingredient_details.append((name, quantity))
        logging.info(f"Ingredient: {name}, Quantity: {quantity}, Mint Address: {mint_address}")
    return ingredient_details


def post_matched_recipes_to_sheet(worksheet, matched_recipes):
    for index, (item_name, quantity, recipe, ingredients) in enumerate(matched_recipes, start=1):
        try:
            ingredient_text = ", ".join([f"{name}: {qty}" for name, qty in ingredients])
            worksheet.update(range_name=f'A{index}', values=[[item_name]])
            worksheet.update(range_name=f'B{index}', values=[[quantity]])
            worksheet.update(range_name=f'C{index}', values=[[ingredient_text]])
            logging.info(f"Posted recipe for '{item_name}' with ingredients '{ingredient_text}' to the sheet at row {index}")
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
    crafting_requests_worksheet = get_worksheet(client, os.getenv('CRAFTING_DATA_FETCH_SHEET'))
    if crafting_requests_worksheet is not None:
        crafting_requests_data = fetch_data_from_sheet(crafting_requests_worksheet, os.getenv('CRAFTING_DATA_FETCH_RANGE'))
        crafting_requests = [[row[0], int(row[1])] for row in crafting_requests_data if len(row) >= 2]
        logging.info(f"Crafting requests fetched: {crafting_requests}")

        # Find matched recipes
        matched_recipes = find_matching_recipes(crafting_requests, parsed_crafting_data, nft_data)
        logging.info(f"Found {len(matched_recipes)} matched recipes.")

        # Get the results worksheet
        results_worksheet = get_worksheet(client, os.getenv('CRAFTING_RESULTS_SHEET'))
        if results_worksheet is not None:
            # Post ingredients and their quantities to the sheet in batch
            post_ingredients_to_sheet(results_worksheet, matched_recipes)

            logging.info("Headers and ingredients with quantities posted successfully")

if __name__ == "__main__":
    main()