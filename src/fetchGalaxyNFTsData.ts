// Import the dotenv package at the top
import dotenv from 'dotenv';
dotenv.config({ path: './.env' });

import fs from 'fs';
import fetch from 'node-fetch';

// Asynchronous function to fetch NFT data from API and save to a JSON file
async function fetchNftData() {
  const url = 'https://galaxy.staratlas.com/nfts';
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const jsonData = await response.json();

    // Writing the JSON data to a file
    const fileName= process.env.GALAXY_NFTS_DATA
    if (!fileName) {
      console.error('The file name has not been set in the environment file... You dang fool!');
      return;
    }
    fs.writeFileSync(fileName, JSON.stringify(jsonData, null, 2));
    console.log('Data saved!');
  } catch (error) {
    console.error('Error fetching or saving NFT data:', error);
  }
}

// Executing the function
fetchNftData();
