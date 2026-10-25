from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from app.settings import settings

pool = ConnectionPool(settings.database_url, min_size=2, max_size=5, kwargs={"row_factory": dict_row}, open=True)


@contextmanager
def connect(owner_url=None):
    if owner_url:
        with psycopg.connect(owner_url, row_factory=dict_row) as conn:
            yield conn
    else:
        with pool.connection() as conn:
            yield conn


def one(conn, query, params=()):
    return conn.execute(query, params).fetchone()


def many(conn, query, params=()):
    return conn.execute(query, params).fetchall()
