// Import the dotenv package at the top
import dotenv from 'dotenv';
dotenv.config({ path: './.env' });

import fs from 'fs';
import { Connection, Keypair, PublicKey } from '@solana/web3.js';
import { Recipe, CRAFTING_IDL } from '@staratlas/crafting';
import { DecodedAccountData, readAllFromRPC } from '@staratlas/data-source';
import { AnchorProvider, Program, Wallet } from '@project-serum/anchor';

async function fetchBlockchainData() {
    try {
        const rpcHost = process.env.NODE_RPC_HOST ?? 'default_rpc_host';
        const connection = new Connection(rpcHost);

        const walletKeypair = Keypair.generate();
        const provider = new AnchorProvider(
            connection,
            new Wallet(walletKeypair),
            AnchorProvider.defaultOptions(),
        );
        const craftingProgramPublicKey = process.env.CRAFTING_PROGRAM_PUBLIC_KEY;
        if (!craftingProgramPublicKey) {
        console.error('The CRAFTING_PROGRAM_PUBLIC_KEY environment variable is not set.');
        return;
        }
        const craftingProgram = new Program(
            CRAFTING_IDL,
            new PublicKey(craftingProgramPublicKey),
            provider,
        );

        const recipeAccounts: Recipe[] = (
            await readAllFromRPC(connection, craftingProgram, Recipe, 'processed')
        ).map((recipe: DecodedAccountData<Recipe>) => recipe.type === 'ok' ? recipe.data : null)
            .filter(recipe => recipe !== null) as Recipe[];

        // Saving to a file in the current directory
        const filePath= process.env.CRAFTING_DATA_RAW
        if (!filePath) {
        console.error('The file name/path has not been set in the environment file... You dang fool!');
        return;
        }
        try {
            fs.writeFileSync(filePath, JSON.stringify(recipeAccounts, null, 2));
            console.log(`Blockchain data fetched and stored successfully at ${filePath}.`);
        } catch (fileError) {
            console.error(`Error writing file at ${filePath}:`, fileError);
        }
    } catch (error) {
        console.error('Error fetching blockchain data:', error);
    }
}

fetchBlockchainData();
