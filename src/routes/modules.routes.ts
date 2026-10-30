import { Router, Request, Response, NextFunction } from 'express';
import { ZipArchive } from 'archiver';
import { z } from 'zod';
import {
  listModules,
  getModuleBySlug,
  publishModule,
  getVersionForDownload,
  getPlatformStats,
  getFeaturedModules,
} from '../services/modules.service.js';
import { query } from '../config/db.js';

const router = Router();

// Zod schema for POST /api/modules upload validation
const ModuleUploadSchema = z.object({
  name: z.string().min(1, 'Module name is required'),
  slug: z.string().optional(),
  categoryId: z.string().min(1, 'Category is required'),
  shortDescription: z.string().optional(),
  description: z.string().optional(),
  framework: z.string().default('React'),
  language: z.string().default('TypeScript'),
  version: z.string().default('1.0.0'),
  tags: z.array(z.string()).optional(),
  files: z.array(
    z.object({
      fileName: z.string(),
      filePath: z.string(),
      content: z.string(),
      language: z.string().default('typescript'),
      isEntry: z.boolean().optional(),
    })
  ).min(1, 'At least one file is required'),
});

// 1. GET /api/modules/stats
// Platform overall statistics (published modules and downloads)
router.get('/stats', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const stats = await getPlatformStats();
    res.json({
      success: true,
      data: stats,
    });
  } catch (err) {
    next(err);
  }
});

// 2. GET /api/modules/featured
// Top featured / downloaded modules
router.get('/featured', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const items = await getFeaturedModules();
    res.json({
      success: true,
      data: items,
    });
  } catch (err) {
    next(err);
  }
});

// 3. GET /api/modules
// Query catalogue with filtering, searching, sorting, and pagination
router.get('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const result = await listModules({
      page: req.query.page ? parseInt(req.query.page as string, 10) : 1,
      limit: req.query.limit ? parseInt(req.query.limit as string, 10) : 12,
      category: req.query.category as string,
      framework: req.query.framework as string,
      search: req.query.search as string,
      sort: req.query.sort as string,
      status: req.query.status as string,
    });

    res.json({
      success: true,
      data: result,
    });
  } catch (err) {
    next(err);
  }
});

// 4. POST /api/modules (Upload / Publish)
// Publish a new module or release a new version with source code files
router.post('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const parseResult = ModuleUploadSchema.safeParse(req.body);
    if (!parseResult.success) {
      res.status(400).json({
        success: false,
        error: 'Validation failed',
        details: parseResult.error.flatten(),
      });
      return;
    }

    const created = await publishModule(parseResult.data);
    res.status(201).json({
      success: true,
      data: {
        id: created.id,
        slug: created.slug,
      },
    });
  } catch (err: any) {
    next(err);
  }
});

// 5. GET /api/modules/:slug/versions/:version/download
// Stream downloadable zip containing all files of the version
router.get('/:slug/versions/:version/download', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const slug = req.params.slug as string;
    const version = req.params.version as string;
    const downloadData = await getVersionForDownload(slug, version);

    if (!downloadData || downloadData.files.length === 0) {
      res.status(404).json({
        success: false,
        error: `Module version ${slug}@${version} not found or contains no files`,
      });
      return;
    }

    const zipFilename = `${slug}-${version}.zip`;
    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename="${zipFilename}"`);

    const archive = new ZipArchive({
      zlib: { level: 9 }, // Maximum compression
    });

    archive.on('error', (err: any) => {
      console.error('[Archive Error]:', err);
      if (!res.headersSent) {
        res.status(500).json({ success: false, error: 'Failed to generate archive' });
      }
    });

    archive.pipe(res);

    // Append each file to the zip archive
    for (const file of downloadData.files) {
      const cleanPath = file.filePath.replace(/^\/+/, '');
      archive.append(file.content, { name: cleanPath });
    }

    await archive.finalize();
  } catch (err) {
    next(err);
  }
});

// 6. GET /api/modules/:slug/versions
// Returns list of versions for a given module
router.get('/:slug/versions', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const slug = req.params.slug as string;
    const sql = `
      SELECT v.id, v.version, v.changelog, v."isLatest", v.status, v."createdAt"
      FROM module_versions v
      JOIN modules m ON v."moduleId" = m.id
      WHERE m.slug = $1
      ORDER BY v."isLatest" DESC, v."createdAt" DESC
    `;
    const result = await query(sql, [slug]);
    res.json({
      success: true,
      data: result.rows,
    });
  } catch (err) {
    next(err);
  }
});

// 7. GET /api/modules/:slug/versions/:version/files
// Returns files list for a given version
router.get('/:slug/versions/:version/files', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const slug = req.params.slug as string;
    const version = req.params.version as string;
    const sql = `
      SELECT f.id, f."filePath", f."fileName", f.language, f.content, f."isEntry"
      FROM module_files f
      JOIN module_versions v ON f."moduleVersionId" = v.id
      JOIN modules m ON v."moduleId" = m.id
      WHERE m.slug = $1 AND v.version = $2
      ORDER BY f."isEntry" DESC, f."filePath" ASC
    `;
    const result = await query(sql, [slug, version]);
    res.json({
      success: true,
      data: result.rows,
    });
  } catch (err) {
    next(err);
  }
});

// 8. GET /api/modules/:slug
// Full module details with current version, files, tags, and related modules
router.get('/:slug', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const slug = req.params.slug as string;
    const moduleItem = await getModuleBySlug(slug);

    if (!moduleItem) {
      res.status(404).json({
        success: false,
        error: `Module with slug '${slug}' not found`,
      });
      return;
    }

    res.json({
      success: true,
      data: moduleItem,
    });
  } catch (err) {
    next(err);
  }
});

export default router;
