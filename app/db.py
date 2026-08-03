"""SQLite 연결 관리 및 스키마 생성."""
import os
import sqlite3
import sys
from typing import Optional


def get_db_path() -> str:
    """exe와 같은 폴더에 DB 파일 위치를 반환한다."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "inventory.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,
    contact TEXT
);

CREATE TABLE IF NOT EXISTS items (
    item_code TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    default_unit_price REAL NOT NULL DEFAULT 0,
    initial_stock REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS price_list (
    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    item_code TEXT NOT NULL REFERENCES items(item_code),
    unit_price REAL NOT NULL,
    PRIMARY KEY (company_id, item_code)
);

CREATE TABLE IF NOT EXISTS transactions (
    tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_date TEXT NOT NULL,
    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    item_code TEXT NOT NULL REFERENCES items(item_code),
    tx_type TEXT NOT NULL CHECK (tx_type IN ('입고', '출고')),
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    amount REAL NOT NULL,
    tx_category TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_tx_item ON transactions(item_code);
CREATE INDEX IF NOT EXISTS idx_tx_company ON transactions(company_id);
CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(tx_date);
"""


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    """DB 연결을 생성하고 스키마가 없으면 생성한다."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(transactions)")}
    if "tx_category" not in columns:
        conn.execute("ALTER TABLE transactions ADD COLUMN tx_category TEXT NOT NULL DEFAULT ''")
    conn.commit()
    return conn
