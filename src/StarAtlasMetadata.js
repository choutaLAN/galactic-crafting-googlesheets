function fetchStarAtlasMetadata() {
    var metadataUrl = 'https://galaxy.staratlas.com/nfts';
    var response = UrlFetchApp.fetch(metadataUrl);
    var metadataList = JSON.parse(response.getContentText());
    
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var metadataSheet = ss.getSheetByName('StarAtlasMetadata');
    
    metadataSheet.clearContents();

    // Updated headers to include attributes
    var headers = ['Mint Address', 'Name', 'Collection Name', 'Collection Family', 'Item Type', 'Class', 'Tier', 'Spec', 'Rarity', 'Category', 'Make', 'Model', 'Unit Length', 'Unit Width', 'Unit Height'];
    metadataSheet.appendRow(headers);

    var metadata = [];
    for (var i = 0; i < metadataList.length; i++) {
        var nft = metadataList[i];

        var collectionName = nft.collection && nft.collection.name ? nft.collection.name : 'N/A';
        var collectionFamily = nft.collection && nft.collection.family ? nft.collection.family : 'N/A';

        // Extracting attributes
        var attributes = nft.attributes || {};
        metadata.push([
            nft.mint,
            nft.name,
            collectionName,
            collectionFamily,
            attributes.itemType || 'N/A',
            attributes.class || 'N/A',
            attributes.tier || 'N/A',
            attributes.spec || 'N/A',
            attributes.rarity || 'N/A',
            attributes.category || 'N/A',
            attributes.make || 'N/A',
            attributes.model || 'N/A',
            attributes.unitLength || 'N/A',
            attributes.unitWidth || 'N/A',
            attributes.unitHeight || 'N/A'
        ]);
    }

    metadataSheet.getRange(2, 1, metadata.length, headers.length).setValues(metadata);
}
