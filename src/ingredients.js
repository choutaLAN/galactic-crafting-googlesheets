function findDeepIngredients() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // Fetch all necessary data from the spreadsheet at once
  var dedOperationsData = ss.getSheetByName('DED. OPERATIONS').getRange('A5:B50').getValues();
  var recipeMatrixData = ss.getSheetByName('recipe matrix').getDataRange().getValues();
  
  // Convert the recipe matrix into a dictionary for faster lookups
  var recipeDict = {};
  for (var i = 1; i < recipeMatrixData.length; i++) {
    var item = recipeMatrixData[i][0];
    recipeDict[item] = recipeMatrixData[i].slice(1);
  }
  
  // Convert the items to craft into a dictionary
  var itemsToCraftDict = {};
  dedOperationsData.forEach(function(row) {
    if (row[0] && row[1]) {
      itemsToCraftDict[row[0]] = row[1];
    }
  });
  
  // Recursive function to get ingredients for an item
  function getIngredientsForItem(item, quantity, depth = 0) {
    if (depth > 7) return [];
    
    var ingredients = recipeMatrixData[0].slice(1);
    var quantities = recipeDict[item] || [];
    
    var ingredientList = [];
    for (var j = 0; j < ingredients.length; j++) {
      if (quantities[j]) {
        var subIngredients = getIngredientsForItem(ingredients[j], quantities[j] * quantity, depth + 1);
        ingredientList = ingredientList.concat(subIngredients);
        ingredientList.push({name: ingredients[j], quantity: quantities[j] * quantity});
      }
    }
    return ingredientList;
  }
  
  // Get all ingredients for all items to craft
  var allIngredients = [];
  Object.keys(itemsToCraftDict).forEach(function(item) {
    var ingredients = getIngredientsForItem(item, itemsToCraftDict[item]);
    allIngredients = allIngredients.concat(ingredients);
  });
  
  // Combine quantities for duplicate ingredients
  var combinedIngredients = {};
  allIngredients.forEach(function(ingredient) {
    if (!combinedIngredients[ingredient.name]) {
      combinedIngredients[ingredient.name] = 0;
    }
    combinedIngredients[ingredient.name] += ingredient.quantity;
  });
  
  // Convert the combined ingredients dictionary back to an array and sort it
  var combinedIngredientsArray = [];
  Object.keys(combinedIngredients).forEach(function(ingredient) {
    combinedIngredientsArray.push([ingredient, combinedIngredients[ingredient]]);
  });
  combinedIngredientsArray.sort(function(a, b) {
    return a[0].localeCompare(b[0]);
  });
  
  // Convert the combined ingredients dictionary back to an array and sort it
  var combinedIngredientsArray = [];
  Object.keys(combinedIngredients).forEach(function(ingredient) {
    combinedIngredientsArray.push([ingredient, combinedIngredients[ingredient]]);
  });
  combinedIngredientsArray.sort(function(a, b) {
    return a[0].localeCompare(b[0]);
  });
  
  // Write the combined ingredients to the 'DED. script' sheet
  var dedScriptSheet = ss.getSheetByName('DED. script');
  
  // Output the headers to the 'DED. script' sheet
  dedScriptSheet.getRange('A2').setValue('FULL RESOURCE'); // Set header in column A
  dedScriptSheet.getRange('B2').setValue('REQUIRED'); // Set header in column B
  
  // Overwrite old data with new data
  var lastRowWithData = 2 + combinedIngredientsArray.length;
  dedScriptSheet.getRange('A3:B' + lastRowWithData).setValues(combinedIngredientsArray); // Output data to columns A and B
  
  // Clear any remaining old data below the new data
  var lastRowInSheet = dedScriptSheet.getLastRow();
  if (lastRowWithData < lastRowInSheet) {
    dedScriptSheet.getRange('A' + (lastRowWithData + 1) + ':B' + lastRowInSheet).clearContent(); // Clear data below the new data in columns A and B
  }
}
