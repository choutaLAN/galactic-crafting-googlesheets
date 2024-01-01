// Import the dotenv package at the top
import dotenv from 'dotenv';
dotenv.config({ path: './.env' });

import { sheets_v4 } from 'googleapis';
import { authenticateGoogleSheets } from './googleSheetsAuth.js';
import fs from 'fs';

interface Ingredient {
  amount: string;
  mint: string;
}

interface CraftingData {
  key: string;
  data: {
    version: number;
    category: string;
    duration: string;
    namespace: string;
    status: string;
    feeAmount: string;
  };
  ingredients: Ingredient[];
}

// Function to read JSON data and upload to Google Sheets
async function uploadCraftingDataToSheet(sheets: sheets_v4.Sheets, spreadsheetId: string, range: string, valueInputOption: string): Promise<void> {
  try {
    const craftingDataPath = process.env.CRAFTING_DATA_FORMAT;
    if (!craftingDataPath) {
      console.error('The file path for the formatted crafting data is not set.');
      return;
    }

    const craftingData: CraftingData[] = JSON.parse(fs.readFileSync(craftingDataPath, 'utf-8'));

    let values: string[][] = [
      ["Recipe Key", "Ingredient Mint Address", "Quantity", "Output Mint Address", "Output", "Status", "Duration", "Fee Amount", "Version Number", "Category"] // Add Namespace to header row
    ]; 

    craftingData.forEach(item => {
      item.ingredients.forEach((ing, index) => {
        let row: string[] = [item.key, ing.mint, ing.amount];

        if (index === item.ingredients.length - 1) {
          row.push(
            item.ingredients[item.ingredients.length - 1].mint, 
            item.data.namespace,
            item.data.status,
            item.data.duration,
            item.data.feeAmount,
            item.data.version.toString(),
            item.data.category
          );
        } else {
          row.push('', '', '', '', '', '', ''); // Fill other rows with empty strings
        }

        values.push(row);
      });
    });

    await sheets.spreadsheets.values.update({
      spreadsheetId,
      range,
      valueInputOption,
      requestBody: { values }
    });

    console.log("Data upload response: Success");
  } catch (error) {
    console.error("Error in uploading data to Google Sheets:", error);
  }
}


// Main function to execute the process
(async () => {
  console.log('Starting the process...');
  try {
    // Authenticate with Google Sheets
    const sheets = await authenticateGoogleSheets();
    console.log("Google Sheets Authentication Successful.");

    // Verify and use environment variables
    const spreadsheetId = process.env.SPREADSHEET_ID;
    const range = process.env.SHEET_RANGE;
    const valueInputOption = process.env.VALUE_INPUT_OPTION;
    if (!spreadsheetId || !range || !valueInputOption) {
      throw new Error("One or more required environment variables (SPREADSHEET_ID, SHEET_RANGE, VALUE_INPUT_OPTION) are not set.");
    }

    console.log('Uploading data to Google Sheets...');
    await uploadCraftingDataToSheet(sheets, spreadsheetId, range, valueInputOption);
    console.log("Data successfully uploaded to Google Sheets.");
  } catch (error) {
    console.error("Error during processing:", error);
  }

  console.log("Process completed.");
})();