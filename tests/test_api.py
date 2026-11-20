import pytest
import time
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client

# -----------------------------------------------------------------------------
# 1. GET /api/categories
# -----------------------------------------------------------------------------
def test_1_get_categories(client):
    res = client.get("/api/categories")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    categories = body["data"]
    assert isinstance(categories, list)
    assert len(categories) > 0
    cat = categories[0]
    assert "id" in cat
    assert "slug" in cat
    assert "name" in cat
    assert "description" in cat
    assert "icon" in cat
    assert "displayOrder" in cat
    assert isinstance(cat["displayOrder"], int)

# -----------------------------------------------------------------------------
# 2. GET /api/modules
# -----------------------------------------------------------------------------
def test_2_get_modules_paginated(client):
    res = client.get("/api/modules?page=1&limit=6&sort=updated")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert "total" in data
    assert "page" in data
    assert "totalPages" in data
    assert "limit" in data
    assert data["page"] == 1
    assert data["limit"] == 6
    assert isinstance(data["items"], list)
    if data["items"]:
        item = data["items"][0]
        assert "id" in item
        assert "slug" in item
        assert "name" in item
        assert "framework" in item
        assert "language" in item
        assert "status" in item
        assert "latestVersion" in item
        assert "downloadCount" in item
        assert "category" in item
        assert "tags" in item
        assert isinstance(item["tags"], list)

# -----------------------------------------------------------------------------
# 4. POST /api/modules (Upload / Publish Module)
# -----------------------------------------------------------------------------
test_module_slug = f"custom-cart-drawer-{int(time.time())}"

def test_4_publish_module(client):
    # Fetch a category first
    cat_res = client.get("/api/categories")
    category_id = cat_res.json()["data"][0]["id"]

    payload = {
        "name": "Custom Cart Drawer",
        "slug": test_module_slug,
        "categoryId": category_id,
        "shortDescription": "A sleek slide-over shopping cart drawer component with quantity controls.",
        "description": "Full markdown overview detailing features and component props.",
        "framework": "React",
        "language": "TypeScript",
        "version": "1.0.0",
        "tags": ["cart", "ui", "drawer"],
        "files": [
            {
                "fileName": "CartDrawer.tsx",
                "filePath": "src/CartDrawer.tsx",
                "content": "export function CartDrawer() { return <div className='drawer'>Cart</div>; }",
                "language": "typescript",
                "isEntry": True
            },
            {
                "fileName": "types.ts",
                "filePath": "src/types.ts",
                "content": "export interface CartItem { id: string; price: number; }",
                "language": "typescript",
                "isEntry": False
            }
        ],
        "overview": "Complete slide-over cart with subtotal calculation.",
        "installation": f"npm install @company/{test_module_slug}",
        "apiReference": f"import {{ CartDrawer }} from '@company/{test_module_slug}';",
        "integrationExample": "<CartDrawer isOpen={true} />"
    }

    res = client.post("/api/modules", json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    assert body["data"]["slug"] == test_module_slug
    assert body["data"]["name"] == "Custom Cart Drawer"
    assert "id" in body["data"]

# -----------------------------------------------------------------------------
# 3. GET /api/modules/:slug
# -----------------------------------------------------------------------------
def test_3_get_module_detail(client):
    res = client.get(f"/api/modules/{test_module_slug}")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    detail = body["data"]
    assert detail["slug"] == test_module_slug
    assert detail["name"] == "Custom Cart Drawer"
    assert detail["framework"] == "React"
    assert detail["language"] == "TypeScript"
    assert "category" in detail
    assert "tags" in detail
    assert len(detail["tags"]) == 3
    assert detail["currentVersion"] is not None
    assert detail["currentVersion"]["version"] == "1.0.0"
    assert len(detail["currentVersion"]["files"]) == 2
    assert detail["currentVersion"]["files"][0]["fileName"] == "CartDrawer.tsx"
    assert detail["currentVersion"]["files"][0]["isEntry"] is True
    # Documentation object
    assert "documentation" in detail
    assert detail["documentation"] is not None
    assert f"npm install @company/{test_module_slug}" in detail["documentation"]["installation"]

# -----------------------------------------------------------------------------
# 5. GET /api/modules/:slug/versions/:version/files
# -----------------------------------------------------------------------------
def test_5_get_version_files(client):
    res = client.get(f"/api/modules/{test_module_slug}/versions/1.0.0/files")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    files = body["data"]
    assert isinstance(files, list)
    assert len(files) == 2
    assert files[0]["fileName"] == "CartDrawer.tsx"
    assert "content" in files[0]
    assert files[0]["isEntry"] is True

# -----------------------------------------------------------------------------
# 6. GET /api/modules/:slug/versions/:version/download
# -----------------------------------------------------------------------------
def test_6_download_module_zip(client):
    res = client.get(f"/api/modules/{test_module_slug}/versions/1.0.0/download")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert f'{test_module_slug}-1.0.0.zip' in res.headers["content-disposition"]
    assert len(res.content) > 50

    # Verify download count incremented
    detail_res = client.get(f"/api/modules/{test_module_slug}")
    assert detail_res.json()["data"]["downloadCount"] == 1

# -----------------------------------------------------------------------------
# 7. GET /api/modules/stats
# -----------------------------------------------------------------------------
def test_7_get_stats(client):
    res = client.get("/api/modules/stats")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    stats = body["data"]
    assert "publishedModules" in stats
    assert "totalDownloads" in stats
    assert isinstance(stats["publishedModules"], int)
    assert isinstance(stats["totalDownloads"], int)

# -----------------------------------------------------------------------------
# 8. GET /api/modules/featured
# -----------------------------------------------------------------------------
def test_8_get_featured(client):
    res = client.get("/api/modules/featured")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    items = body["data"]
    assert isinstance(items, list)
    assert len(items) <= 8
    if items:
        f = items[0]
        assert "id" in f
        assert "slug" in f
        assert "name" in f
        assert "downloadCount" in f
        assert "category" in f
        assert "tags" in f
