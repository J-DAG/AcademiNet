import os
from contextlib import contextmanager
from dotenv import load_dotenv
import psycopg
import psycopg_pool
from psycopg.rows import dict_row

load_dotenv()

_conninfo = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'academinet')} "
    f"user={os.getenv('DB_USER', 'postgres')} "
    f"password={os.getenv('DB_PASSWORD', '')}"
)

_pool: psycopg_pool.ConnectionPool | None = None


def get_pool() -> psycopg_pool.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg_pool.ConnectionPool(
            conninfo=_conninfo,
            min_size=2,
            max_size=20,
            open=True,
        )
    return _pool


def close_pool() -> None:
    """Cierra limpiamente los workers del pool al apagar la aplicación."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_conn():
    with get_pool().connection() as conn:
        yield conn


@contextmanager
def get_cursor():
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur


def init_db():
    """Ejecuta todos los scripts SQL de inicialización en orden."""
    sql_dir = os.path.join(os.path.dirname(__file__), "..", "database")
    scripts = sorted([
        f for f in os.listdir(sql_dir)
        if f.endswith(".sql")
    ])
    with get_pool().connection() as conn:
        for script in scripts:
            path = os.path.join(sql_dir, script)
            with open(path, "r", encoding="utf-8") as f:
                sql = f.read()
            conn.execute(sql)
        conn.commit()
    return scripts
