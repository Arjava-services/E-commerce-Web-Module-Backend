from fastapi import APIRouter, HTTPException
from app.database import get_cursor, is_mysql

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("")
def get_categories():
    """
    1. GET /api/categories
    Used by the navigation sidebar, categories page, and module upload dropdown.
    Response data: Array<Category>
      id (string), slug (string), name (string), description (string),
      icon (string), displayOrder (number), moduleCount (number, optional)
    """
    try:
        col_order = "`displayOrder`" if is_mysql else '"displayOrder"'
        col_cat_id = "`categoryId`" if is_mysql else '"categoryId"'

        sql = f"""
            SELECT 
                c.id, 
                c.slug, 
                c.name, 
                c.description, 
                c.icon, 
                c.{col_order} AS {col_order},
                COUNT(m.id) AS moduleCount
            FROM categories c
            LEFT JOIN modules m ON c.id = m.{col_cat_id} AND m.status = 'PUBLISHED'
            GROUP BY c.id, c.slug, c.name, c.description, c.icon, c.{col_order}
            ORDER BY c.{col_order} ASC, c.name ASC
        """
        with get_cursor() as cur:
            cur.execute(sql)
            categories = cur.fetchall()

        formatted = []
        for cat in categories:
            row = dict(cat)
            disp_order = row.get("displayOrder") or row.get("displayorder") or 0
            mod_count = row.get("moduleCount") or row.get("modulecount") or 0
            formatted.append({
                "id": str(row["id"]),
                "slug": str(row["slug"]),
                "name": str(row["name"]),
                "description": row.get("description") or "",
                "icon": row.get("icon") or "Package",
                "displayOrder": int(disp_order),
                "moduleCount": int(mod_count),
            })

        return {
            "success": True,
            "data": formatted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
