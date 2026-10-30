import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PORT: int = int(os.getenv("PORT", "4000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://hope3services@localhost:5432/moduleforge")
    CORS_ORIGIN: str = os.getenv("CORS_ORIGIN", "*")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

settings = Settings()

