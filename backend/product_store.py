"""SQLite persistence for generated products."""
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("AGENT_FACTORY_DB", str(BASE / "agent_factory.sqlite3"))).expanduser()


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_products_updated_at ON products(updated_at DESC)")


def _normalize_id(product_id: Any) -> str:
    value = str(product_id or "").strip()
    if not value or len(value) > 100:
        raise ValueError("Produkt-ID fehlt oder ist ungültig.")
    return value


def save_product(product: dict) -> dict:
    init_db()
    item = dict(product)
    item_id = _normalize_id(item.get("id"))
    item["id"] = item_id
    now = int(time.time())
    with _connect() as conn:
        row = conn.execute("SELECT created_at FROM products WHERE id = ?", (item_id,)).fetchone()
        created_at = int(row["created_at"]) if row else now
        item["created_at"] = int(item.get("created_at") or created_at)
        item["updated_at"] = now
        conn.execute("""INSERT INTO products(id,payload,created_at,updated_at) VALUES(?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at""",
            (item_id, json.dumps(item, ensure_ascii=False), item["created_at"], now))
    return item


def list_products() -> list[dict]:
    init_db()
    with _connect() as conn:
        rows = conn.execute("SELECT payload FROM products ORDER BY updated_at DESC, created_at DESC").fetchall()
    return [json.loads(row["payload"]) for row in rows]


def get_product(product_id: str) -> dict | None:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT payload FROM products WHERE id = ?", (_normalize_id(product_id),)).fetchone()
    return json.loads(row["payload"]) if row else None


def update_product(product_id: str, patch: dict) -> dict | None:
    current = get_product(product_id)
    if current is None:
        return None
    # Only product metadata is editable. Keep generated assets and publishing details intact.
    for key in ("title", "description", "price", "niche", "tags"):
        if key in patch:
            current[key] = patch[key]
    return save_product(current)


def delete_product(product_id: str) -> bool:
    init_db()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM products WHERE id = ?", (_normalize_id(product_id),))
        return cur.rowcount > 0
