import { Router, Request, Response } from 'express';
import categoriesRouter from './categories.routes.js';
import modulesRouter from './modules.routes.js';
import { query } from '../config/db.js';

const apiRouter = Router();

// Health check endpoint
apiRouter.get('/health', async (_req: Request, res: Response) => {
  try {
    const dbRes = await query('SELECT 1 as connected');
    res.json({
      success: true,
      data: {
        status: 'ok',
        uptime: process.uptime(),
        database: dbRes.rows.length > 0 ? 'connected' : 'disconnected',
        timestamp: new Date().toISOString(),
      },
    });
  } catch (err: any) {
    res.status(503).json({
      success: false,
      error: 'Database connection error',
      details: err.message,
    });
  }
});

// Technologies list endpoint (for frontend compatibility)
apiRouter.get('/technologies', async (_req: Request, res: Response) => {
  try {
    const sql = `
      SELECT DISTINCT framework AS name, 'FRONTEND' AS category 
      FROM modules 
      WHERE framework IS NOT NULL AND framework != ''
      UNION
      SELECT DISTINCT language AS name, 'FRONTEND' AS category 
      FROM modules 
      WHERE language IS NOT NULL AND language != ''
    `;
    const resDb = await query(sql);
    const techList = resDb.rows.map((row) => ({
      id: row.name.toLowerCase(),
      slug: row.name.toLowerCase(),
      name: row.name,
      category: row.category,
      icon: null,
    }));
    res.json({ success: true, data: techList });
  } catch {
    res.json({
      success: true,
      data: [
        { id: 'react', slug: 'react', name: 'React', category: 'FRONTEND', icon: null },
        { id: 'typescript', slug: 'typescript', name: 'TypeScript', category: 'FRONTEND', icon: null },
        { id: 'nodejs', slug: 'nodejs', name: 'Node.js', category: 'BACKEND', icon: null },
      ],
    });
  }
});

// Core routes
apiRouter.use('/categories', categoriesRouter);
apiRouter.use('/modules', modulesRouter);

export default apiRouter;

