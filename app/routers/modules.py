import io
import re
import math
import zipfile
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from app.database import get_db, get_cursor
from app.schemas import ModuleUploadPayload

router = APIRouter(prefix="/modules", tags=["Modules"])

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
        sql = """
            SELECT 
                COUNT(id)::int AS "publishedModules",
                COALESCE(SUM("downloadCount"), 0)::int AS "totalDownloads"
            FROM modules
            WHERE status = 'PUBLISHED'
        """
        with get_cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()

        return {
            "success": True,
            "data": {
                "publishedModules": row["publishedModules"] if row else 0,
                "totalDownloads": row["totalDownloads"] if row else 0,
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
        sql = """
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
        """
        with get_cursor() as cur:
            cur.execute(sql)
            items = cur.fetchall()

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
            conditions.append('(c.slug = %s OR m."categoryId" = %s)')
            values.extend([category, category])

        # Framework filter
        if framework and framework != "all":
            conditions.append("m.framework ILIKE %s")
            values.append(framework)

        # Search filter
        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append('(m.name ILIKE %s OR m."shortDescription" ILIKE %s OR m.description ILIKE %s OR m.slug ILIKE %s)')
            values.extend([term, term, term, term])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Order by
        order_by = 'm."updatedAt" DESC'
        if sort == "downloads":
            order_by = 'm."downloadCount" DESC, m."updatedAt" DESC'
        elif sort == "newest":
            order_by = 'm."createdAt" DESC'
        elif sort == "name":
            order_by = "m.name ASC"
        elif sort == "updated":
            order_by = 'm."updatedAt" DESC'

        with get_cursor() as cur:
            # Count total
            count_sql = f"""
                SELECT COUNT(m.id)::int AS total
                FROM modules m
                LEFT JOIN categories c ON m."categoryId" = c.id
                {where_clause}
            """
            cur.execute(count_sql, values)
            total = cur.fetchone()["total"]
            total_pages = math.ceil(total / limit) if total > 0 else 1

            # Fetch items
            data_sql = f"""
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
                {where_clause}
                ORDER BY {order_by}
                LIMIT %s OFFSET %s
            """
            cur.execute(data_sql, values + [limit, offset])
            items = cur.fetchall()

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
        slug = f"module-{int(io.time.time())}"

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
                cur.execute('SELECT id FROM categories ORDER BY "displayOrder" ASC LIMIT 1')
                first_cat = cur.fetchone()
                if not first_cat:
                    raise HTTPException(status_code=400, detail="No categories exist in database")
                category_id = first_cat[0]
            else:
                category_id = cat_row[0]

            # 2. Upsert Module
            upsert_module_sql = """
                INSERT INTO modules (
                    id, slug, name, "shortDescription", description, "categoryId", 
                    status, framework, language, "updatedAt"
                )
                VALUES (
                    gen_random_uuid()::text, %s, %s, %s, %s, %s, 
                    'PUBLISHED', %s, %s, CURRENT_TIMESTAMP
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
            """
            cur.execute(upsert_module_sql, (
                slug,
                payload.name,
                short_desc,
                desc,
                category_id,
                payload.framework,
                payload.language,
            ))
            mod_row = cur.fetchone()
            module_id, module_slug = mod_row[0], mod_row[1]

            # 3. Mark previous versions isLatest = False
            cur.execute(
                'UPDATE module_versions SET "isLatest" = false WHERE "moduleId" = %s',
                (module_id,)
            )

            # 4. Upsert Version
            upsert_version_sql = """
                INSERT INTO module_versions (
                    id, "moduleId", version, changelog, "isLatest", status, "updatedAt"
                )
                VALUES (
                    gen_random_uuid()::text, %s, %s, %s, true, 'PUBLISHED', CURRENT_TIMESTAMP
                )
                ON CONFLICT ("moduleId", version) DO UPDATE SET
                    changelog = EXCLUDED.changelog,
                    "isLatest" = true,
                    status = 'PUBLISHED',
                    "updatedAt" = CURRENT_TIMESTAMP
                RETURNING id;
            """
            cur.execute(upsert_version_sql, (
                module_id,
                payload.version,
                f"Release {payload.version}",
            ))
            version_id = cur.fetchone()[0]

            # 5. Insert files
            cur.execute('DELETE FROM module_files WHERE "moduleVersionId" = %s', (version_id,))
            insert_file_sql = """
                INSERT INTO module_files (
                    id, "moduleVersionId", "filePath", "fileName", language, content, "isEntry"
                )
                VALUES (
                    gen_random_uuid()::text, %s, %s, %s, %s, %s, %s
                );
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
                    cur.execute(
                        """
                        INSERT INTO tags (id, slug, name) 
                        VALUES (gen_random_uuid()::text, %s, %s)
                        ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                        RETURNING id;
                        """,
                        (tag_slug, tag_name)
                    )
                    tag_id = cur.fetchone()[0]
                    cur.execute(
                        """
                        INSERT INTO module_tags ("moduleId", "tagId")
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING;
                        """,
                        (module_id, tag_id)
                    )

    return {
        "success": True,
        "data": {
            "id": module_id,
            "slug": module_slug,
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
            sql = """
                SELECT 
                    m.id AS "moduleId",
                    m.slug,
                    m.name,
                    v.id AS "versionId",
                    v.version
                FROM modules m
                JOIN module_versions v ON m.id = v."moduleId"
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
            module_id, version_id = item[0], item[3]

            # Increment download count
            cur.execute(
                'UPDATE modules SET "downloadCount" = "downloadCount" + 1 WHERE id = %s',
                (module_id,)
            )

            # Get files
            files_sql = """
                SELECT "filePath", "fileName", content
                FROM module_files
                WHERE "moduleVersionId" = %s
                ORDER BY "filePath" ASC
            """
            cur.execute(files_sql, (version_id,))
            files = cur.fetchall()

    if not files:
        raise HTTPException(
            status_code=404,
            detail=f"No files found for module version {slug}@{version}"
        )

    # Build ZIP archive in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, file_name, content in files:
            clean_path = file_path.lstrip("/\\")
            zf.writestr(clean_path, content.encode("utf-8"))

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
        sql = """
            SELECT v.id, v.version, v.changelog, v."isLatest", v.status, v."createdAt"
            FROM module_versions v
            JOIN modules m ON v."moduleId" = m.id
            WHERE m.slug = %s
            ORDER BY v."isLatest" DESC, v."createdAt" DESC
        """
        with get_cursor() as cur:
            cur.execute(sql, (slug,))
            versions = cur.fetchall()

        return {
            "success": True,
            "data": versions
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
        sql = """
            SELECT f.id, f."filePath", f."fileName", f.language, f.content, f."isEntry"
            FROM module_files f
            JOIN module_versions v ON f."moduleVersionId" = v.id
            JOIN modules m ON v."moduleId" = m.id
            WHERE m.slug = %s AND v.version = %s
            ORDER BY f."isEntry" DESC, f."filePath" ASC
        """
        with get_cursor() as cur:
            cur.execute(sql, (slug, version))
            files = cur.fetchall()

        return {
            "success": True,
            "data": files
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
            module_sql = """
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
                WHERE m.slug = %s
                LIMIT 1
            """
            cur.execute(module_sql, (slug,))
            module_item = cur.fetchone()

            if not module_item:
                raise HTTPException(
                    status_code=404,
                    detail=f"Module with slug '{slug}' not found"
                )

            # 2. Fetch Versions
            versions_sql = """
                SELECT 
                    id,
                    "moduleId",
                    version,
                    changelog,
                    "isLatest",
                    status,
                    "createdAt"
                FROM module_versions
                WHERE "moduleId" = %s
                ORDER BY "isLatest" DESC, "createdAt" DESC
            """
            cur.execute(versions_sql, (module_item["id"],))
            versions = cur.fetchall()

            # Find latest/current version
            current_ver = next((v for v in versions if v["isLatest"]), versions[0] if versions else None)
            current_version_with_files = None

            if current_ver:
                files_sql = """
                    SELECT 
                        id,
                        "filePath",
                        "fileName",
                        language,
                        content,
                        "isEntry"
                    FROM module_files
                    WHERE "moduleVersionId" = %s
                    ORDER BY "isEntry" DESC, "filePath" ASC
                """
                cur.execute(files_sql, (current_ver["id"],))
                files = cur.fetchall()
                current_version_with_files = dict(current_ver)
                current_version_with_files["files"] = files

            # 3. Fetch Tags
            tags_sql = """
                SELECT t.id, t.slug, t.name
                FROM tags t
                JOIN module_tags mt ON t.id = mt."tagId"
                WHERE mt."moduleId" = %s
                ORDER BY t.name ASC
            """
            cur.execute(tags_sql, (module_item["id"],))
            tags = cur.fetchall()

            # 4. Related modules
            related_sql = """
                SELECT 
                    m.id,
                    m.slug,
                    m.name,
                    m."shortDescription",
                    m.framework,
                    m.language,
                    m."downloadCount"
                FROM modules m
                WHERE m."categoryId" = %s AND m.id != %s AND m.status = 'PUBLISHED'
                ORDER BY m."downloadCount" DESC
                LIMIT 4
            """
            cur.execute(related_sql, (module_item["categoryId"], module_item["id"]))
            related_modules = cur.fetchall()

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

