import pytest
import time
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"
    assert data["data"]["database"] == "connected"

def test_get_categories(client):
    res = client.get("/api/categories")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
    first_cat = data["data"][0]
    assert "slug" in first_cat
    assert "name" in first_cat
    assert "displayOrder" in first_cat

def test_get_modules_stats(client):
    res = client.get("/api/modules/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "publishedModules" in data["data"]
    assert "totalDownloads" in data["data"]
    assert isinstance(data["data"]["publishedModules"], int)
    assert isinstance(data["data"]["totalDownloads"], int)

def test_list_modules_pagination_and_filters(client):
    res = client.get("/api/modules?page=1&limit=6&sort=updated")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    result = data["data"]
    assert "items" in result
    assert "total" in result
    assert "page" in result
    assert result["page"] == 1
    assert isinstance(result["items"], list)

def test_publish_and_retrieve_module(client):
    test_slug = f"fastapi-test-module-{int(time.time())}"
    cat_res = client.get("/api/categories")
    first_category_id = cat_res.json()["data"][0]["id"]

    payload = {
        "name": "FastAPI Shopping Drawer",
        "slug": test_slug,
        "categoryId": first_category_id,
        "shortDescription": "High-performance cart drawer created via FastAPI backend",
        "description": "Full documentation for shopping drawer component.",
        "framework": "React",
        "language": "TypeScript",
        "version": "1.0.0",
        "tags": ["react", "fastapi", "cart"],
        "files": [
            {
                "fileName": "Drawer.tsx",
                "filePath": "src/Drawer.tsx",
                "content": "export function Drawer() { return <div>Drawer</div>; }",
                "language": "typescript",
                "isEntry": True
            },
            {
                "fileName": "types.ts",
                "filePath": "src/types.ts",
                "content": "export interface DrawerProps { open: boolean; }",
                "language": "typescript",
                "isEntry": False
            }
        ]
    }

    # 1. Publish Module (POST /api/modules)
    post_res = client.post("/api/modules", json=payload)
    assert post_res.status_code == 201
    post_data = post_res.json()
    assert post_data["success"] is True
    assert post_data["data"]["slug"] == test_slug
    assert "id" in post_data["data"]

    # 2. Get Module Detail (GET /api/modules/:slug)
    get_res = client.get(f"/api/modules/{test_slug}")
    assert get_res.status_code == 200
    detail = get_res.json()["data"]
    assert detail["slug"] == test_slug
    assert detail["name"] == "FastAPI Shopping Drawer"
    assert detail["currentVersion"] is not None
    assert len(detail["currentVersion"]["files"]) == 2
    assert detail["currentVersion"]["files"][0]["fileName"] == "Drawer.tsx"

    # 3. Download ZIP (GET /api/modules/:slug/versions/:version/download)
    dl_res = client.get(f"/api/modules/{test_slug}/versions/1.0.0/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/zip"
    assert "attachment;" in dl_res.headers["content-disposition"]
    assert len(dl_res.content) > 50

    # 4. Verify Download Count incremented
    after_dl = client.get(f"/api/modules/{test_slug}").json()["data"]
    assert after_dl["downloadCount"] == 1
