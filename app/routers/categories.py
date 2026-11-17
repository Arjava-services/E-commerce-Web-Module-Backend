from fastapi import APIRouter, HTTPException
from app.database import get_cursor, is_mysql

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("")
def get_categories():
    """
    Returns the list of categories for the catalogue sidebar and upload form.
    Response: Array of { id, slug, name, description, icon, displayOrder, moduleCount }
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
                c.{col_order} AS displayOrder,
                COUNT(m.id) AS moduleCount
            FROM categories c
            LEFT JOIN modules m ON c.id = m.{col_cat_id} AND m.status = 'PUBLISHED'
            GROUP BY c.id, c.slug, c.name, c.description, c.icon, c.{col_order}
            ORDER BY c.{col_order} ASC, c.name ASC
        """
        with get_cursor() as cur:
            cur.execute(sql)
            categories = cur.fetchall()

        # Format rows cleanly
        formatted = []
        for cat in categories:
            row = dict(cat)
            row["displayOrder"] = int(row.get("displayOrder") or 0)
            row["moduleCount"] = int(row.get("moduleCount") or 0)
            formatted.append(row)

        return {
            "success": True,
            "data": formatted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
