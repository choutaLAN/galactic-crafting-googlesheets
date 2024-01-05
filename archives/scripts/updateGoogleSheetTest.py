import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import json
import logging
import pandas as pd
import warnings
import random
import time
from collections import defaultdict
# Suppress DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("debug.log"),
                              logging.StreamHandler()])
logging.info("Script started")

# A simple in-memory cache to store data with expiration time.
class SimpleCache:
    def __init__(self):
        self._cache = defaultdict(dict)

    def set(self, key, value, ttl):
        self._cache[key] = {
            'value': value,
            'expire_at': time.time() + ttl
        }

    def get(self, key):
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.time() > entry['expire_at']:
            del self._cache[key]
            return None
        return entry['value']

    def contents(self):
        return self._cache
    
    def get_permanent(self, key):
        return self._cache.get(key, {}).get('value')
    
    def set_permanent_with_refresh(self, key, value, refresh_interval=None):
        self._cache[key] = {
            'value': value,
            'last_update': time.time(),
            'refresh_interval': refresh_interval
        }

    def get_with_optional_refresh(self, key):
        entry = self._cache.get(key)
        if not entry:
            return None
        if (entry.get('refresh_interval') is not None and
                (time.time() - entry['last_update'] > entry['refresh_interval'])):
            # The data is considered stale and needs to be refreshed
            return None
        return entry['value']

    def invalidate(self, key):
        if key in self._cache:
            del self._cache[key]

    def refresh(self, key):
        if key in self._cache:
            self._cache[key]['last_update'] = 0  # Force refresh on next get_with_optional_refresh call

# Global cache object
cache = SimpleCache()



def fetch_data_with_caching(client, sheet_title, data_range, ttl=3600):
    cache_key = f"{sheet_title}_{data_range}"
    data = cache.get(cache_key)
    if data is None:
        worksheet = get_worksheet(client, sheet_title)
        if worksheet:
            data = worksheet.get(data_range)
            cache.set(cache_key, data, ttl)
    return data


# Google Sheets integration functions
def get_worksheet(client, sheet_title):
    try:
        spreadsheet = client.open_by_key(os.getenv('SPREADSHEET_ID'))
        return spreadsheet.worksheet(sheet_title)
    except Exception as e:
        logging.error(f"Failed to access worksheet {sheet_title}: {e}")
        return None


crystal_lattice_variants = {
    'Diamond': 'Crystal Lattice 1',
    'Rochinol': 'Crystal Lattice 2',
    'Arco': 'Crystal Lattice 3'
}

framework_variants = {
    'Framework 1 (Iron)': 'Framework 1',
    'Framework 2 (Steel)': 'Framework 2'
}

toolkit_variants = {
    'Toolkit 1 (Iron)': 'Toolkit 1',
    'Toolkit 2 (Steel)': 'Toolkit 2'
}

def choose_framework_and_toolkit_variants(player_ingredients):
    iron_count = player_ingredients.get('Iron', 0)
    carbon_count = player_ingredients.get('Carbon', 0)

    # Determine if Steel or Iron should be used
    if carbon_count >= iron_count * 2:
        framework_variant = 'Framework 2 (Steel)'
        toolkit_variant = 'Toolkit 2 (Steel)'
    else:
        framework_variant = 'Framework 1 (Iron)'
        toolkit_variant = 'Toolkit 1 (Iron)'

    return framework_variant, toolkit_variant

# Global variables for sheet titles and ranges
PLAYER_PROFILE_SHEET = os.getenv('PLAYER_PROFILE_SHEET')
PLAYER_PROFILE_RANGE = os.getenv('PLAYER_PROFILE_RANGE')
ACCOUNT_DATA_FETCH_SHEET = os.getenv('ACCOUNT_DATA_FETCH_SHEET')
ACCOUNT_DATA_FETCH_RANGE = os.getenv('ACCOUNT_DATA_FETCH_RANGE')
CRAFTING_DATA_FETCH_SHEET = os.getenv('CRAFTING_DATA_FETCH_SHEET')
CRAFTING_DATA_FETCH_RANGE = os.getenv('CRAFTING_DATA_FETCH_RANGE')
CRAFTING_RESULTS_SHEET = os.getenv('CRAFTING_RESULTS_SHEET')
CRYSTAL_LOOKUP_KEY = os.getenv('CRYSTAL_LOOKUP_KEY')
FACTION_LOOKUP_KEY = os.getenv('FACTION_LOOKUP_KEY')
CACHE_EXPIRY = int(os.getenv('CACHE_EXPIRY', 3600)) # Default cache expiry is 1 hour
CACHE_EXPIRY_PERMANENT = int(os.getenv('CACHE_EXPIRY_PERMANENT', 86400)) # Default cache expiry is 1 day
FRAMEWORK_LOOKUP_KEY=os.getenv('FRAMEWORK_LOOKUP_KEY')
TOOLKIT_LOOKUP_KEY=os.getenv('TOOLKIT_LOOKUP_KEY')


# Simple cache dictionary
json_data_cache = {}

def load_json_file(file_path):
    # Check if data is already in cache
    if file_path in json_data_cache:
        logging.info(f"Loading {file_path} from cache")
        return json_data_cache[file_path]

    logging.info(f"Loading JSON data from {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            # Save data to cache
            json_data_cache[file_path] = data
        return data
    except Exception as e:
        logging.error(f"Error loading JSON file at {file_path}: {e}")
        return None

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
def parse_crafting_data(crafting_data, nft_data, force_refresh=False):
    mint_to_name = cache.get_with_optional_refresh('mint_to_name')
    if mint_to_name is None or force_refresh:
        mint_to_name = {nft['mint']: nft['name'] for nft in nft_data}
        cache.set_permanent_with_refresh('mint_to_name', mint_to_name, refresh_interval=CACHE_EXPIRY_PERMANENT)
    parsed_data = {}
    for item in crafting_data:
        item_name = mint_to_name.get(item['key'], item['data']['namespace'])
        parsed_data[item_name] = item
    return parsed_data
# Call this function when you need to see the contents of the cache
#print(cache.contents())



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

def fetch_user_preferences(client, sheet_title, framework_key, toolkit_key):
    framework_key = FRAMEWORK_LOOKUP_KEY
    toolkit_key = TOOLKIT_LOOKUP_KEY
    worksheet = get_worksheet(client, sheet_title)
    data = worksheet.get_all_values()
    preferences = {'framework': 'none', 'toolkit': 'none'}

    for row in data:
        if framework_key in row:
            preferences['framework'] = row[row.index(framework_key) + 1].strip().title()
        if toolkit_key in row:
            preferences['toolkit'] = row[row.index(toolkit_key) + 1].strip().title()

    return preferences


def find_player_faction(client):
    # Use the global variables instead of fetching from os.getenv() every time
    data = fetch_data_with_caching(client, PLAYER_PROFILE_SHEET, PLAYER_PROFILE_RANGE, ttl=CACHE_EXPIRY)

    # Search for the faction key in the cached data
    faction_name = None
    for row in data:
        if FACTION_LOOKUP_KEY in row:
            faction_index = row.index(FACTION_LOOKUP_KEY)
            if faction_index + 1 < len(row):  # Check if next cell exists
                faction_name = row[faction_index + 1]
                break

    if faction_name is None:
        logging.error(f"Error finding player faction: {FACTION_LOOKUP_KEY} not found in the data.")
    else:
        logging.info(f"Player faction found: {faction_name}")

    return faction_name
    

def find_player_crystal_choice(client):
    # Fetch the data from cache or sheets using global variables
    data = fetch_data_with_caching(client, PLAYER_PROFILE_SHEET, PLAYER_PROFILE_RANGE, ttl=CACHE_EXPIRY)

    # Search for the crystal choice within the cached data
    crystal_choice = None
    for row in data:
        # Create a case-insensitive search for the lookup key in each row
        row_lower = [cell.lower() for cell in row]  # Convert each cell in the row to lowercase
        if CRYSTAL_LOOKUP_KEY.lower() in row_lower:
            # Get the index of the lookup key and retrieve the adjacent value
            crystal_choice = row[row_lower.index(CRYSTAL_LOOKUP_KEY.lower()) + 1].strip().lower()
            break

    if crystal_choice is None:
        logging.error(f"Error finding player crystal choice: {CRYSTAL_LOOKUP_KEY} not found in the data.")
    elif crystal_choice == 'none':
        logging.info("Player has not specified a crystal choice (set to 'none').")
    else:
        logging.info(f"Player's crystal choice found: {crystal_choice}")

    return crystal_choice



def get_player_ingredient_quantities(client):

    # Fetch the data from cache or sheets using global variables
    data = fetch_data_with_caching(client, ACCOUNT_DATA_FETCH_SHEET, ACCOUNT_DATA_FETCH_RANGE, ttl=CACHE_EXPIRY)

    # Convert the fetched data into a dictionary of ingredients and quantities
    player_ingredients = {}
    for row in data:
        if len(row) >= 2 and row[0] and row[1]:
            ingredient = row[0].strip()
            quantity = row[1].strip().replace(',', '')  # Remove commas for conversion to int
            try:
                player_ingredients[ingredient] = int(quantity)
            except ValueError:
                logging.error(f"Invalid quantity for ingredient '{ingredient}': {quantity}")
                continue

    if not player_ingredients:
        logging.info("No player ingredients found in the specified range.")
    else:
        # Log the fetched player ingredients
        for ingredient, quantity in player_ingredients.items():
            logging.info(f"{ingredient}: {quantity}")

    return player_ingredients


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

    logging.info(f"Chosen crystal based on account data: {chosen_crystal}")

    crystal_recipe = crystal_to_recipe_mapping.get(chosen_crystal, 'Crystal Lattice 1')
    logging.info(f"Using recipe: {crystal_recipe} for crystal: {chosen_crystal}")

    # Find the matched recipe for the chosen crystal
    matched_recipe = parsed_crafting_data.get(crystal_recipe)

    if matched_recipe and 'ingredients' in matched_recipe:
        ingredients_df = pd.DataFrame(matched_recipe['ingredients'])
        ingredients_df['total_quantity'] = ingredients_df['amount'].astype(int)  # Assuming quantity 1 for now

        merged_df = ingredients_df.merge(nft_df[['mint', 'name']], on='mint', how='left')
        merged_df['name'].fillna('Unknown Ingredient', inplace=True)

        consolidated_df = merged_df.groupby('name')['total_quantity'].sum().reset_index()
        ingredient_details = list(consolidated_df.itertuples(index=False, name=None))

        logging.info(f"Matched recipe for '{crystal_recipe}' with ingredients: {ingredient_details}")
        return crystal_recipe, ingredient_details
    else:
        logging.warning(f"No matched recipe found for '{crystal_recipe}'.")
        return crystal_recipe, []




def find_matching_recipes(crafting_requests, parsed_crafting_data, nft_data, user_preferences, framework_variants, toolkit_variants, player_ingredients):
    nft_df = pd.DataFrame(nft_data)
    matched_recipes = []
    all_initial_ingredients = {}  # Initialize the dictionary to hold all initial ingredients

    # Determine specific variants for Toolkit and Framework if user preference is 'none'
    if user_preferences['framework'] in ['none', 'None'] or user_preferences['toolkit'] in ['none', 'None']:
        framework_variant, toolkit_variant = choose_framework_and_toolkit_variants(player_ingredients)
        user_preferences['framework'] = framework_variant if user_preferences['framework'] in ['none', 'None'] else user_preferences['framework']
        user_preferences['toolkit'] = toolkit_variant if user_preferences['toolkit'] in ['none', 'None'] else user_preferences['toolkit']

    for item_name, request_quantity in crafting_requests:
        item_name_normalized = item_name.strip().title()

        # Map 'Toolkit' and 'Framework' to specific variants
        if item_name_normalized == 'Toolkit':
            item_name_normalized = toolkit_variants.get(user_preferences['toolkit'], item_name_normalized)
        elif item_name_normalized == 'Framework':
            item_name_normalized = framework_variants.get(user_preferences['framework'], item_name_normalized)

        matched_recipe = parsed_crafting_data.get(item_name_normalized)

        if matched_recipe and 'ingredients' in matched_recipe:
            ingredients_df = pd.DataFrame(matched_recipe['ingredients'])
            if not ingredients_df.empty:
                ingredients_df['total_quantity'] = ingredients_df['amount'].astype(int) * request_quantity
                
                merged_df = ingredients_df.merge(nft_df[['mint', 'name']], on='mint', how='left')
                merged_df['name'].fillna('Unknown Ingredient', inplace=True)

                consolidated_df = merged_df.groupby('name')['total_quantity'].sum().reset_index()
                ingredient_details = list(consolidated_df.itertuples(index=False, name=None))

                matched_recipes.append((item_name_normalized, request_quantity, matched_recipe, ingredient_details))
                logging.info(f"Matched recipe for '{item_name_normalized}' with ingredients.")
                
                for name, qty in ingredient_details:
                    all_initial_ingredients[name] = all_initial_ingredients.get(name, 0) + qty
            else:
                logging.warning(f"Recipe found for '{item_name_normalized}' but no ingredients present.")
        else:
            logging.warning(f"No matched recipe found for '{item_name_normalized}'.")

    return matched_recipes, all_initial_ingredients





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


def find_all_ingredients(item, parsed_data, mint_to_name, crystal_recipe, depth=0, max_depth=7, final_product_quantity=0, parent_quantity=1):
    """
    Recursively find all the ingredients required for an item.
    This function returns a tuple: (all_ingredients, raw_ingredients)
    """
    if depth > max_depth:
        return {}, []

    item_key = str(item).strip().title()
    if item_key == 'Crystal Lattice':
        item_key = crystal_recipe

    all_ingredients = {}
    raw_ingredients = []

    if item_key not in parsed_data or 'ingredients' not in parsed_data[item_key]:
        raw_ingredients.append((item_key, parent_quantity))
        return {item_key: parent_quantity}, raw_ingredients

    for ingredient in parsed_data[item_key]['ingredients']:
        ingredient_mint = ingredient['mint']
        ingredient_name = mint_to_name.get(ingredient_mint, "Unknown Ingredient")
        ingredient_quantity = int(ingredient['amount']) * parent_quantity

        # Update all ingredients
        all_ingredients[ingredient_name] = all_ingredients.get(ingredient_name, 0) + ingredient_quantity

        # Recursively find ingredients for the sub-ingredient
        sub_all_ingredients, sub_raw_ingredients = find_all_ingredients(
            ingredient_name, parsed_data, mint_to_name, crystal_recipe, depth + 1, max_depth, parent_quantity=ingredient_quantity
        )

        # Update all ingredients with sub-ingredients
        for name, qty in sub_all_ingredients.items():
            all_ingredients[name] = all_ingredients.get(name, 0) + qty

        # Update raw ingredients list
        raw_ingredients.extend(sub_raw_ingredients)

    # If we are at the initial call, and this item is the final product, subtract the requested quantity
    if depth == 0 and final_product_quantity > 0:
        all_ingredients[item_key] = all_ingredients.get(item_key, 0) + 1 - final_product_quantity

    return all_ingredients, list(set(raw_ingredients))  # Convert to set and back to list to remove duplicates


def post_ingredients_to_sheet(worksheet, matched_recipes, parsed_crafting_data, mint_to_name, crystal_recipe):
    worksheet.clear()
    logging.info("Worksheet cleared of old data.")

    all_initial_ingredients = []
    all_full_ingredients = {}
    all_raw_ingredients = {}

    for item_name, request_quantity, recipe, ingredient_details in matched_recipes:
        if ingredient_details:
            ingredient_df = pd.DataFrame(ingredient_details, columns=['name', 'total_quantity'])
            all_initial_ingredients.append(ingredient_df)

        full_ingredients, raw_ingredients_list = find_all_ingredients(item_name, parsed_crafting_data, mint_to_name, crystal_recipe)

        for raw_name, raw_qty in raw_ingredients_list:
            all_raw_ingredients[raw_name] = all_raw_ingredients.get(raw_name, 0) + raw_qty * request_quantity

        for full_name, full_qty in full_ingredients.items():
            if full_name not in all_raw_ingredients:
                all_full_ingredients[full_name] = all_full_ingredients.get(full_name, 0) + full_qty * request_quantity

    for raw_name, raw_qty in all_raw_ingredients.items():
        if raw_name not in all_full_ingredients:
            all_full_ingredients[raw_name] = raw_qty

    if all_initial_ingredients:
        consolidated_initial_ingredients_df = pd.concat(all_initial_ingredients)
        consolidated_initial_ingredients = consolidated_initial_ingredients_df.groupby('name', as_index=False).sum()
        initial_ingredients_values = [['INGREDIENT', 'AMOUNT']] + consolidated_initial_ingredients.sort_values('name').values.tolist()
        worksheet.update('A1:B' + str(len(initial_ingredients_values)), initial_ingredients_values)
        logging.info("Batch update completed for initial ingredients and quantities.")

    full_ingredients_sorted = sorted(all_full_ingredients.items())
    full_ingredients_values = [['FULL INGREDIENTS', 'AMOUNT']] + [[ingredient, amount] for ingredient, amount in full_ingredients_sorted]
    worksheet.update('G1:H' + str(len(full_ingredients_values)), full_ingredients_values)

    raw_ingredients_sorted = sorted(all_raw_ingredients.items())
    raw_ingredients_values = [['RAW INGREDIENT', 'AMOUNT']] + [[ingredient, amount] for ingredient, amount in raw_ingredients_sorted]
    worksheet.update('D1:E' + str(len(raw_ingredients_values)), raw_ingredients_values)

    logging.info("Updated worksheet with initial, full, and raw ingredients.")
    return all_full_ingredients
    

def calculate_needed_ingredients(player_ingredients, crafting_requests, parsed_crafting_data, mint_to_name, all_full_ingredients):
    logging.info(f"Inside function - Crafting requests: {crafting_requests}")
    all_recipes_needed_ingredients = {}

    def decompose(item_name, quantity_needed, player_ingredients, temp_needed_ingredients):
        logging.info(f"Decomposing {quantity_needed} of {item_name}")
        if item_name in parsed_crafting_data and 'ingredients' in parsed_crafting_data[item_name]:
            for ingredient_dict in parsed_crafting_data[item_name]['ingredients']:
                component_name = mint_to_name.get(ingredient_dict['mint'], "Unknown Ingredient")
                component_qty = int(ingredient_dict['amount'])
                total_component_needed = component_qty * quantity_needed
                player_component_qty = player_ingredients.get(component_name, 0)
                remaining_qty = max(total_component_needed - player_component_qty, 0)

                logging.info(f"Component {component_name}: Need {total_component_needed}, Player has {player_component_qty}, Remaining {remaining_qty}")

                if remaining_qty > 0:
                    temp_needed_ingredients[component_name] = temp_needed_ingredients.get(component_name, 0) + remaining_qty
                    decompose(component_name, remaining_qty, player_ingredients, temp_needed_ingredients)

    for item_name, quantity_needed in crafting_requests.items():
        temp_needed_ingredients = {}
        player_qty = player_ingredients.get(item_name, 0)
        needed_qty = max(quantity_needed - player_qty, 0)

        if needed_qty > 0:
            temp_needed_ingredients[item_name] = needed_qty
            decompose(item_name, needed_qty, player_ingredients.copy(), temp_needed_ingredients)

        all_recipes_needed_ingredients[item_name] = temp_needed_ingredients

    # Consolidating needed ingredients across all recipes
    consolidated_needed_ingredients = {}
    for recipe_needed_ingredients in all_recipes_needed_ingredients.values():
        for ingredient, qty in recipe_needed_ingredients.items():
            consolidated_needed_ingredients[ingredient] = consolidated_needed_ingredients.get(ingredient, 0) + qty

    # Add missing ingredients with amount 0
    for ingredient in all_full_ingredients:
        if ingredient not in consolidated_needed_ingredients:
            consolidated_needed_ingredients[ingredient] = 0

    return consolidated_needed_ingredients



def post_needed_ingredients_to_sheet(worksheet, needed_ingredients, mint_to_name, name_to_mint):
    # Prepare the data for the needed ingredients list
    needed_ingredients_values = [['NEEDED INGREDIENTS', 'AMOUNT']]
    
    # Sort the ingredients alphabetically by name before adding to the list
    for ingredient_name in sorted(needed_ingredients.keys()):
        amount = needed_ingredients[ingredient_name]
        mint_address = name_to_mint.get(ingredient_name, "Unknown Ingredient: " + ingredient_name)
        resolved_name = mint_to_name.get(mint_address, "Unknown Ingredient: " + mint_address)
        needed_ingredients_values.append([resolved_name, amount])

    # Update the worksheet with needed ingredients in columns J and K
    worksheet.update('J1:K' + str(len(needed_ingredients_values)), needed_ingredients_values)


def main():
    # Load data from JSON files
    crafting_data, nft_data = load_data()

    # Parse the crafting data
    parsed_crafting_data = parse_crafting_data(crafting_data, nft_data)
    logging.info("Crafting data parsed successfully")

    # Create the mint_to_name dictionary
    mint_to_name = {nft['mint']: nft['name'] for nft in nft_data}
    name_to_mint = {name: mint for mint, name in mint_to_name.items()}

    # Initialize the Google Sheets client
    client = auth_gspread()
    logging.info("Authenticated with Google Sheets successfully")

    # Fetch user preferences for Framework and Toolkit
    user_preferences = fetch_user_preferences(client, PLAYER_PROFILE_SHEET, FRAMEWORK_LOOKUP_KEY, TOOLKIT_LOOKUP_KEY)

    # Fetch player profile and account data from Google Sheets
    player_profile_worksheet = get_worksheet(client, PLAYER_PROFILE_SHEET)
    account_data_worksheet = get_worksheet(client, ACCOUNT_DATA_FETCH_SHEET)
    
    if player_profile_worksheet is None or account_data_worksheet is None:
        logging.error("Error accessing worksheets")
        return

    # Find player's crystal choice and faction
    player_crystal_choice = find_player_crystal_choice(client)
    player_faction = find_player_faction(client)
    player_ingredients = get_player_ingredient_quantities(client)
    logging.info(f"Player's crystal choice: {player_crystal_choice}")

    # Update user preferences for Framework and Toolkit based on inventory if 'none'
    if user_preferences['framework'] == 'none' or user_preferences['toolkit'] == 'none':
        framework_variant, toolkit_variant = choose_framework_and_toolkit_variants(player_ingredients)
        user_preferences['framework'] = framework_variant if user_preferences['framework'] == 'none' else user_preferences['framework']
        user_preferences['toolkit'] = toolkit_variant if user_preferences['toolkit'] == 'none' else user_preferences['toolkit']

    chosen_crystal_recipe, crystal_ingredients = None, []
    if player_crystal_choice and player_crystal_choice.title() in crystal_lattice_variants:
        chosen_crystal_recipe = crystal_lattice_variants[player_crystal_choice.title()]
    else:
        chosen_crystal_recipe, crystal_ingredients = choose_crystal_lattice_variant(player_faction, player_ingredients, parsed_crafting_data, nft_data)
    logging.info(f"Chosen Crystal Lattice Recipe: {chosen_crystal_recipe} with ingredients: {crystal_ingredients}")

    # Fetch crafting requests data
    crafting_requests_worksheet = get_worksheet(client, CRAFTING_DATA_FETCH_SHEET)
    if crafting_requests_worksheet is not None:
        crafting_requests_data = fetch_data_with_caching(client, CRAFTING_DATA_FETCH_SHEET, CRAFTING_DATA_FETCH_RANGE, ttl=CACHE_EXPIRY)
        crafting_requests = [(row[0], int(row[1].replace(',', ''))) for row in crafting_requests_data if len(row) >= 2]
        logging.info(f"Crafting requests fetched: {crafting_requests}")

        # Find matched recipes and all initial ingredients
        matched_recipes, all_initial_ingredients_dict = find_matching_recipes(crafting_requests, parsed_crafting_data, nft_data, user_preferences, framework_variants, toolkit_variants, player_ingredients)

        logging.info(f"Found {len(matched_recipes)} matched recipes.")

        # Get the results worksheet
        results_worksheet = get_worksheet(client, CRAFTING_RESULTS_SHEET)
        if results_worksheet is not None:
            # Post initial ingredients, full ingredient list, and raw ingredients to the sheet
            all_full_ingredients = post_ingredients_to_sheet(results_worksheet, matched_recipes, parsed_crafting_data, mint_to_name, chosen_crystal_recipe)
            logging.info("Ingredients with quantities posted successfully")

            if all_full_ingredients is not None:
                # Calculate needed ingredients
                # Just before calling calculate_needed_ingredients
                logging.info(f"Inspecting crafting requests structure: {crafting_requests}")
                needed_ingredients = calculate_needed_ingredients(player_ingredients, all_initial_ingredients_dict, parsed_crafting_data, mint_to_name, all_full_ingredients)
                logging.info("Calculated needed ingredients")

                # Post needed ingredients to the sheet
                post_needed_ingredients_to_sheet(results_worksheet, needed_ingredients, mint_to_name, name_to_mint)
                logging.info("Needed ingredients with quantities posted successfully")
            else:
                logging.error("Error: all_full_ingredients is None")

if __name__ == "__main__":
    main()