"""companies / items / price_list / transactions 데이터 접근 계층."""
import sqlite3
from typing import List, Optional, Tuple

TX_TYPES = ("입고", "출고")


# ---------- companies ----------

def list_companies(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM companies ORDER BY company_name"
    ).fetchall()


def get_company(conn: sqlite3.Connection, company_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM companies WHERE company_id = ?", (company_id,)
    ).fetchone()


def add_company(conn: sqlite3.Connection, company_name: str, contact: Optional[str] = None) -> int:
    cur = conn.execute(
        "INSERT INTO companies (company_name, contact) VALUES (?, ?)",
        (company_name, contact),
    )
    conn.commit()
    return cur.lastrowid


def update_company(conn: sqlite3.Connection, company_id: int, company_name: str, contact: Optional[str]) -> None:
    conn.execute(
        "UPDATE companies SET company_name = ?, contact = ? WHERE company_id = ?",
        (company_name, contact, company_id),
    )
    conn.commit()


# ---------- items ----------

def list_items(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM items ORDER BY item_code").fetchall()


def get_item(conn: sqlite3.Connection, item_code: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM items WHERE item_code = ?", (item_code,)
    ).fetchone()


def add_item(
    conn: sqlite3.Connection,
    item_code: str,
    item_name: str,
    default_unit_price: float = 0,
    initial_stock: float = 0,
) -> None:
    conn.execute(
        "INSERT INTO items (item_code, item_name, default_unit_price, initial_stock) "
        "VALUES (?, ?, ?, ?)",
        (item_code, item_name, default_unit_price, initial_stock),
    )
    conn.commit()


def update_item(
    conn: sqlite3.Connection,
    item_code: str,
    item_name: str,
    default_unit_price: float,
    initial_stock: float,
) -> None:
    conn.execute(
        "UPDATE items SET item_name = ?, default_unit_price = ?, initial_stock = ? "
        "WHERE item_code = ?",
        (item_name, default_unit_price, initial_stock, item_code),
    )
    conn.commit()


# ---------- price_list ----------

def get_company_price(conn: sqlite3.Connection, company_id: int, item_code: str) -> Optional[float]:
    row = conn.execute(
        "SELECT unit_price FROM price_list WHERE company_id = ? AND item_code = ?",
        (company_id, item_code),
    ).fetchone()
    return row["unit_price"] if row else None


def set_company_price(conn: sqlite3.Connection, company_id: int, item_code: str, unit_price: float) -> None:
    conn.execute(
        "INSERT INTO price_list (company_id, item_code, unit_price) VALUES (?, ?, ?) "
        "ON CONFLICT(company_id, item_code) DO UPDATE SET unit_price = excluded.unit_price",
        (company_id, item_code, unit_price),
    )
    conn.commit()


def list_prices_for_company(conn: sqlite3.Connection, company_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT p.item_code, i.item_name, p.unit_price FROM price_list p "
        "JOIN items i ON i.item_code = p.item_code "
        "WHERE p.company_id = ? ORDER BY p.item_code",
        (company_id,),
    ).fetchall()


def resolve_unit_price(conn: sqlite3.Connection, company_id: int, item_code: str) -> float:
    """price_list 우선 조회, 없으면 items.default_unit_price로 폴백."""
    override = get_company_price(conn, company_id, item_code)
    if override is not None:
        return override
    item = get_item(conn, item_code)
    if item is None:
        raise ValueError(f"존재하지 않는 품번입니다: {item_code}")
    return item["default_unit_price"]
