function calculateRemainingResources() {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    
    // 1. Fetching Data
    var dedOperationsSheet = ss.getSheetByName('DED. OPERATIONS');
    var recipeMatrixSheet = ss.getSheetByName('recipe matrix');
    
    var required = {};
    var collected = {};
    var graph = {};
    var remaining = {};
    var originalRemaining = {};

    // Fetch required resources
    var requiredResourcesData = dedOperationsSheet.getRange('D5:E' + dedOperationsSheet.getLastRow()).getValues();
    requiredResourcesData.forEach(function(row) {
        if(row[0]) {  // Add this condition to exclude empty keys
            required[row[0]] = row[1];
        }
    });
    Logger.log("Required Resources: " + JSON.stringify(required));

    // Fetch collected resources
    var collectedResourcesData = dedOperationsSheet.getRange('I5:K' + dedOperationsSheet.getLastRow()).getValues();
    collectedResourcesData.forEach(function(row) {
        if(row[0]) {  // Add this condition to exclude empty keys
            collected[row[0]] = row[2];
        }
    });
    Logger.log("Collected Resources: " + JSON.stringify(collected));  

    // Fetch crafting recipes and build the graph
    var matrixData = recipeMatrixSheet.getDataRange().getValues();
    var headers = matrixData[0];
    matrixData.slice(1).forEach(function(row) {
        var item = row[0];
        var ingredients = {};
        row.slice(1).forEach(function(quantity, index) {
            if (quantity > 0) {
                ingredients[headers[index + 1]] = quantity;
            }
        });
        graph[item] = ingredients;
    });

    // Calculate initial remaining based on requirement - collected
    for (var item in graph) { // Initialize with all items in graph
        remaining[item] = 0;
        originalRemaining[item] = 0;
    }
    for (var item in required) {
        remaining[item] = (required[item] || 0) - (collected[item] || 0);
        originalRemaining[item] = (required[item] || 0) - (collected[item] || 0);
    }

    function decompose(item, quantity) {
        if (graph[item]) {
            for (var ingredient in graph[item]) {
                var needed = graph[item][ingredient] * quantity;

                // Deduct from collected first
                if (collected[ingredient] && collected[ingredient] > 0) {
                    var fromCollected = Math.min(needed, collected[ingredient]);
                    collected[ingredient] -= fromCollected;
                    needed -= fromCollected;
                }

                // If there's still some left after taking from collected, add to remaining
                if (needed > 0) {
                    remaining[ingredient] = (remaining[ingredient] || 0) + needed;
                    decompose(ingredient, needed);
                }
            }
        }
    }

    // Decompose missing items
    for (var item in remaining) {
        if (remaining[item] > 0) {
            decompose(item, remaining[item]);
        }
    }

    // Subtract the decomposed values from the original requirements
    for (var item in originalRemaining) {
        originalRemaining[item] -= (remaining[item] || 0);
    }

    Logger.log("After crafting: " + JSON.stringify(remaining));

    // 3. Filtering and Sorting the Output Data
    var outputData = Object.keys(collected)
        .sort()
        .map(item => [item, remaining[item] || 0]);

    Logger.log("Filtered Results: " + JSON.stringify(outputData));

    // 4. Outputting to the Spreadsheet
    var dedScriptSheet = ss.getSheetByName('DED. script');

    // Create combined data array with headers and then outputData
    var combinedData = [['RESOURCE REMAINDER', 'REMAINING']].concat(outputData);

    // Clear the entire possible range where old data might exist before writing new data
    var lastRow = dedScriptSheet.getLastRow();
    var dataRange = 'G2:H' + lastRow;
    if (lastRow > 1) { // Check if there are more than just header rows
        dedScriptSheet.getRange(dataRange).clearContent();
    }

    // Write combined data to the worksheet in one operation
    dedScriptSheet.getRange('G2').offset(0, 0, combinedData.length, 2).setValues(combinedData);

}
