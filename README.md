# E-Commerce Web Module Platform Backend (FastAPI)

A high-performance REST API backend powering the E-Commerce Web Module Platform catalogue, source code viewer, documentation viewer, upload registry, and zip downloader.

Built with **Python 3.9+**, **FastAPI**, **Uvicorn**, and database compatibility for **PostgreSQL** and **MySQL (`Arjava_module`)**.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python >= 3.9
- PostgreSQL >= 13 OR MySQL >= 8.0

### 2. Setup Virtual Environment
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env`:
```env
PORT=4000
HOST=0.0.0.0
# For PostgreSQL:
DATABASE_URL=postgresql://hope3services@localhost:5432/moduleforge
# For MySQL (e.g. Arjava_module):
# DATABASE_URL=mysql+pymysql://arjava_module:YOUR_PASSWORD@localhost:3306/Arjava_module
CORS_ORIGIN=*
ENVIRONMENT=development
```

### 4. Run the Server
```bash
# Activate virtual environment
source venv/bin/activate

# Start server
python main.py

# Or with uvicorn directly:
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

Interactive Documentation:
- **Swagger UI**: [http://localhost:4000/docs](http://localhost:4000/docs)
- **ReDoc**: [http://localhost:4000/redoc](http://localhost:4000/redoc)

### 5. Run Automated Tests
```bash
pytest tests/ -v
```

---

## 📡 The 8 REST API Endpoints

All responses follow the standard response envelope:
```json
{
  "success": true,
  "data": ...
}
```

### 1. `GET /api/categories`
- **Purpose**: Navigation sidebar, categories page, and module upload dropdown.
- **Response**: Array of categories `{ id, slug, name, description, icon, displayOrder, moduleCount }`.

### 2. `GET /api/modules`
- **Purpose**: Main catalog page searching, filtering, sorting, and pagination.
- **Query Params**: `search`, `category`, `framework`, `sort` ("updated", "alphabetical", "downloads", "views"), `page` (default: 1), `limit` (default: 12).
- **Response**: `{ total, page, totalPages, limit, items: [ ModuleSummary ] }`.

### 3. `GET /api/modules/:slug`
- **Purpose**: Module detail page (live preview, documentation tabs, source code, historical versions).
- **Response**: Full module object including `currentVersion.files`, `tags`, `category`, `documentation` (`overview`, `installation`, `apiReference`, `integrationExample`), and `relatedModules`.

### 4. `POST /api/modules`
- **Purpose**: Upload and publish a new module or version from `/upload`.
- **Payload**:
  ```json
  {
    "name": "Custom Cart Drawer",
    "slug": "custom-cart-drawer",
    "categoryId": "cat-id-or-slug",
    "shortDescription": "Slide-over shopping cart drawer component.",
    "description": "Full markdown overview.",
    "framework": "React",
    "language": "TypeScript",
    "version": "1.0.0",
    "tags": ["cart", "ui", "drawer"],
    "files": [
      {
        "fileName": "CartDrawer.tsx",
        "filePath": "src/CartDrawer.tsx",
        "content": "export function CartDrawer() { ... }",
        "language": "typescript",
        "isEntry": true
      }
    ],
    "overview": "Overview text...",
    "installation": "npm install @company/custom-cart-drawer",
    "apiReference": "import { CartDrawer } from '@company/custom-cart-drawer';",
    "integrationExample": "<CartDrawer isOpen={true} />"
  }
  ```
- **Response**: `{ "id": "...", "slug": "custom-cart-drawer", "name": "Custom Cart Drawer" }` with HTTP `201 Created`.

### 5. `GET /api/modules/:slug/versions/:version/files`
- **Purpose**: Code viewer when selecting a specific historical release version.
- **Response**: Array of `ModuleFile` (`id`, `filePath`, `fileName`, `language`, `isEntry`, `content`).

### 6. `GET /api/modules/:slug/versions/:version/download`
- **Purpose**: Download package ZIP button.
- **Response**: Binary Stream (`application/zip`) with header `Content-Disposition: attachment; filename="<slug>-<version>.zip"`.
- **Behavior**: Automatically increments `downloadCount` on the module.

### 7. `GET /api/modules/stats`
- **Purpose**: Home page statistics counter.
- **Response**: `{ "publishedModules": 122, "totalDownloads": 780 }`.

### 8. `GET /api/modules/featured`
- **Purpose**: Home page featured showcase section.
- **Response**: Array of top 4 to 8 `ModuleSummary` objects (with `category` and `tags`).
