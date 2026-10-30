# E-Commerce Web Module Platform Backend (FastAPI)

A high-performance REST API backend powering the E-Commerce Web Module Platform catalogue, source code viewer, upload registry, and zip downloader.

Built with **Python 3.9+**, **FastAPI**, **Uvicorn**, and **PostgreSQL (`psycopg2-binary`)**.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python >= 3.9
- PostgreSQL >= 13

### 2. Setup Virtual Environment
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` and configure your PostgreSQL database connection:
```env
PORT=4000
HOST=0.0.0.0
DATABASE_URL=postgresql://username:password@localhost:5432/moduleforge
CORS_ORIGIN=*
ENVIRONMENT=development
```

### 4. Initialize Database & Seed
```bash
# Creates the 5 core tables and indexes
python database/init_db.py

# Optional: seed categories and sample modules
python database/seed_db.py
```

### 5. Run the Server
```bash
# Run with Python
python main.py

# Or directly with Uvicorn
uvicorn app.main:app --reload --port 4000 --host 0.0.0.0
```

Interactive API documentation will be available at:
- Swagger UI: `http://localhost:4000/docs`
- ReDoc: `http://localhost:4000/redoc`

### 6. Run Automated Tests
```bash
pytest tests/ -v
```

---

## 🗄️ Minimal Database Schema (5 Core Tables)

The platform is designed around 5 core relational tables:

1. **`categories`**
   - Stores catalog categories for module classification and navigation.
   - Fields: `id`, `slug`, `name`, `description`, `icon`, `displayOrder`, `createdAt`, `updatedAt`.
2. **`modules`**
   - Core module entity containing metadata, category linkage, framework, and metrics.
   - Fields: `id`, `slug`, `name`, `shortDescription`, `description`, `categoryId`, `status`, `framework`, `language`, `downloadCount`, `createdAt`, `updatedAt`.
3. **`module_versions`**
   - Semantic versions for each module with changelog and active/latest flag.
   - Fields: `id`, `moduleId`, `version`, `changelog`, `isLatest`, `status`, `createdAt`, `updatedAt`.
4. **`module_files`**
   - Source code files belonging to a specific module version.
   - Fields: `id`, `moduleVersionId`, `filePath`, `fileName`, `language`, `content`, `isEntry`, `createdAt`.
5. **`tags` & `module_tags`**
   - Multi-tag categorization system.
   - `tags`: `id`, `slug`, `name`, `createdAt`.
   - `module_tags`: `moduleId`, `tagId` (Composite PK).

---

## 📡 REST API Endpoints

All responses follow the standard JSON response format expected by the frontend:
```json
{
  "success": true,
  "data": ...
}
```

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/categories` | Returns catalog categories for sidebar & forms |
| `GET` | `/api/modules` | Query catalog with filters (`page`, `limit`, `category`, `framework`, `search`, `sort`) |
| `GET` | `/api/modules/:slug` | Full module details, versions, tags, and current version source files |
| `POST` | `/api/modules` | Upload / publish new module or version with source files |
| `GET` | `/api/modules/:slug/versions/:version/download` | Downloads streamed ZIP package and increments download count |
| `GET` | `/api/modules/stats` | Platform totals (`publishedModules`, `totalDownloads`) |
| `GET` | `/api/modules/featured` | Top downloaded / featured modules |
| `GET` | `/api/health` | Service health status & database connectivity |
