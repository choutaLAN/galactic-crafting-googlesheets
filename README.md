# StarAtlasApp
A Star Atlas App with a Google Sheets interface and integration.

Greetings! I am a noobie dev. I would appreciate any advice and help! Feel free to DM me or reach out here on GitHub https://x.com/choutaLAN.

The script calculates recipes for user-set crafting items, checks players' profiles for star atlas assets via wallet address and tells you how much more of each item you need considering the cascading effect of having higher tier items reducing lower tier item needs.
Crafting recipes are updated directly from what Star Atlas has published to the blockchain, meaning the latest costs are used.
I've added some basic logic to deal with player preferences for Crystal Lattice, Framework and Toolkit recipes. You can specify a preference in the PROFILE tab; otherwise, leave the preference set to 'none' to apply logic based on what is currently in your gaming account inventory or faction alignment.

User will need to make a copy of this Google sheet: https://docs.google.com/spreadsheets/d/1ReahH_DFlaJUnz4v3CczyqwR_IQklEZ-7oeyl6n6bIM/edit?usp=sharing

The script will need to be run via a local environment using the terminal at this stage. Run the Typescript build commands listed in the package.json to construct the JSON data files containing the blockchain recipes and Star Atlas Galaxy NFT APT information (including the formatted data json file). 

Don't forget to install node js dependencies.
requirement.txt file contains the needed dependencies for Python, in which the main "updateProfile.py" and updateGoogleSheet.py" files are written.

Lastly, you will need to create and set a .env environment file.

Here is the outline you will need to use for the current code to work with the above-shared Google sheet.

```
# Google Credentials
GOOGLE_CREDENTIALS_FILE=C:\Users\[USERNAME]\[ANY FOLDER PATH YOU WANT]\[FILE NAME FROM GOOGLE].json
SERVICE_ACCOUNT_EMAIL=[CREATE YOUR OWN USER SERVICE EMAIL VIA GOOGLE- ASK CHATGPT WHAT THIS IS IF YOU DON'T KNOW!]

# Spreadsheet Configuration
SPREADSHEET_ID=[ADD YOUR SPREADSHEETS ID]
VALUE_INPUT_OPTION=USER_ENTERED  # Options: USER_ENTERED, or RAW. 
# This tells the API how to interpret the values in the spreadsheet. 
# For example, using USER_ENTERED will let the API know to parse the values as if the user typed them into the sheet by a human and apply formatting appropriately.
# RAW tells the API to not parse the values and add them in as is.
CRAFTING_DATA_SHEET_RANGE=StarAtlasCrafting!A1

CRAFTING_RESULTS_SHEET=RecipeCalcs
CRAFTING_RESULTS_RANGE=A1

CRAFTING_DATA_FETCH_SHEET=DASHBOARD
CRAFTING_DATA_FETCH_RANGE=A5:B50

CRAFTING_RECIPE_FETCH_SHEET=StarAtlasCrafting
CRAFTING_RECIPE_FETCH_RANGE=A2:J

ACCOUNT_DATA_FETCH_SHEET=ACCOUNT_RESOURCES
ACCOUNT_DATA_FETCH_RANGE=A4:B

PLAYER_PROFILE_SHEET=PROFILE
PLAYER_PROFILE_RANGE=A2:B

COLLECTED_DATA_FETCH_SHEET=DASHBOARD
COLLECTED_DATA_FETCH_RANGE=A5:B50

# Crafting Defaults and profile lookups.
WALLET_LOOKUP_KEY=B3
FACTION_LOOKUP_KEY=Faction
CRYSTAL_LOOKUP_KEY=Crystal Default
FRAMEWORK_LOOKUP_KEY=Framework Default
TOOLKIT_LOOKUP_KEY=Toolkit Default

# Node RPC Host
NODE_RPC_HOST=https://solana-api.syndica.io/access-token/WPoEqWQ2auQQY1zHRNGJyRBkvfOLqw58FqYucdYtmy8q9Z84MBWwqtfVf8jKhcFh/rpc #You can add your own RPC Host here. This one has been working well for me. It was passed on by Granite Warlock from the CLUB.

# Data Directory
CRAFTING_DATA_RAW='../data/craftingDataRaw.json'
CRAFTING_DATA_FORMAT='../data/craftingDataFormat.json'
GALAXY_NFTS_DATA='../data/galaxyNFTsData.json'

# Star Atlas
CRAFTING_PROGRAM_PUBLIC_KEY=Craftf1EGzEoPFJ1rpaTSQG1F6hhRRBAf4gRo9hdSZjR

# CACHING
CACHE_EXPIRY = 3600  # 1 hour
CACHE_EXPIRY_PERMANENT = 86400 # Default cache expiry is 1 day
```
