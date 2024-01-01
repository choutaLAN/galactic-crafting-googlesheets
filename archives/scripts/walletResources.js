function updateResourcesFromWallet() {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var collectionOpsSheet = ss.getSheetByName('Collection Ops');
    var playerProflieSheet = ss.getSheetByName('Player Profile');
    var metadataSheet = ss.getSheetByName('StarAtlasMetadata');
    var walletAddress = collectionOpsSheet.getRange('B3').getValue();

    Logger.log("Wallet Address: " + walletAddress);

    var url = 'https://api.mainnet-beta.solana.com/';
    var payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [walletAddress, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}]
    };
    var options = {'method' : 'post', 'headers': {'Content-Type': 'application/json'}, 'payload' : JSON.stringify(payload)};
    var response = UrlFetchApp.fetch(url, options);
    var data = JSON.parse(response.getContentText());

    Logger.log(JSON.stringify(data));

    if (data && data.result && data.result.value) {
        var tokenAccounts = data.result.value;

        // Retrieve Star Atlas metadata
        var lastRowMetadata = metadataSheet.getLastRow();
        var starAtlasData = metadataSheet.getRange(2, 1, lastRowMetadata - 1, 2).getValues();
        var starAtlasMap = new Map(starAtlasData);

        // Clear existing data in Collection Ops from row 4 downwards
        clearSheetContent(collectionOpsSheet);

        var tokenData = [];
        for (var i = 0; i < tokenAccounts.length; i++) {
            var mintAddress = tokenAccounts[i].account.data.parsed.info.mint;
            var amount = tokenAccounts[i].account.data.parsed.info.tokenAmount.uiAmountString;

            if (starAtlasMap.has(mintAddress)) {
                var resourceName = starAtlasMap.get(mintAddress);
                tokenData.push([resourceName, amount]);
            }
        }

        // Update Collection Ops sheet
        if (tokenData.length > 0) {
            collectionOpsSheet.getRange(4, 2, tokenData.length, 2).setValues(tokenData);
        }
    } else {
        Logger.log("No token accounts found for the provided wallet address.");
    }
}

function clearSheetContent(sheet) {
    var lastRow = sheet.getLastRow();
    if (lastRow >= 4) {
        sheet.getRange('B4:C' + lastRow).clearContent();
    }
}
