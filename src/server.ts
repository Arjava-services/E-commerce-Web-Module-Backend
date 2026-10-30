import dotenv from 'dotenv';
dotenv.config();

import app from './app.js';
import { pool } from './config/db.js';

const PORT = parseInt(process.env.PORT || '4000', 10);

async function startServer() {
  try {
    // Verify database connection
    const client = await pool.connect();
    console.log('✅ PostgreSQL connected successfully');
    client.release();

    const server = app.listen(PORT, '0.0.0.0', () => {
      console.log(`🚀 E-Commerce Web Module Platform Backend running on http://localhost:${PORT}`);
      console.log(`📡 API Endpoints available under http://localhost:${PORT}/api`);
    });

    // Graceful Shutdown
    const shutdown = async (signal: string) => {
      console.log(`\n🛑 Received ${signal}, closing server and database pool...`);
      server.close(async () => {
        await pool.end();
        console.log('🏁 Server closed cleanly.');
        process.exit(0);
      });
    };

    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGTERM', () => shutdown('SIGTERM'));
  } catch (err: any) {
    console.error('❌ Failed to start server:', err.message);
    process.exit(1);
  }
}

startServer();

