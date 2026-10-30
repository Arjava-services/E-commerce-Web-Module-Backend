import express, { Request, Response } from 'express';
import cors from 'cors';
import apiRouter from './routes/index.js';
import { errorHandler } from './middleware/errorHandler.js';

const app = express();

// Enable CORS
const corsOrigins = process.env.CORS_ORIGIN
  ? process.env.CORS_ORIGIN.split(',').map((o) => o.trim())
  : ['http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:3000'];

app.use(
  cors({
    origin: corsOrigins.includes('*') ? '*' : corsOrigins,
    credentials: true,
  })
);

// Body parsers (support large source code payloads)
app.use(express.json({ limit: '20mb' }));
app.use(express.urlencoded({ extended: true, limit: '20mb' }));

// Mount API routes
app.use('/api', apiRouter);

// Root greeting
app.get('/', (_req: Request, res: Response) => {
  res.json({
    name: 'E-Commerce Web Module Platform API',
    version: '1.0.0',
    status: 'online',
    docs: '/api/health',
  });
});

// 404 Fallback
app.use((req: Request, res: Response) => {
  res.status(404).json({
    success: false,
    error: `Cannot ${req.method} ${req.originalUrl}`,
  });
});

// Centralized Error Handling
app.use(errorHandler);

export default app;

