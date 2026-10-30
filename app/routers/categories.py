from fastapi import APIRouter, HTTPException
from app.database import get_cursor

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("")
def get_categories():
    """
    Returns the list of categories for the catalogue sidebar and upload form.
    Response: Array of { id, slug, name, description, icon, displayOrder, moduleCount }
    """
    try:
        sql = """
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
        """
        with get_cursor() as cur:
            cur.execute(sql)
            categories = cur.fetchall()

        return {
            "success": True,
            "data": categories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

