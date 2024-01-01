function onEdit(e) {
  // Get the active spreadsheet and sheet
  var ss = e.source;
  var sheet = ss.getActiveSheet();
  
  // Check if the edited sheet is 'DED. OPERATIONS'
  if (sheet.getName() === 'DED. OPERATIONS') {
    // Get the range that was edited
    var editedRange = e.range;
    
    // Check if the edited range intersects with A5:B50
    if (editedRange.getRow() >= 5 && editedRange.getRow() <= 50 && editedRange.getColumn() <= 2) {
      // Run the scripts
      findDirectIngredientsOnly();
    }
  }
}

function findDirectIngredientsOnly() {
  // Access the spreadsheet
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // Access the 'DED. OPERATIONS' sheet and get the items to craft and their quantities
  var dedOperationsSheet = ss.getSheetByName('DED. OPERATIONS');
  var itemsToCraft = dedOperationsSheet.getRange('A5:A50').getValues().flat();
  var quantitiesToCraft = dedOperationsSheet.getRange('B5:B50').getValues().flat();
  
  // Access the 'recipe matrix' sheet
  var recipeMatrixSheet = ss.getSheetByName('recipe matrix');
  
  // Function to get direct ingredients for a given item
  function getDirectIngredientsForItem(item, quantity) {
    var rowIndex = -1;
    var items = recipeMatrixSheet.getRange('A:A').getValues();
    for (var i = 0; i < items.length; i++) {
      if (items[i][0] === item) {
        rowIndex = i;
        break;
      }
    }
    if (rowIndex === -1) return [];
    
    var ingredients = recipeMatrixSheet.getRange(1, 2, 1, recipeMatrixSheet.getLastColumn()).getValues()[0];
    var quantities = recipeMatrixSheet.getRange(rowIndex + 1, 2, 1, recipeMatrixSheet.getLastColumn()).getValues()[0];
    
    var ingredientList = [];
    for (var j = 0; j < ingredients.length; j++) {
      if (quantities[j]) {
        ingredientList.push({name: ingredients[j], quantity: quantities[j] * quantity});
      }
    }
    return ingredientList;
  }
  
  // Initialize combined ingredients list
  var combinedIngredients = [];
  
  // Iterate over each item and its quantity
  for (var k = 0; k < itemsToCraft.length; k++) {
    if (itemsToCraft[k] && quantitiesToCraft[k]) {
      var directIngredients = getDirectIngredientsForItem(itemsToCraft[k], quantitiesToCraft[k]);
      
      // Combine quantities for duplicate ingredients
      directIngredients.forEach(function(ingredient) {
        var found = false;
        for (var i = 0; i < combinedIngredients.length; i++) {
          if (combinedIngredients[i].name === ingredient.name) {
            combinedIngredients[i].quantity += ingredient.quantity;
            found = true;
            break;
          }
        }
        if (!found) {
          combinedIngredients.push(ingredient);
        }
      });
    }
  }
  
  // Sort the ingredients alphabetically
  combinedIngredients.sort(function(a, b) {
    return a.name.localeCompare(b.name);
  });
  
   // Prepare the output data
  var outputData = combinedIngredients.map(function(ingredient) {
    return [ingredient.name, ingredient.quantity];
  });
  
  // Access the 'DED. script' sheet
  var dedScriptSheet = ss.getSheetByName('DED. script');
  
  // Overwrite old data with new data for direct ingredients
  dedScriptSheet.getRange(3, 4, outputData.length, 2).setValues(outputData); // Changed from 7 to 4
  // Clear any remaining old data below the new data for direct ingredients
  var lastRow = dedScriptSheet.getLastRow();
  if (lastRow > outputData.length + 2) {
    dedScriptSheet.getRange(outputData.length + 3, 4, lastRow - outputData.length - 2, 2).clearContent(); // Changed from 7 to 4
  }
  
  // Set titles for the table
  dedScriptSheet.getRange('D2').setValue('RECIPE RESOURCE'); 
  dedScriptSheet.getRange('E2').setValue('REQUIRED'); //
}

