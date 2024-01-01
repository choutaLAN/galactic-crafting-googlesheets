// Import the dotenv package at the top
import dotenv from 'dotenv';
dotenv.config({ path: './.env' });

import { google, sheets_v4 } from 'googleapis';
import { JWT } from 'google-auth-library';
import fs from 'fs';

interface ServiceAccount {
  type: string;
  project_id: string;
  private_key_id: string;
  private_key: string;
  client_email: string;
  client_id: string;
  auth_uri: string;
  token_uri: string;
  auth_provider_x509_cert_url: string;
  client_x509_cert_url: string;
}

export async function authenticateGoogleSheets(): Promise<sheets_v4.Sheets> {
  const serviceAccountEmail = process.env.SERVICE_ACCOUNT_EMAIL;
  const privateKeyPath = process.env.GOOGLE_CREDENTIALS_FILE;

  if (!serviceAccountEmail || !privateKeyPath) {
    throw new Error('Environment variables SERVICE_ACCOUNT_EMAIL and PRIVATE_KEY_PATH must be set.');
  }

  // Read the JSON file containing the service account credentials
  const credentialsJson = fs.readFileSync(privateKeyPath, 'utf8');
  const credentials: ServiceAccount = JSON.parse(credentialsJson);

  const jwtClient = new JWT({
    email: credentials.client_email,
    key: credentials.private_key,
    scopes: ['https://www.googleapis.com/auth/spreadsheets'],
  });

  return google.sheets({ version: 'v4', auth: jwtClient });
}
