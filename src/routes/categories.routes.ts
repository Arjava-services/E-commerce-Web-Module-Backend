import { Router, Request, Response, NextFunction } from 'express';
import { getAllCategories } from '../services/categories.service.js';

const router = Router();

// GET /api/categories
// Returns the list of categories for the catalogue sidebar and upload form
router.get('/', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const categories = await getAllCategories();
    res.json({
      success: true,
      data: categories,
    });
  } catch (err) {
    next(err);
  }
});

export default router;

