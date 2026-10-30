import { query, getClient } from '../config/db.js';

export interface ModuleQueryParams {
  page?: number;
  limit?: number;
  category?: string;
  framework?: string;
  search?: string;
  sort?: string;
  status?: string;
}

export interface ModuleFileItem {
  id?: string;
  filePath: string;
  fileName: string;
  language: string;
  content: string;
  isEntry?: boolean;
}

export interface PublishModuleInput {
  name: string;
  slug?: string;
  categoryId: string;
  shortDescription?: string;
  description?: string;
  framework?: string;
  language?: string;
  version?: string;
  tags?: string[];
  files: ModuleFileItem[];
}

export async function listModules(params: ModuleQueryParams) {
  const page = Math.max(1, Number(params.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(params.limit) || 12));
  const offset = (page - 1) * limit;

  const conditions: string[] = [];
  const values: any[] = [];
  let paramIdx = 1;

  // Status filter (default to PUBLISHED)
  const status = params.status || 'PUBLISHED';
  conditions.push(`m.status = $${paramIdx++}`);
  values.push(status);

  // Category filter (slug or id)
  if (params.category && params.category !== 'all') {
    conditions.push(`(c.slug = $${paramIdx} OR m."categoryId" = $${paramIdx})`);
    values.push(params.category);
    paramIdx++;
  }

  // Framework filter
  if (params.framework && params.framework !== 'all') {
    conditions.push(`m.framework ILIKE $${paramIdx++}`);
    values.push(params.framework);
  }

  // Search filter
  if (params.search && params.search.trim()) {
    conditions.push(`(m.name ILIKE $${paramIdx} OR m."shortDescription" ILIKE $${paramIdx} OR m.description ILIKE $${paramIdx} OR m.slug ILIKE $${paramIdx})`);
    values.push(`%${params.search.trim()}%`);
    paramIdx++;
  }

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

  // Sort ordering
  let orderBy = 'm."updatedAt" DESC';
  if (params.sort === 'downloads') {
    orderBy = 'm."downloadCount" DESC, m."updatedAt" DESC';
  } else if (params.sort === 'newest') {
    orderBy = 'm."createdAt" DESC';
  } else if (params.sort === 'name') {
    orderBy = 'm.name ASC';
  } else if (params.sort === 'updated') {
    orderBy = 'm."updatedAt" DESC';
  }

  // Total count query
  const countSql = `
    SELECT COUNT(m.id)::int AS total
    FROM modules m
    LEFT JOIN categories c ON m."categoryId" = c.id
    ${whereClause}
  `;
  const countRes = await query<{ total: number }>(countSql, values);
  const total = countRes.rows[0]?.total || 0;
  const totalPages = Math.ceil(total / limit) || 1;

  // Data query
  const dataSql = `
    SELECT 
      m.id,
      m.slug,
      m.name,
      m."shortDescription",
      m.framework,
      m.language,
      m.status,
      m."downloadCount",
      m."createdAt",
      m."updatedAt",
      json_build_object(
        'id', c.id,
        'name', c.name,
        'slug', c.slug,
        'icon', c.icon
      ) AS category,
      (
        SELECT v.version 
        FROM module_versions v 
        WHERE v."moduleId" = m.id 
        ORDER BY v."isLatest" DESC, v."createdAt" DESC 
        LIMIT 1
      ) AS "latestVersion"
    FROM modules m
    LEFT JOIN categories c ON m."categoryId" = c.id
    ${whereClause}
    ORDER BY ${orderBy}
    LIMIT $${paramIdx++} OFFSET $${paramIdx++}
  `;

  values.push(limit, offset);
  const dataRes = await query(dataSql, values);

  return {
    items: dataRes.rows,
    total,
    page,
    totalPages,
  };
}

export async function getModuleBySlug(slug: string) {
  // 1. Fetch module with category
  const moduleSql = `
    SELECT 
      m.id,
      m.slug,
      m.name,
      m."shortDescription",
      m.description,
      m."categoryId",
      m.status,
      m.framework,
      m.language,
      m."downloadCount",
      m."createdAt",
      m."updatedAt",
      json_build_object(
        'id', c.id,
        'name', c.name,
        'slug', c.slug,
        'description', c.description,
        'icon', c.icon
      ) AS category
    FROM modules m
    LEFT JOIN categories c ON m."categoryId" = c.id
    WHERE m.slug = $1
    LIMIT 1
  `;
  const moduleRes = await query(moduleSql, [slug]);
  const moduleItem = moduleRes.rows[0];
  if (!moduleItem) return null;

  // 2. Fetch versions
  const versionsSql = `
    SELECT 
      id,
      "moduleId",
      version,
      changelog,
      "isLatest",
      status,
      "createdAt"
    FROM module_versions
    WHERE "moduleId" = $1
    ORDER BY "isLatest" DESC, "createdAt" DESC
  `;
  const versionsRes = await query(versionsSql, [moduleItem.id]);
  const versions = versionsRes.rows;

  // Determine current version (the latest or first available)
  const currentVer = versions.find((v: any) => v.isLatest) || versions[0] || null;

  let currentVersionWithFiles = null;
  if (currentVer) {
    const filesSql = `
      SELECT 
        id,
        "filePath",
        "fileName",
        language,
        content,
        "isEntry"
      FROM module_files
      WHERE "moduleVersionId" = $1
      ORDER BY "isEntry" DESC, "filePath" ASC
    `;
    const filesRes = await query(filesSql, [currentVer.id]);
    currentVersionWithFiles = {
      ...currentVer,
      files: filesRes.rows,
    };
  }

  // 3. Fetch tags
  const tagsSql = `
    SELECT t.id, t.slug, t.name
    FROM tags t
    JOIN module_tags mt ON t.id = mt."tagId"
    WHERE mt."moduleId" = $1
    ORDER BY t.name ASC
  `;
  const tagsRes = await query(tagsSql, [moduleItem.id]);

  // 4. Fetch related modules (same category)
  const relatedSql = `
    SELECT 
      m.id,
      m.slug,
      m.name,
      m."shortDescription",
      m.framework,
      m.language,
      m."downloadCount"
    FROM modules m
    WHERE m."categoryId" = $1 AND m.id != $2 AND m.status = 'PUBLISHED'
    ORDER BY m."downloadCount" DESC
    LIMIT 4
  `;
  const relatedRes = await query(relatedSql, [moduleItem.categoryId, moduleItem.id]);

  return {
    ...moduleItem,
    latestVersion: currentVer?.version || '1.0.0',
    versions,
    currentVersion: currentVersionWithFiles,
    tags: tagsRes.rows,
    relatedModules: relatedRes.rows,
  };
}

export async function publishModule(data: PublishModuleInput) {
  const client = await getClient();

  try {
    await client.query('BEGIN');

    // Generate slug if not provided
    const slug = (data.slug || data.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')).trim();

    // Resolve categoryId (could be UUID or slug)
    let categoryId = data.categoryId;
    const catCheck = await client.query('SELECT id FROM categories WHERE id = $1 OR slug = $1 LIMIT 1', [categoryId]);
    if (catCheck.rows.length === 0) {
      // Default to first available category if not matched
      const fallbackCat = await client.query('SELECT id FROM categories ORDER BY "displayOrder" ASC LIMIT 1');
      if (fallbackCat.rows.length === 0) {
        throw new Error('No categories exist in database. Please run seed script.');
      }
      categoryId = fallbackCat.rows[0].id;
    } else {
      categoryId = catCheck.rows[0].id;
    }

    const shortDesc = data.shortDescription || data.name;
    const desc = data.description || shortDesc;
    const framework = data.framework || 'React';
    const language = data.language || 'TypeScript';
    const versionStr = data.version || '1.0.0';

    // 1. Upsert Module
    const moduleUpsertSql = `
      INSERT INTO modules (
        id, slug, name, "shortDescription", description, "categoryId", 
        status, framework, language, "updatedAt"
      )
      VALUES (
        gen_random_uuid()::text, $1, $2, $3, $4, $5, 
        'PUBLISHED', $6, $7, CURRENT_TIMESTAMP
      )
      ON CONFLICT (slug) DO UPDATE SET
        name = EXCLUDED.name,
        "shortDescription" = EXCLUDED."shortDescription",
        description = EXCLUDED.description,
        "categoryId" = EXCLUDED."categoryId",
        framework = EXCLUDED.framework,
        language = EXCLUDED.language,
        status = 'PUBLISHED',
        "updatedAt" = CURRENT_TIMESTAMP
      RETURNING id, slug;
    `;

    const moduleRes = await client.query(moduleUpsertSql, [
      slug,
      data.name,
      shortDesc,
      desc,
      categoryId,
      framework,
      language,
    ]);
    const moduleId = moduleRes.rows[0].id;

    // 2. Mark previous versions isLatest = false
    await client.query(
      'UPDATE module_versions SET "isLatest" = false WHERE "moduleId" = $1',
      [moduleId]
    );

    // 3. Upsert Version
    const versionUpsertSql = `
      INSERT INTO module_versions (
        id, "moduleId", version, changelog, "isLatest", status, "updatedAt"
      )
      VALUES (
        gen_random_uuid()::text, $1, $2, $3, true, 'PUBLISHED', CURRENT_TIMESTAMP
      )
      ON CONFLICT ("moduleId", version) DO UPDATE SET
        changelog = EXCLUDED.changelog,
        "isLatest" = true,
        status = 'PUBLISHED',
        "updatedAt" = CURRENT_TIMESTAMP
      RETURNING id;
    `;
    const versionRes = await client.query(versionUpsertSql, [
      moduleId,
      versionStr,
      `Release ${versionStr}`,
    ]);
    const versionId = versionRes.rows[0].id;

    // 4. Insert Module Files
    if (data.files && data.files.length > 0) {
      // Clear previous files for this version
      await client.query('DELETE FROM module_files WHERE "moduleVersionId" = $1', [versionId]);

      for (const file of data.files) {
        const fileSql = `
          INSERT INTO module_files (
            id, "moduleVersionId", "filePath", "fileName", language, content, "isEntry"
          )
          VALUES (
            gen_random_uuid()::text, $1, $2, $3, $4, $5, $6
          );
        `;
        await client.query(fileSql, [
          versionId,
          file.filePath || file.fileName,
          file.fileName,
          file.language || 'typescript',
          file.content || '',
          Boolean(file.isEntry),
        ]);
      }
    }

    // 5. Link Tags if provided
    if (data.tags && Array.isArray(data.tags)) {
      for (const tagRaw of data.tags) {
        const tagName = tagRaw.trim();
        if (!tagName) continue;
        const tagSlug = tagName.toLowerCase().replace(/[^a-z0-9]+/g, '-');

        // Upsert tag
        const tagRes = await client.query(
          `INSERT INTO tags (id, slug, name) 
           VALUES (gen_random_uuid()::text, $1, $2)
           ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
           RETURNING id`,
          [tagSlug, tagName]
        );
        const tagId = tagRes.rows[0].id;

        // Link in module_tags
        await client.query(
          `INSERT INTO module_tags ("moduleId", "tagId")
           VALUES ($1, $2)
           ON CONFLICT DO NOTHING`,
          [moduleId, tagId]
        );
      }
    }

    await client.query('COMMIT');

    return {
      id: moduleId,
      slug,
    };
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}

export async function getVersionForDownload(slug: string, version: string) {
  // Check module & version
  const sql = `
    SELECT 
      m.id AS "moduleId",
      m.slug,
      m.name,
      v.id AS "versionId",
      v.version
    FROM modules m
    JOIN module_versions v ON m.id = v."moduleId"
    WHERE m.slug = $1 AND v.version = $2
    LIMIT 1
  `;
  const res = await query(sql, [slug, version]);
  const item = res.rows[0];
  if (!item) return null;

  // Increment download count on module
  await query('UPDATE modules SET "downloadCount" = "downloadCount" + 1 WHERE id = $1', [item.moduleId]);

  // Fetch files
  const filesSql = `
    SELECT "filePath", "fileName", content
    FROM module_files
    WHERE "moduleVersionId" = $1
    ORDER BY "filePath" ASC
  `;
  const filesRes = await query(filesSql, [item.versionId]);

  return {
    module: item,
    files: filesRes.rows,
  };
}

export async function getPlatformStats() {
  const sql = `
    SELECT 
      COUNT(id)::int AS "publishedModules",
      COALESCE(SUM("downloadCount"), 0)::int AS "totalDownloads"
    FROM modules
    WHERE status = 'PUBLISHED'
  `;
  const res = await query(sql);
  return {
    publishedModules: res.rows[0]?.publishedModules || 0,
    totalDownloads: res.rows[0]?.totalDownloads || 0,
  };
}

export async function getFeaturedModules() {
  const sql = `
    SELECT 
      m.id,
      m.slug,
      m.name,
      m."shortDescription",
      m.framework,
      m.language,
      m.status,
      m."downloadCount",
      json_build_object(
        'name', c.name,
        'slug', c.slug,
        'icon', c.icon
      ) AS category,
      (
        SELECT v.version 
        FROM module_versions v 
        WHERE v."moduleId" = m.id 
        ORDER BY v."isLatest" DESC, v."createdAt" DESC 
        LIMIT 1
      ) AS "latestVersion"
    FROM modules m
    LEFT JOIN categories c ON m."categoryId" = c.id
    WHERE m.status = 'PUBLISHED'
    ORDER BY m."downloadCount" DESC, m."updatedAt" DESC
    LIMIT 8
  `;
  const res = await query(sql);
  return res.rows;
}

