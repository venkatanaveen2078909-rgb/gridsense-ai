"""
GRIDSENSE DB Layer — Phase 3 (Multi-Tenant) with SQLite fallback for local dev.
When DATABASE_URL is set to a postgres:// URL and the server is reachable, uses PostgreSQL (Phase 2+).
When running locally without Docker, falls back to SQLite automatically.
"""
import os
import json
import sqlite3
from contextlib import contextmanager
from app.logging_config import get_logger

log = get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_PATH      = os.getenv("GRIDSENSE_DB_PATH",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gridsense_live.db"))

# Detect backend
_use_postgres = DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")
_pool = None

# ── PostgreSQL ────────────────────────────────────────────────────────────────
POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    api_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS telemetry (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    asset_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    metrics_json JSONB NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_tel_unproc ON telemetry(processed) WHERE processed = FALSE;
CREATE INDEX IF NOT EXISTS idx_tel_asset ON telemetry(tenant_id, asset_id);
CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asset_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    rule TEXT NOT NULL,
    status TEXT NOT NULL,
    first_seen TIMESTAMP WITH TIME ZONE NOT NULL,
    last_seen TIMESTAMP WITH TIME ZONE NOT NULL,
    work_order_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_inc_active ON incidents(tenant_id, asset_id, rule, status);
CREATE TABLE IF NOT EXISTS work_orders (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    incident_id INTEGER NOT NULL REFERENCES incidents(id),
    asset_id TEXT NOT NULL,
    rule TEXT NOT NULL,
    severity TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence REAL NOT NULL,
    data_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE TABLE IF NOT EXISTS plant_state (
    tenant_id TEXT PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    grid_available BOOLEAN NOT NULL DEFAULT TRUE,
    plant_status TEXT NOT NULL DEFAULT 'RUNNING',
    assets_in_maintenance JSONB NOT NULL DEFAULT '[]'::jsonb,
    shut_down_assets JSONB NOT NULL DEFAULT '[]'::jsonb
);
CREATE TABLE IF NOT EXISTS webhooks (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    events TEXT NOT NULL DEFAULT 'ALL',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

# ── SQLite ────────────────────────────────────────────────────────────────────
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    api_key TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    processed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tel_unproc ON telemetry(processed) WHERE processed=0;
CREATE INDEX IF NOT EXISTS idx_tel_asset ON telemetry(tenant_id, asset_id);
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    rule TEXT NOT NULL,
    status TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    work_order_id TEXT
);
CREATE TABLE IF NOT EXISTS work_orders (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    incident_id INTEGER NOT NULL,
    asset_id TEXT NOT NULL,
    rule TEXT NOT NULL,
    severity TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence REAL NOT NULL,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plant_state (
    tenant_id TEXT PRIMARY KEY,
    grid_available INTEGER NOT NULL DEFAULT 1,
    plant_status TEXT NOT NULL DEFAULT 'RUNNING',
    assets_in_maintenance TEXT NOT NULL DEFAULT '[]',
    shut_down_assets TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    events TEXT NOT NULL DEFAULT 'ALL',
    created_at TEXT DEFAULT (datetime('now'))
);
"""

def _init_postgres_pool():
    global _pool
    if _pool is not None:
        return
    from psycopg2.pool import ThreadedConnectionPool
    _pool = ThreadedConnectionPool(1, 20, dsn=DATABASE_URL)
    log.info("PostgreSQL pool initialized")

class _PgWrapper:
    """Thin wrapper to unify psycopg2 and sqlite3 interfaces."""
    def __init__(self, conn, cur):
        self.c  = conn
        self.cu = cur
        self._last_rowid = None

    def execute(self, query, params=None):
        q = query.replace("?", "%s")
        self.cu.execute(q, params)
        return self.cu

    def fetchone(self):  return self.cu.fetchone()
    def fetchall(self):  return self.cu.fetchall()
    def commit(self):    self.c.commit()
    def executescript(self, s): self.cu.execute(s)

class _SqliteWrapper:
    def __init__(self, conn, cur):
        self.c  = conn
        self.cu = cur

    def execute(self, query, params=None):
        # Convert %s → ? and RETURNING id (not supported in SQLite 3.35-)
        q = query.replace("%s", "?")
        # Strip RETURNING clause — we'll use lastrowid instead
        import re
        q = re.sub(r'\s+RETURNING\s+\w+', '', q, flags=re.IGNORECASE)
        self.cu.execute(q, params or ())
        return self.cu

    def fetchone(self):
        row = self.cu.fetchone()
        if row is None: return None
        # Wrap as dict-like (sqlite3.Row already is)
        return row

    def fetchall(self):  return self.cu.fetchall()
    def commit(self):    self.c.commit()
    def executescript(self, s): self.c.executescript(s)

    @property
    def lastrowid(self): return self.cu.lastrowid

@contextmanager
def get_db():
    if _use_postgres:
        from psycopg2.extras import RealDictCursor
        _init_postgres_pool()
        conn = _pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield _PgWrapper(conn, cur)
        except Exception:
            conn.rollback(); raise
        finally:
            _pool.putconn(conn)
    else:
        conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            cur = conn.cursor()
            yield _SqliteWrapper(conn, cur)
        except Exception:
            conn.rollback(); raise
        finally:
            conn.close()

def init_db():
    import time
    retries = 5
    for attempt in range(retries):
        try:
            with get_db() as conn:
                schema = POSTGRES_SCHEMA if _use_postgres else SQLITE_SCHEMA
                conn.executescript(schema)
                conn.commit()
            seed_db()
            log.info("Database schema initialized", extra={"backend": "postgres" if _use_postgres else "sqlite"})
            return
        except Exception as e:
            if attempt < retries - 1:
                log.warning("DB not ready, retrying…", extra={"attempt": attempt+1, "error": str(e)})
                time.sleep(2)
            else:
                log.error("Failed to init DB", extra={"error": str(e)})

def seed_db():
    import bcrypt
    with get_db() as conn:
        res = conn.execute("SELECT COUNT(*) as c FROM tenants").fetchone()
        if (res["c"] if isinstance(res, dict) else res[0]) > 0:
            return

        tenants = [
            ("aerowind", "AeroWind Corp",  "key-aerowind"),
            ("solaris",  "Solaris Energy", "key-solaris"),
        ]
        for tid, tname, tkey in tenants:
            conn.execute(
                "INSERT INTO tenants (id, name, api_key) VALUES (?, ?, ?)",
                (tid, tname, tkey)
            )
            # Seed 3 users per tenant — Admin, Operator, Viewer
            for email, role in [
                (f"admin@{tid}.com",    "Admin"),
                (f"operator@{tid}.com", "Operator"),
                (f"viewer@{tid}.com",   "Viewer"),
            ]:
                pw_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
                conn.execute(
                    "INSERT INTO users (tenant_id, email, password_hash, role) VALUES (?, ?, ?, ?)",
                    (tid, email, pw_hash, role)
                )
            conn.execute("INSERT INTO plant_state (tenant_id) VALUES (?)", (tid,))
        conn.commit()
        log.info("Seeded tenants: AeroWind Corp, Solaris Energy — Admin/Operator/Viewer users (password: password123)")

# Auto-init connection pool if using postgres
if _use_postgres:
    try:
        _init_postgres_pool()
    except Exception as e:
        log.warning("Postgres not reachable, falling back to SQLite", extra={"error": str(e)})
        _use_postgres = False
