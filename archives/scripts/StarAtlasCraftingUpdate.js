function updateCraftingRecipes() {
    var url = 'https://api.staratlas.com/crafting/recipes';

    var response = UrlFetchApp.fetch(url);
    var data = JSON.parse(response.getContentText());

    // Get the 'StarAtlasCrafting' sheet
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var craftingSheet = ss.getSheetByName('StarAtlasCrafting');

    // Clear the existing data
    craftingSheet.getRange('A2:Z' + craftingSheet.getLastRow()).clearContent();

    // Write the new data
    for (var i = 0; i < data.length; i++) {
        craftingSheet.getRange('A' + (i + 2)).setValue(data[i].id);
        craftingSheet.getRange('B' + (i + 2)).setValue(data[i].name);
        // Add more columns as needed based on the data structure
    }
}