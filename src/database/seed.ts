import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { pool } from '../config/db.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export async function seedDb() {
  console.log('🌱 Seeding database...');
  const seedPath = path.join(__dirname, 'seed.sql');
  const sql = fs.readFileSync(seedPath, 'utf-8');

  const client = await pool.connect();
  try {
    await client.query(sql);
    console.log('✅ Database seeded successfully.');
  } catch (err: any) {
    console.error('❌ Failed to seed database:', err.message);
    throw err;
  } finally {
    client.release();
  }
}

if (process.argv[1] === __filename) {
  seedDb()
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}

