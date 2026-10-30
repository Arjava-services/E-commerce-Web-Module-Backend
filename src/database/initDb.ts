import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { pool } from '../config/db.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export async function initDb() {
  console.log('🔄 Initializing database schema...');
  const schemaPath = path.join(__dirname, 'schema.sql');
  const sql = fs.readFileSync(schemaPath, 'utf-8');

  const client = await pool.connect();
  try {
    await client.query(sql);
    console.log('✅ Database schema initialized successfully.');
  } catch (err: any) {
    console.error('❌ Failed to initialize database schema:', err.message);
    throw err;
  } finally {
    client.release();
  }
}

if (process.argv[1] === __filename) {
  initDb()
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}

