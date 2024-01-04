import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import json
import logging
import pandas as pd
import warnings
import random
# Suppress DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("debug.log"),
                              logging.StreamHandler()])
logging.info("Script started")


crystal_lattice_variants = {
    'Diamond': 'Crystal Lattice 1',
    'Rochinol': 'Crystal Lattice 2',
    'Arco': 'Crystal Lattice 3'
}

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


def find_player_faction(worksheet):
    """
    Dynamically find the row containing 'FACTION_LOOKUP_KEY' and return the faction name.
    """
    try:
        # Search for the cell containing 'Faction' manually
        cell = None
        all_cells = worksheet.findall('Faction') + worksheet.findall('faction')
        if all_cells:
            cell = all_cells[0]

        if cell is None:
            raise ValueError("Faction cell not found")

        faction_cell_row = cell.row
        faction_name = worksheet.cell(faction_cell_row, cell.col + 1).value
        return faction_name
    except Exception as e:
        logging.error(f"Error finding player faction: {e}")
        return None
    

def find_player_crystal_choice(worksheet, lookup_key):
    """
    Find the row containing 'lookup_key' in a case-insensitive manner
    and return the corresponding faction crystal or None.
    """
    try:
        cell = worksheet.find(lookup_key, in_column=1)
        if cell is None:
            raise ValueError(f"{lookup_key} cell not found")

        crystal_choice = worksheet.cell(cell.row, 2).value.strip().lower()
        return None if crystal_choice.lower() == 'none' else crystal_choice
    except Exception as e:
        logging.error(f"Error finding player crystal choice: {e}")
        return None


def get_player_ingredient_quantities(worksheet, data_range):
    """
    Retrieve the player's available ingredients and their quantities from a specified range.
    """
    try:
        logging.info(f"Attempting to fetch player ingredients from range: {data_range}")
        ingredients_data = worksheet.get(data_range)
        
        if not ingredients_data:
            logging.info("No player ingredients found in the specified range.")
            return {}

        player_ingredients = {row[0]: int(row[1].replace(',', '')) for row in ingredients_data if row[0] and row[1]}
        
        # Log the fetched player ingredients
        logging.info("Fetched player ingredients and quantities:")
        for ingredient, quantity in player_ingredients.items():
            logging.info(f"{ingredient}: {quantity}")

        return player_ingredients
    except Exception as e:
        logging.error(f"Error fetching player ingredients: {e}")
        return {}



def choose_crystal_lattice_variant(player_faction, player_ingredients, parsed_crafting_data, nft_data):
    nft_df = pd.DataFrame(nft_data)

    faction_crystal_mapping = {
        'MUD': 'Diamond',
        'ONI': 'Rochinol',
        'USTUR': 'Arco'
    }
    crystal_to_recipe_mapping = {
        'Diamond': 'Crystal Lattice 1',
        'Rochinol': 'Crystal Lattice 2',
        'Arco': 'Crystal Lattice 3'
    }

    chosen_crystal = faction_crystal_mapping.get(player_faction, 'Diamond')
    max_quantity = player_ingredients.get(chosen_crystal, 0)

    equal_quantities = []
    for crystal, _ in crystal_to_recipe_mapping.items():
        quantity = player_ingredients.get(crystal, 0)
        if quantity > 0:
            if quantity > max_quantity:
                chosen_crystal = crystal
                max_quantity = quantity
                equal_quantities = []
            elif quantity == max_quantity and crystal != chosen_crystal:
                equal_quantities.append(crystal)

    if equal_quantities:
        equal_quantities.append(chosen_crystal)
        if faction_crystal_mapping[player_faction] in equal_quantities:
            chosen_crystal = faction_crystal_mapping[player_faction]
        else:
            # Randomly select a crystal when none align with the faction
            chosen_crystal = random.choice(equal_quantities)

    # logging.info(f"Chosen crystal based on account data: {chosen_crystal}")

    crystal_recipe = crystal_to_recipe_mapping.get(chosen_crystal, 'Crystal Lattice 1')
    # logging.info(f"Using recipe: {crystal_recipe} for crystal: {chosen_crystal}")

    # Find the matched recipe for the chosen crystal
    matched_recipe = parsed_crafting_data.get(crystal_recipe)

    if matched_recipe and 'ingredients' in matched_recipe:
        ingredients_df = pd.DataFrame(matched_recipe['ingredients'])
        ingredients_df['total_quantity'] = ingredients_df['amount'].astype(int)  # Assuming quantity 1 for now

        merged_df = ingredients_df.merge(nft_df[['mint', 'name']], on='mint', how='left')
        merged_df['name'].fillna('Unknown Ingredient', inplace=True)

        consolidated_df = merged_df.groupby('name')['total_quantity'].sum().reset_index()
        ingredient_details = list(consolidated_df.itertuples(index=False, name=None))

        # logging.info(f"Matched recipe for '{crystal_recipe}' with ingredients: {ingredient_details}")
        return crystal_recipe, ingredient_details
    else:
        logging.warning(f"No matched recipe found for '{crystal_recipe}'.")
        return crystal_recipe, []




def find_matching_recipes(crafting_requests, parsed_crafting_data, nft_data):
    nft_df = pd.DataFrame(nft_data)

    # Create a DataFrame from crafting_requests for vectorized operations
    requests_df = pd.DataFrame(crafting_requests, columns=['item_name', 'request_quantity'])
    requests_df['item_name'] = requests_df['item_name'].str.strip().str.title()

    # Vectorized lookup for matched recipes
    requests_df['matched_recipe'] = requests_df['item_name'].map(parsed_crafting_data)

    # Filter out rows without a matched recipe
    valid_requests_df = requests_df.dropna(subset=['matched_recipe'])

    # Extract 'ingredients' into a separate column
    valid_requests_df['ingredients'] = valid_requests_df['matched_recipe'].apply(lambda x: x.get('ingredients') if isinstance(x, dict) else None)

    # Expand the ingredients information
    expanded_df = valid_requests_df.explode('ingredients').reset_index(drop=True)
    expanded_df = pd.concat([expanded_df.drop(['matched_recipe'], axis=1), expanded_df['ingredients'].apply(pd.Series)], axis=1)

    # Calculate total quantities required
    expanded_df['total_quantity'] = expanded_df['amount'].astype(int) * expanded_df['request_quantity']

    # Merge with NFT data for additional details
    merged_df = expanded_df.merge(nft_df[['mint', 'name']], on='mint', how='left')
    merged_df['name'].fillna('Unknown Ingredient', inplace=True)

    # Group and sum the quantities
    final_df = merged_df.groupby(['item_name', 'name'])['total_quantity'].sum().reset_index()

    # Convert back to the desired format
    matched_recipes = final_df.groupby('item_name').apply(lambda x: x[['name', 'total_quantity']].to_records(index=False).tolist()).to_dict()

    return matched_recipes



def post_ingredients_to_sheet(worksheet, matched_recipes):
    # Prepare a list of update requests
    update_requests = []

    # Flatten the matched_recipes into a list of tuples for easier processing
    flattened_data = [(item_name, ingredient[0], ingredient[1]) for item_name, ingredients in matched_recipes.items() for ingredient in ingredients]

    # Create a DataFrame from the flattened data
    df = pd.DataFrame(flattened_data, columns=['item_name', 'name', 'total_quantity'])

    # Group by 'name' to consolidate ingredients from all items
    consolidated_df = df.groupby('name')['total_quantity'].sum().reset_index()

    # Prepare the cell values to be updated
    cell_values = [['INGREDIENT', 'AMOUNT']] + consolidated_df.values.tolist()

    # Add the update request for the consolidated ingredients
    update_requests.append({
        'range': 'A1:B' + str(len(cell_values)),
        'values': cell_values
    })

    # Send all updates in one batch request
    worksheet.batch_update(update_requests)
    logging.info("Batch update completed for consolidated ingredients and quantities.")




def get_ingredient_details(ingredients, nft_data):
    ingredient_details = []
    mint_to_name = {nft['mint']: nft['name'] for nft in nft_data}
    for ingredient in ingredients:
        mint_address = ingredient['mint']
        quantity = ingredient['amount']
        name = mint_to_name.get(mint_address, "Unknown Ingredient")
        ingredient_details.append((name, quantity))
        # logging.info(f"Ingredient: {name}, Quantity: {quantity}, Mint Address: {mint_address}")
    return ingredient_details


def post_matched_recipes_to_sheet(worksheet, matched_recipes):
    for index, (item_name, quantity, recipe, ingredients) in enumerate(matched_recipes, start=1):
        try:
            ingredient_text = ", ".join([f"{name}: {qty}" for name, qty in ingredients])
            worksheet.update(range_name=f'A{index}', values=[[item_name]])
            worksheet.update(range_name=f'B{index}', values=[[quantity]])
            worksheet.update(range_name=f'C{index}', values=[[ingredient_text]])
            # logging.info(f"Posted recipe for '{item_name}' with ingredients '{ingredient_text}' to the sheet at row {index}")
        except Exception as e:
            logging.error(f"Failed to update sheet for {item_name}: {e}")


def find_raw_ingredients(item, parsed_data, mint_to_name, crystal_recipe, depth=0, max_depth=7):
    """
    Recursively find the raw ingredients required for an item.
    """
    if depth > max_depth:
        return []

    item_key = str(item).strip().title()

    # Handle the 'Crystal Lattice' recipe specifically
    if item_key == 'Crystal Lattice':
        # logging.info(f"'Crystal Lattice' detected. Using recipe: {crystal_recipe}")
        item_key = crystal_recipe

    if item_key not in parsed_data or 'ingredients' not in parsed_data[item_key]:
        return [(item_key, 1)]

    raw_ingredients = []
    for ingredient in parsed_data[item_key]['ingredients']:
        ingredient_mint = ingredient['mint']
        ingredient_name = mint_to_name.get(ingredient_mint, "Unknown Ingredient")
        
        try:
            ingredient_quantity = int(ingredient['amount'])
        except ValueError:
            # logging.error(f"Invalid quantity for ingredient '{ingredient_name}': {ingredient['amount']}")
            continue

        sub_ingredients = find_raw_ingredients(ingredient_name, parsed_data, mint_to_name, crystal_recipe, depth + 1, max_depth)

        for sub_ingredient_name, sub_quantity in sub_ingredients:
            raw_ingredients.append((sub_ingredient_name, sub_quantity * ingredient_quantity))

    return raw_ingredients



def post_raw_ingredients_to_sheet(worksheet, matched_recipes, parsed_crafting_data, mint_to_name, crystal_recipe, crystal_ingredients):
    all_raw_ingredients = []

    # Iterate over the matched recipes dictionary
    for item_name, ingredients in matched_recipes.items():
        for ingredient in ingredients:
            ingredient_name, request_quantity = ingredient
            raw_ingredients = find_raw_ingredients(item_name, parsed_crafting_data, mint_to_name, crystal_recipe)
            raw_ingredients = [(name, qty * request_quantity) for name, qty in raw_ingredients]
            all_raw_ingredients.extend(raw_ingredients)

    # Process raw ingredients for the chosen crystal recipe
    if crystal_ingredients:
        for ingredient_name, total_quantity in crystal_ingredients:
            raw_ingredients = find_raw_ingredients(ingredient_name, parsed_crafting_data, mint_to_name, crystal_recipe)
            all_raw_ingredients.extend([(name, qty * total_quantity) for name, qty in raw_ingredients])

    # Aggregate quantities for each raw ingredient
    df = pd.DataFrame(all_raw_ingredients, columns=['name', 'quantity'])
    aggregated_ingredients = df.groupby('name', as_index=False).sum()

    # Convert to a list of lists for worksheet update
    cell_values = [['RAW INGREDIENT', 'AMOUNT']] + aggregated_ingredients.values.tolist()

    # Update the worksheet in one batch
    worksheet.update('D1:E' + str(len(cell_values)), cell_values)



def main():
    # Load data from JSON files
    crafting_data, nft_data = load_data()

    # Parse the crafting data
    parsed_crafting_data = parse_crafting_data(crafting_data, nft_data)
    logging.info("Crafting data parsed successfully")

    # Create the mint_to_name dictionary
    mint_to_name = {nft['mint']: nft['name'] for nft in nft_data}

   # Initialize the Google Sheets client
    client = auth_gspread()
    logging.info("Authenticated with Google Sheets successfully")

    player_profile_worksheet = get_worksheet(client, os.getenv('PLAYER_PROFILE_SHEET'))
    account_data_worksheet = get_worksheet(client, os.getenv('ACCOUNT_DATA_FETCH_SHEET'))
    
    if player_profile_worksheet is None or account_data_worksheet is None:
        return  # Error already logged in get_worksheet

    player_crystal_choice = find_player_crystal_choice(player_profile_worksheet, os.getenv('CRYSTAL_LOOKUP_KEY'))
    logging.info(f"Player's crystal choice: {player_crystal_choice}")

    chosen_crystal_recipe, crystal_ingredients = None, []
    if player_crystal_choice and player_crystal_choice.title() in crystal_lattice_variants:
        chosen_crystal_recipe = crystal_lattice_variants[player_crystal_choice.title()]
        logging.info(f"Using player's chosen crystal recipe: {chosen_crystal_recipe}")
    else:
        player_faction = find_player_faction(player_profile_worksheet)
        player_ingredients = get_player_ingredient_quantities(account_data_worksheet, os.getenv('ACCOUNT_DATA_FETCH_RANGE'))
        chosen_crystal_recipe, crystal_ingredients = choose_crystal_lattice_variant(player_faction, player_ingredients, parsed_crafting_data, nft_data)
        logging.info(f"Chosen Crystal Lattice Recipe based on faction: {chosen_crystal_recipe} with ingredients: {crystal_ingredients}")

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
            # Post initial ingredients and their quantities to the sheet in batch
            post_ingredients_to_sheet(results_worksheet, matched_recipes)

            # Post raw ingredients to the sheet, now also passing mint_to_name
            post_raw_ingredients_to_sheet(results_worksheet, matched_recipes, parsed_crafting_data, mint_to_name, chosen_crystal_recipe, crystal_ingredients)

            logging.info("Headers and ingredients with quantities posted successfully")

if __name__ == "__main__":
    main()