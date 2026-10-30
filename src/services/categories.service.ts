import { query } from '../config/db.js';

export interface CategoryItem {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  icon: string | null;
  displayOrder: number;
  moduleCount: number;
}

export async function getAllCategories(): Promise<CategoryItem[]> {
  const sql = `
    SELECT 
      c.id, 
      c.slug, 
      c.name, 
      c.description, 
      c.icon, 
      c."displayOrder",
      COUNT(m.id)::int AS "moduleCount"
    FROM categories c
    LEFT JOIN modules m ON c.id = m."categoryId" AND m.status = 'PUBLISHED'
    GROUP BY c.id
    ORDER BY c."displayOrder" ASC, c.name ASC
  `;
  const result = await query<CategoryItem>(sql);
  return result.rows;
}

export async function getCategoryBySlugOrId(identifier: string) {
  const sql = `
    SELECT id, slug, name, description, icon, "displayOrder"
    FROM categories
    WHERE slug = $1 OR id = $1
    LIMIT 1
  `;
  const result = await query(sql, [identifier]);
  return result.rows[0] || null;
}

