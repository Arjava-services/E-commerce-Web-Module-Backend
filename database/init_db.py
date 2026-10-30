import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://hope3services@localhost:5432/moduleforge")

def init_db():
    print("🔄 Initializing PostgreSQL database schema...")
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        print("✅ Database schema initialized successfully.")
    except Exception as e:
        print(f"❌ Error initializing schema: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()

