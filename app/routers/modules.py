import io
import re
import math
import time
import zipfile
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from app.database import get_db, get_cursor, is_mysql
from app.schemas import ModuleUploadPayload

router = APIRouter(prefix="/modules", tags=["Modules"])

def q(col: str) -> str:
    """Quotes an identifier for MySQL (backticks) or PostgreSQL (double quotes)."""
    return f"`{col}`" if is_mysql else f'"{col}"'

def gen_uuid_sql() -> str:
    """Returns SQL expression for generating a UUID."""
    return "UUID()" if is_mysql else "gen_random_uuid()::text"

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

# 1. GET /api/modules/stats
@router.get("/stats")
def get_stats():
    """
    Returns platform statistics: publishedModules and totalDownloads
    """
    try:
        sql = f"""
            SELECT 
                COUNT(id) AS {q("publishedModules")},
                COALESCE(SUM({q("downloadCount")}), 0) AS {q("totalDownloads")}
            FROM modules
            WHERE status = 'PUBLISHED'
        """
        with get_cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()

        pub_count = int(row.get("publishedModules") or row.get("publishedmodules") or 0)
        tot_downloads = int(row.get("totalDownloads") or row.get("totaldownloads") or 0)

        return {
            "success": True,
            "data": {
                "publishedModules": pub_count,
                "totalDownloads": tot_downloads,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. GET /api/modules/featured
@router.get("/featured")
def get_featured():
    """
    Returns top featured/downloaded modules
    """
    try:
        sql = f"""
            SELECT 
                m.id,
                m.slug,
                m.name,
                m.{q("shortDescription")} AS {q("shortDescription")},
                m.framework,
                m.language,
                m.status,
                m.{q("downloadCount")} AS {q("downloadCount")},
                c.id AS cat_id,
                c.name AS cat_name,
                c.slug AS cat_slug,
                c.icon AS cat_icon,
                (
                    SELECT v.version 
                    FROM module_versions v 
                    WHERE v.{q("moduleId")} = m.id 
                    ORDER BY v.{q("isLatest")} DESC, v.{q("createdAt")} DESC 
                    LIMIT 1
                ) AS {q("latestVersion")}
            FROM modules m
            LEFT JOIN categories c ON m.{q("categoryId")} = c.id
            WHERE m.status = 'PUBLISHED'
            ORDER BY m.{q("downloadCount")} DESC, m.{q("updatedAt")} DESC
            LIMIT 8
        """
        with get_cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

        items = []
        for r in rows:
            item = dict(r)
            cat_id = item.pop("cat_id", None)
            cat_name = item.pop("cat_name", None)
            cat_slug = item.pop("cat_slug", None)
            cat_icon = item.pop("cat_icon", None)
            item["category"] = {
                "id": cat_id,
                "name": cat_name,
                "slug": cat_slug,
                "icon": cat_icon,
            } if cat_name else None
            items.append(item)

        return {
            "success": True,
            "data": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. GET /api/modules
@router.get("")
def list_modules(
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    category: Optional[str] = Query(None),
    framework: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query("updated"),
    status_filter: Optional[str] = Query("PUBLISHED", alias="status")
):
    """
    Query catalogue with filtering, searching, sorting, and pagination
    """
    try:
        offset = (page - 1) * limit
        conditions = []
        values = []

        # Status filter
        if status_filter:
            conditions.append("m.status = %s")
            values.append(status_filter)

        # Category filter (by slug or id)
        if category and category != "all":
            conditions.append(f'(c.slug = %s OR m.{q("categoryId")} = %s)')
            values.extend([category, category])

        # Framework filter
        if framework and framework != "all":
            conditions.append("m.framework LIKE %s" if is_mysql else "m.framework ILIKE %s")
            values.append(framework)

        # Search filter
        if search and search.strip():
            term = f"%{search.strip()}%"
            like_op = "LIKE" if is_mysql else "ILIKE"
            conditions.append(
                f'(m.name {like_op} %s OR m.{q("shortDescription")} {like_op} %s OR m.description {like_op} %s OR m.slug {like_op} %s)'
            )
            values.extend([term, term, term, term])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Order by
        order_by = f'm.{q("updatedAt")} DESC'
        if sort == "downloads":
            order_by = f'm.{q("downloadCount")} DESC, m.{q("updatedAt")} DESC'
        elif sort == "newest":
            order_by = f'm.{q("createdAt")} DESC'
        elif sort == "name":
            order_by = "m.name ASC"
        elif sort == "updated":
            order_by = f'm.{q("updatedAt")} DESC'

        with get_cursor() as cur:
            # Count total
            count_sql = f"""
                SELECT COUNT(m.id) AS total
                FROM modules m
                LEFT JOIN categories c ON m.{q("categoryId")} = c.id
                {where_clause}
            """
            cur.execute(count_sql, values)
            count_row = cur.fetchone()
            total = int(count_row.get("total") if count_row else 0)
            total_pages = math.ceil(total / limit) if total > 0 else 1

            # Fetch items
            data_sql = f"""
                SELECT 
                    m.id,
                    m.slug,
                    m.name,
                    m.{q("shortDescription")} AS {q("shortDescription")},
                    m.framework,
                    m.language,
                    m.status,
                    m.{q("downloadCount")} AS {q("downloadCount")},
                    m.{q("createdAt")} AS {q("createdAt")},
                    m.{q("updatedAt")} AS {q("updatedAt")},
                    c.id AS cat_id,
                    c.name AS cat_name,
                    c.slug AS cat_slug,
                    c.icon AS cat_icon,
                    (
                        SELECT v.version 
                        FROM module_versions v 
                        WHERE v.{q("moduleId")} = m.id 
                        ORDER BY v.{q("isLatest")} DESC, v.{q("createdAt")} DESC 
                        LIMIT 1
                    ) AS {q("latestVersion")}
                FROM modules m
                LEFT JOIN categories c ON m.{q("categoryId")} = c.id
                {where_clause}
                ORDER BY {order_by}
                LIMIT %s OFFSET %s
            """
            cur.execute(data_sql, values + [limit, offset])
            rows = cur.fetchall()

        items = []
        for r in rows:
            item = dict(r)
            cat_id = item.pop("cat_id", None)
            cat_name = item.pop("cat_name", None)
            cat_slug = item.pop("cat_slug", None)
            cat_icon = item.pop("cat_icon", None)
            item["category"] = {
                "id": cat_id,
                "name": cat_name,
                "slug": cat_slug,
                "icon": cat_icon,
            } if cat_name else None
            items.append(item)

        return {
            "success": True,
            "data": {
                "items": items,
                "total": total,
                "page": page,
                "totalPages": total_pages,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. POST /api/modules (Upload / Publish)
@router.post("", status_code=status.HTTP_201_CREATED)
def publish_module(payload: ModuleUploadPayload):
    """
    Publish a new module or release a new version with source code files
    """
    slug = (payload.slug or slugify(payload.name)).strip()
    if not slug:
        slug = f"module-{int(time.time())}"

    short_desc = payload.shortDescription or payload.name
    desc = payload.description or short_desc

    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Resolve Category ID (UUID or slug)
            cur.execute(
                'SELECT id FROM categories WHERE id = %s OR slug = %s LIMIT 1',
                (payload.categoryId, payload.categoryId)
            )
            cat_row = cur.fetchone()
            if not cat_row:
                cur.execute(f'SELECT id FROM categories ORDER BY {q("displayOrder")} ASC LIMIT 1')
                first_cat = cur.fetchone()
                if not first_cat:
                    raise HTTPException(status_code=400, detail="No categories exist in database")
                category_id = first_cat[0] if isinstance(first_cat, (list, tuple)) else first_cat["id"]
            else:
                category_id = cat_row[0] if isinstance(cat_row, (list, tuple)) else cat_row["id"]

            # 2. Check if Module exists
            cur.execute('SELECT id FROM modules WHERE slug = %s LIMIT 1', (slug,))
            existing_mod = cur.fetchone()

            if existing_mod:
                module_id = existing_mod[0] if isinstance(existing_mod, (list, tuple)) else existing_mod["id"]
                update_sql = f"""
                    UPDATE modules SET
                        name = %s,
                        {q("shortDescription")} = %s,
                        description = %s,
                        {q("categoryId")} = %s,
                        framework = %s,
                        language = %s,
                        status = 'PUBLISHED',
                        {q("updatedAt")} = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                cur.execute(update_sql, (
                    payload.name,
                    short_desc,
                    desc,
                    category_id,
                    payload.framework,
                    payload.language,
                    module_id,
                ))
            else:
                insert_sql = f"""
                    INSERT INTO modules (
                        id, slug, name, {q("shortDescription")}, description, {q("categoryId")}, 
                        status, framework, language, {q("updatedAt")}
                    )
                    VALUES (
                        {gen_uuid_sql()}, %s, %s, %s, %s, %s, 
                        'PUBLISHED', %s, %s, CURRENT_TIMESTAMP
                    )
                """
                cur.execute(insert_sql, (
                    slug,
                    payload.name,
                    short_desc,
                    desc,
                    category_id,
                    payload.framework,
                    payload.language,
                ))
                cur.execute('SELECT id FROM modules WHERE slug = %s LIMIT 1', (slug,))
                new_mod = cur.fetchone()
                module_id = new_mod[0] if isinstance(new_mod, (list, tuple)) else new_mod["id"]

            # 3. Mark previous versions isLatest = False
            cur.execute(
                f'UPDATE module_versions SET {q("isLatest")} = FALSE WHERE {q("moduleId")} = %s',
                (module_id,)
            )

            # 4. Upsert Version
            cur.execute(
                f'SELECT id FROM module_versions WHERE {q("moduleId")} = %s AND version = %s LIMIT 1',
                (module_id, payload.version)
            )
            existing_ver = cur.fetchone()

            if existing_ver:
                version_id = existing_ver[0] if isinstance(existing_ver, (list, tuple)) else existing_ver["id"]
                update_ver_sql = f"""
                    UPDATE module_versions SET
                        changelog = %s,
                        {q("isLatest")} = TRUE,
                        status = 'PUBLISHED',
                        {q("updatedAt")} = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                cur.execute(update_ver_sql, (f"Release {payload.version}", version_id))
            else:
                insert_ver_sql = f"""
                    INSERT INTO module_versions (
                        id, {q("moduleId")}, version, changelog, {q("isLatest")}, status, {q("updatedAt")}
                    )
                    VALUES (
                        {gen_uuid_sql()}, %s, %s, %s, TRUE, 'PUBLISHED', CURRENT_TIMESTAMP
                    )
                """
                cur.execute(insert_ver_sql, (
                    module_id,
                    payload.version,
                    f"Release {payload.version}",
                ))
                cur.execute(
                    f'SELECT id FROM module_versions WHERE {q("moduleId")} = %s AND version = %s LIMIT 1',
                    (module_id, payload.version)
                )
                new_ver = cur.fetchone()
                version_id = new_ver[0] if isinstance(new_ver, (list, tuple)) else new_ver["id"]

            # 5. Insert files
            cur.execute(f'DELETE FROM module_files WHERE {q("moduleVersionId")} = %s', (version_id,))
            insert_file_sql = f"""
                INSERT INTO module_files (
                    id, {q("moduleVersionId")}, {q("filePath")}, {q("fileName")}, language, content, {q("isEntry")}
                )
                VALUES (
                    {gen_uuid_sql()}, %s, %s, %s, %s, %s, %s
                )
            """
            for f in payload.files:
                file_path = f.filePath or f.fileName
                cur.execute(insert_file_sql, (
                    version_id,
                    file_path,
                    f.fileName,
                    f.language or "typescript",
                    f.content or "",
                    bool(f.isEntry),
                ))

            # 6. Associate Tags
            if payload.tags:
                for tag_name in payload.tags:
                    tag_name = tag_name.strip()
                    if not tag_name:
                        continue
                    tag_slug = slugify(tag_name)
                    
                    cur.execute('SELECT id FROM tags WHERE slug = %s LIMIT 1', (tag_slug,))
                    tag_row = cur.fetchone()
                    if tag_row:
                        tag_id = tag_row[0] if isinstance(tag_row, (list, tuple)) else tag_row["id"]
                    else:
                        cur.execute(
                            f'INSERT INTO tags (id, slug, name) VALUES ({gen_uuid_sql()}, %s, %s)',
                            (tag_slug, tag_name)
                        )
                        cur.execute('SELECT id FROM tags WHERE slug = %s LIMIT 1', (tag_slug,))
                        new_tag = cur.fetchone()
                        tag_id = new_tag[0] if isinstance(new_tag, (list, tuple)) else new_tag["id"]

                    # Link tag
                    link_sql = (
                        f'INSERT IGNORE INTO module_tags ({q("moduleId")}, {q("tagId")}) VALUES (%s, %s)'
                        if is_mysql else
                        f'INSERT INTO module_tags ({q("moduleId")}, {q("tagId")}) VALUES (%s, %s) ON CONFLICT DO NOTHING'
                    )
                    cur.execute(link_sql, (module_id, tag_id))

    return {
        "success": True,
        "data": {
            "id": module_id,
            "slug": slug,
        }
    }

# 5. GET /api/modules/{slug}/versions/{version}/download
@router.get("/{slug}/versions/{version}/download")
def download_module_version(slug: str, version: str):
    """
    Returns downloadable ZIP package of the module version and increments downloadCount
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            # Find module & version
            sql = f"""
                SELECT 
                    m.id AS moduleId,
                    m.slug,
                    m.name,
                    v.id AS versionId,
                    v.version
                FROM modules m
                JOIN module_versions v ON m.id = v.{q("moduleId")}
                WHERE m.slug = %s AND v.version = %s
                LIMIT 1
            """
            cur.execute(sql, (slug, version))
            item = cur.fetchone()
            if not item:
                raise HTTPException(
                    status_code=404,
                    detail=f"Module version {slug}@{version} not found"
                )
            module_id = item[0] if isinstance(item, (list, tuple)) else (item.get("moduleId") or item.get("moduleid"))
            version_id = item[3] if isinstance(item, (list, tuple)) else (item.get("versionId") or item.get("versionid"))

            # Increment download count
            cur.execute(
                f'UPDATE modules SET {q("downloadCount")} = {q("downloadCount")} + 1 WHERE id = %s',
                (module_id,)
            )

            # Get files
            files_sql = f"""
                SELECT {q("filePath")} AS {q("filePath")}, {q("fileName")} AS {q("fileName")}, content
                FROM module_files
                WHERE {q("moduleVersionId")} = %s
                ORDER BY {q("filePath")} ASC
            """
            cur.execute(files_sql, (version_id,))
            files_rows = cur.fetchall()

    if not files_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No files found for module version {slug}@{version}"
        )

    # Build ZIP archive in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files_rows:
            if isinstance(f, (list, tuple)):
                file_path, file_name, content = f[0], f[1], f[2]
            else:
                file_path = f.get("filePath") or f.get("filepath")
                content = f.get("content")
            clean_path = str(file_path).lstrip("/\\")
            zf.writestr(clean_path, content.encode("utf-8") if isinstance(content, str) else content)

    zip_bytes = zip_buffer.getvalue()
    filename = f"{slug}-{version}.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(zip_bytes)),
        }
    )

# 6. GET /api/modules/{slug}/versions
@router.get("/{slug}/versions")
def get_module_versions(slug: str):
    """
    Returns list of versions for a given module
    """
    try:
        sql = f"""
            SELECT 
                v.id, 
                v.version, 
                v.changelog, 
                v.{q("isLatest")} AS {q("isLatest")}, 
                v.status, 
                v.{q("createdAt")} AS {q("createdAt")}
            FROM module_versions v
            JOIN modules m ON v.{q("moduleId")} = m.id
            WHERE m.slug = %s
            ORDER BY v.{q("isLatest")} DESC, v.{q("createdAt")} DESC
        """
        with get_cursor() as cur:
            cur.execute(sql, (slug,))
            versions = cur.fetchall()

        return {
            "success": True,
            "data": [dict(v) for v in versions]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 7. GET /api/modules/{slug}/versions/{version}/files
@router.get("/{slug}/versions/{version}/files")
def get_module_version_files(slug: str, version: str):
    """
    Returns files list for a given version
    """
    try:
        sql = f"""
            SELECT 
                f.id, 
                f.{q("filePath")} AS {q("filePath")}, 
                f.{q("fileName")} AS {q("fileName")}, 
                f.language, 
                f.content, 
                f.{q("isEntry")} AS {q("isEntry")}
            FROM module_files f
            JOIN module_versions v ON f.{q("moduleVersionId")} = v.id
            JOIN modules m ON v.{q("moduleId")} = m.id
            WHERE m.slug = %s AND v.version = %s
            ORDER BY f.{q("isEntry")} DESC, f.{q("filePath")} ASC
        """
        with get_cursor() as cur:
            cur.execute(sql, (slug, version))
            files = cur.fetchall()

        return {
            "success": True,
            "data": [dict(f) for f in files]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 8. GET /api/modules/{slug}
@router.get("/{slug}")
def get_module_detail(slug: str):
    """
    Module detail page (source code viewer, documentation, versions)
    """
    try:
        with get_cursor() as cur:
            # 1. Fetch Module & Category
            module_sql = f"""
                SELECT 
                    m.id,
                    m.slug,
                    m.name,
                    m.{q("shortDescription")} AS {q("shortDescription")},
                    m.description,
                    m.{q("categoryId")} AS {q("categoryId")},
                    m.status,
                    m.framework,
                    m.language,
                    m.{q("downloadCount")} AS {q("downloadCount")},
                    m.{q("createdAt")} AS {q("createdAt")},
                    m.{q("updatedAt")} AS {q("updatedAt")},
                    c.id AS cat_id,
                    c.name AS cat_name,
                    c.slug AS cat_slug,
                    c.description AS cat_desc,
                    c.icon AS cat_icon
                FROM modules m
                LEFT JOIN categories c ON m.{q("categoryId")} = c.id
                WHERE m.slug = %s
                LIMIT 1
            """
            cur.execute(module_sql, (slug,))
            row = cur.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Module with slug '{slug}' not found"
                )

            module_item = dict(row)
            cat_id = module_item.pop("cat_id", None)
            cat_name = module_item.pop("cat_name", None)
            cat_slug = module_item.pop("cat_slug", None)
            cat_desc = module_item.pop("cat_desc", None)
            cat_icon = module_item.pop("cat_icon", None)
            module_item["category"] = {
                "id": cat_id,
                "name": cat_name,
                "slug": cat_slug,
                "description": cat_desc,
                "icon": cat_icon,
            } if cat_name else None

            category_id = module_item.get("categoryId") or module_item.get("categoryid")

            # 2. Fetch Versions
            versions_sql = f"""
                SELECT 
                    id,
                    {q("moduleId")} AS {q("moduleId")},
                    version,
                    changelog,
                    {q("isLatest")} AS {q("isLatest")},
                    status,
                    {q("createdAt")} AS {q("createdAt")}
                FROM module_versions
                WHERE {q("moduleId")} = %s
                ORDER BY {q("isLatest")} DESC, {q("createdAt")} DESC
            """
            cur.execute(versions_sql, (module_item["id"],))
            versions = [dict(v) for v in cur.fetchall()]

            # Find latest/current version
            current_ver = next((v for v in versions if v.get("isLatest") or v.get("islatest")), versions[0] if versions else None)
            current_version_with_files = None

            if current_ver:
                files_sql = f"""
                    SELECT 
                        id,
                        {q("filePath")} AS {q("filePath")},
                        {q("fileName")} AS {q("fileName")},
                        language,
                        content,
                        {q("isEntry")} AS {q("isEntry")}
                    FROM module_files
                    WHERE {q("moduleVersionId")} = %s
                    ORDER BY {q("isEntry")} DESC, {q("filePath")} ASC
                """
                cur.execute(files_sql, (current_ver["id"],))
                files = [dict(f) for f in cur.fetchall()]
                current_version_with_files = dict(current_ver)
                current_version_with_files["files"] = files

            # 3. Fetch Tags
            tags_sql = f"""
                SELECT t.id, t.slug, t.name
                FROM tags t
                JOIN module_tags mt ON t.id = mt.{q("tagId")}
                WHERE mt.{q("moduleId")} = %s
                ORDER BY t.name ASC
            """
            cur.execute(tags_sql, (module_item["id"],))
            tags = [dict(t) for t in cur.fetchall()]

            # 4. Related modules
            related_sql = f"""
                SELECT 
                    m.id,
                    m.slug,
                    m.name,
                    m.{q("shortDescription")} AS {q("shortDescription")},
                    m.framework,
                    m.language,
                    m.{q("downloadCount")} AS {q("downloadCount")}
                FROM modules m
                WHERE m.{q("categoryId")} = %s AND m.id != %s AND m.status = 'PUBLISHED'
                ORDER BY m.{q("downloadCount")} DESC
                LIMIT 4
            """
            cur.execute(related_sql, (category_id, module_item["id"]))
            related_modules = [dict(r) for r in cur.fetchall()]

        result = dict(module_item)
        result["latestVersion"] = current_ver["version"] if current_ver else "1.0.0"
        result["versions"] = versions
        result["currentVersion"] = current_version_with_files
        result["tags"] = tags
        result["relatedModules"] = related_modules

        return {
            "success": True,
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
