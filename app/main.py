from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_pool, close_pool, get_cursor
from app.routers import categories, modules

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_pool()
    yield
    # Shutdown
    close_pool()

app = FastAPI(
    title="E-Commerce Web Module Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS setup
origins = (
    [origin.strip() for origin in settings.CORS_ORIGIN.split(",")]
    if settings.CORS_ORIGIN != "*"
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Error Handlers for consistent frontend response format
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "error": "Validation error", "details": exc.errors()},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": str(exc)},
    )

# Root route
@app.get("/")
def root():
    return {
        "name": "E-Commerce Web Module Platform API",
        "version": "1.0.0",
        "framework": "FastAPI",
        "status": "online",
        "docs": "/docs",
    }

# Health check
@app.get("/api/health")
def health():
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1 as connected")
            connected = cur.fetchone() is not None
        return {
            "success": True,
            "data": {
                "status": "ok",
                "database": "connected" if connected else "disconnected"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"success": False, "error": f"Database error: {str(e)}"}
        )

# Technologies route (for frontend compatibility)
@app.get("/api/technologies")
def get_technologies():
    try:
        sql = """
            SELECT DISTINCT framework AS name, 'FRONTEND' AS category 
            FROM modules 
            WHERE framework IS NOT NULL AND framework != ''
            UNION
            SELECT DISTINCT language AS name, 'FRONTEND' AS category 
            FROM modules 
            WHERE language IS NOT NULL AND language != ''
        """
        with get_cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

        tech_list = [
            {
                "id": r["name"].lower(),
                "slug": r["name"].lower(),
                "name": r["name"],
                "category": r["category"],
                "icon": None,
            }
            for r in rows
        ]
        return {"success": True, "data": tech_list}
    except Exception:
        return {
            "success": True,
            "data": [
                {"id": "react", "slug": "react", "name": "React", "category": "FRONTEND", "icon": None},
                {"id": "typescript", "slug": "typescript", "name": "TypeScript", "category": "FRONTEND", "icon": None},
                {"id": "nodejs", "slug": "nodejs", "name": "Node.js", "category": "BACKEND", "icon": None},
            ]
        }

# Mount core routers under /api
app.include_router(categories.router, prefix="/api")
app.include_router(modules.router, prefix="/api")

