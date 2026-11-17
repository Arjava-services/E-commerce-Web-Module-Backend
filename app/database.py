import logging
import urllib.parse
from queue import Queue, Empty
from contextlib import contextmanager
from app.config import settings

logger = logging.getLogger(__name__)

is_mysql = settings.DATABASE_URL.startswith("mysql")

# Pool state
_pg_pool = None
_mysql_pool = None

class SimpleMySQLPool:
    def __init__(self, dsn: str, max_connections: int = 20):
        self.dsn = dsn
        self.max_connections = max_connections
        self.pool = Queue(maxsize=max_connections)
        self.created = 0
        self._parse_dsn(dsn)

    def _parse_dsn(self, dsn: str):
        # Format: mysql://user:password@host:port/dbname or mysql+pymysql://...
        clean_dsn = dsn.replace("mysql+pymysql://", "mysql://")
        parsed = urllib.parse.urlparse(clean_dsn)
        self.user = urllib.parse.unquote(parsed.username or "root")
        self.password = urllib.parse.unquote(parsed.password or "")
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 3306
        self.database = parsed.path.lstrip("/")

    def _create_connection(self):
        import pymysql
        from pymysql.cursors import DictCursor
        return pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            port=self.port,
            cursorclass=DictCursor,
            autocommit=False,
            charset="utf8mb4",
        )

    def get_connection(self):
        try:
            conn = self.pool.get_nowait()
            conn.ping(reconnect=True)
            return conn
        except Empty:
            if self.created < self.max_connections:
                self.created += 1
                return self._create_connection()
            return self.pool.get(block=True, timeout=10)

    def return_connection(self, conn):
        try:
            self.pool.put_nowait(conn)
        except Exception:
            conn.close()

    def closeall(self):
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except Exception:
                pass


def init_pool():
    global _pg_pool, _mysql_pool
    if is_mysql:
        if _mysql_pool is None:
            try:
                _mysql_pool = SimpleMySQLPool(settings.DATABASE_URL)
                logger.info("✅ MySQL connection pool initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize MySQL connection pool: {e}")
                raise e
    else:
        from psycopg2.pool import ThreadedConnectionPool
        if _pg_pool is None or getattr(_pg_pool, "closed", True):
            try:
                _pg_pool = ThreadedConnectionPool(
                    minconn=1,
                    maxconn=20,
                    dsn=settings.DATABASE_URL
                )
                logger.info("✅ PostgreSQL connection pool initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize PostgreSQL connection pool: {e}")
                raise e


def close_pool():
    global _pg_pool, _mysql_pool
    if _mysql_pool is not None:
        _mysql_pool.closeall()
        _mysql_pool = None
    if _pg_pool is not None and not getattr(_pg_pool, "closed", True):
        _pg_pool.closeall()
        _pg_pool = None


@contextmanager
def get_db():
    global _pg_pool, _mysql_pool
    if is_mysql:
        if _mysql_pool is None:
            init_pool()
        conn = _mysql_pool.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            _mysql_pool.return_connection(conn)
    else:
        if _pg_pool is None or getattr(_pg_pool, "closed", True):
            init_pool()
        conn = _pg_pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            if _pg_pool is not None and not getattr(_pg_pool, "closed", True):
                _pg_pool.putconn(conn)


@contextmanager
def get_cursor():
    with get_db() as conn:
        if is_mysql:
            with conn.cursor() as cur:
                yield cur
        else:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
