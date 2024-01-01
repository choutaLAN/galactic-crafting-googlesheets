// Import the dotenv package at the top
import dotenv from 'dotenv';
dotenv.config({ path: './.env' });

import fs from 'fs';
import BN from 'bn.js';

// Function to read and parse the JSON file
function readJsonFile(filePath: string) {
    const rawData = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(rawData);
}

function convertFeeAmount(rawFee: string) {
    const unitsInATLAS = new BN('100000000'); // 1 ATLAS = 100,000,000 units (8 decimal places)
    const feeInRawUnits = new BN(rawFee, 16); // Convert hexadecimal fee to raw units (BN)

    // Scale up the feeInRawUnits to preserve decimals after division
    const scaledFee = feeInRawUnits.mul(new BN('100000000'));
    const feeInATLAS = scaledFee.div(unitsInATLAS);

    // Format the result to include decimal places
    let formattedFee = feeInATLAS.toString(10);
    while (formattedFee.length < 9) { // Ensure string is long enough for decimal placement
        formattedFee = '0' + formattedFee;
    }
    const decimalIndex = formattedFee.length - 8;
    const feeString = formattedFee.slice(0, decimalIndex) + "." + formattedFee.slice(decimalIndex);

    return feeString; // Return the formatted fee amount with decimals
}

// Function to make sure quantities are correctly interpreted as decimal numbers.
// Modified function to convert hexadecimal to string
function convertHexToString(hexString: string): string {
    const value = new BN(hexString, 16).toString(10);
    return value;
}

// Function to convert ASCII codes to a string, excluding null characters
function asciiArrayToString(asciiArray: number[]) {
    return asciiArray
        .filter(code => code !== 0) // Filter out null ASCII codes
        .map(code => String.fromCharCode(code))
        .join('');
}

// Function to convert the status code to a readable string
function getStatusString(statusCode: number) {
    switch (statusCode) {
        case 2: return "ACTIVE";
        case 3: return "INACTIVE";
        default: return "UNKNOWN"; // Default case for unexpected values
    }
}

// Main function area to reformat the recipe data
interface IngredientIO {
    amount: string; // Or any other type that represents the amount
    mint: string;
  }
// Modified reformatRecipes function with additional console logs for Category
function reformatRecipes(recipes: any[]): any[] {
    // Filter only active recipes
    const activeRecipes = recipes.filter(recipe => recipe._data.status === 2);
    // Log the number of active recipes
    console.log("Number of active recipes:", activeRecipes.length);
    return activeRecipes.map(recipe => {
        const ingredients = recipe._ingredientInputsOutputs.map((ingredient: IngredientIO) => {
            const convertedAmount = convertHexToString(ingredient.amount);
            return {
                amount: convertedAmount,
                mint: ingredient.mint
            };
        });

        const output = ingredients.pop(); // Remove and retrieve the last ingredient

        return {
            key: recipe._key,
            data: {
                version: convertHexToString(recipe._data.version),
                category: recipe._data.category, // Directly assign the string value
                duration: convertHexToString(recipe._data.duration),
                namespace: Array.isArray(recipe._data.namespace) ? asciiArrayToString(recipe._data.namespace) : undefined,
                status: getStatusString(recipe._data.status),
                feeAmount: convertFeeAmount(recipe._data.feeAmount)
            },
            ingredients: ingredients,
            output: output ? {
                amount: output.amount,
                mint: output.mint
            } : undefined
        };
    });
}

// Function to write the reformatted data to a new JSON file
function writeJsonFile(filePath: string, data: any) {
    const jsonData = JSON.stringify(data, null, 2);
    fs.writeFileSync(filePath, jsonData, 'utf8');
}

// Main function to orchestrate the process
async function main() {
    const filePath= process.env.CRAFTING_DATA_RAW
    const fileName= process.env.CRAFTING_DATA_FORMAT //the name is specified by the path set in the enviroment file. If it cannot find a file named this already, it creates a new one with this name.
    if (!filePath) {
      console.error('The file path to point the app to where the formatted crafting data is has not been set... You dang fool!');
      return;
    }
    if (!fileName) {
        console.error('The .json file name has not been set... You dang fool!');
        return;
    }
    const recipes = readJsonFile(filePath);
    const formattedRecipes = reformatRecipes(recipes);
    writeJsonFile(fileName, formattedRecipes);
    console.log('Formatted recipes saved successfully.');
}

main();


