import logging
from contextlib import contextmanager
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize connection pool (minconn=1, maxconn=20)
pool: ThreadedConnectionPool = None

def init_pool():
    global pool
    if pool is None or getattr(pool, "closed", True):
        try:
            pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=settings.DATABASE_URL
            )
            logger.info("✅ PostgreSQL connection pool initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize connection pool: {e}")
            raise e

def close_pool():
    global pool
    if pool is not None and not getattr(pool, "closed", True):
        try:
            pool.closeall()
            logger.info("PostgreSQL connection pool closed")
        except Exception as e:
            logger.warning(f"Error closing connection pool: {e}")
        finally:
            pool = None

@contextmanager
def get_db():
    """
    Context manager yielding a database connection from the pool.
    Automatically handles commit and rollback.
    """
    global pool
    if pool is None or getattr(pool, "closed", True):
        init_pool()

    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        if pool is not None and not getattr(pool, "closed", True):
            pool.putconn(conn)

@contextmanager
def get_cursor():
    """
    Context manager yielding a RealDictCursor.
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
