"""companies / items / price_list / transactions 데이터 접근 계층."""
import sqlite3
from datetime import date, datetime
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


def import_companies(conn: sqlite3.Connection, rows) -> Tuple[int, int]:
    """rows: [(거래처명, 담당자/연락처?), ...]. (추가건수, 제외건수) 반환."""
    added, skipped = 0, 0
    for row in rows:
        if not row or not row[0]:
            continue
        name = str(row[0]).strip()
        contact = str(row[1]).strip() if len(row) > 1 and row[1] else None
        try:
            add_company(conn, name, contact)
            added += 1
        except sqlite3.IntegrityError:
            skipped += 1
    return added, skipped


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


def import_items(conn: sqlite3.Connection, rows) -> Tuple[int, int]:
    """rows: [(품번, 품명, 기본단가?, 기초재고?), ...]. (추가건수, 제외건수) 반환."""
    added, skipped = 0, 0
    for row in rows:
        if not row or not row[0] or len(row) < 2 or not row[1]:
            skipped += 1
            continue
        code = str(row[0]).strip()
        name = str(row[1]).strip()
        price = float(row[2]) if len(row) > 2 and row[2] not in (None, "") else 0
        stock = float(row[3]) if len(row) > 3 and row[3] not in (None, "") else 0
        try:
            add_item(conn, code, name, price, stock)
            added += 1
        except sqlite3.IntegrityError:
            skipped += 1
    return added, skipped


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


# ---------- transactions ----------

def add_transaction(
    conn: sqlite3.Connection,
    tx_date: str,
    company_id: int,
    item_code: str,
    tx_type: str,
    quantity: float,
    unit_price: float,
    tx_category: str = "",
) -> int:
    if tx_type not in TX_TYPES:
        raise ValueError("구분은 '입고' 또는 '출고'여야 합니다.")
    if quantity is None or quantity < 0:
        raise ValueError("수량은 0 이상이어야 합니다.")
    amount = quantity * unit_price
    cur = conn.execute(
        "INSERT INTO transactions "
        "(tx_date, company_id, item_code, tx_type, quantity, unit_price, amount, tx_category) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (tx_date, company_id, item_code, tx_type, quantity, unit_price, amount, tx_category),
    )
    conn.commit()
    return cur.lastrowid


_BLANK = "미기재"


def _or_blank(value) -> str:
    text = str(value).strip() if value not in (None, "") else ""
    return text or _BLANK


def _existing_tx_signatures(conn: sqlite3.Connection) -> set:
    return {
        (r["tx_date"], r["company_id"], r["item_code"], r["tx_type"], r["quantity"], r["tx_category"])
        for r in conn.execute(
            "SELECT tx_date, company_id, item_code, tx_type, quantity, tx_category FROM transactions"
        )
    }


def import_transactions(conn: sqlite3.Connection, rows) -> Tuple[int, int, int]:
    """rows: [(분류, 거래처명, 날짜, 구분, 품번, 수량), ...]. 거래처/품목이 마스터에 없으면 자동 등록.
    분류/거래처명/날짜/품번이 공란이면 '미기재'로 채우고, 수량이 공란이면 0으로 채운다.
    구분(입고/출고)은 필수값이라 공란이면 해당 행이 실패로 처리된다.
    날짜/거래처/품번/구분/수량/분류가 모두 같은 행은 중복으로 보고 건너뛴다.
    (추가건수, 중복건수, 실패건수) 반환."""
    companies = {c["company_name"]: c["company_id"] for c in list_companies(conn)}
    item_codes = {i["item_code"] for i in list_items(conn)}
    seen = _existing_tx_signatures(conn)
    added, duplicated, failed = 0, 0, 0
    for row in rows:
        if not row or all(v in (None, "") for v in row):
            continue
        try:
            tx_category = _or_blank(row[0])
            company_name = _or_blank(row[1])
            company_id = companies.get(company_name)
            if company_id is None:
                company_id = add_company(conn, company_name)
                companies[company_name] = company_id
            raw_date = row[2]
            tx_date = (
                raw_date.strftime("%Y-%m-%d")
                if isinstance(raw_date, (datetime, date))
                else _or_blank(raw_date)
            )
            tx_type = str(row[3]).strip()
            item_code = _or_blank(row[4])
            if item_code not in item_codes:
                add_item(conn, item_code, item_code)
                item_codes.add(item_code)
            quantity = float(row[5]) if row[5] not in (None, "") else 0.0

            signature = (tx_date, company_id, item_code, tx_type, quantity, tx_category)
            if signature in seen:
                duplicated += 1
                continue

            unit_price = resolve_unit_price(conn, company_id, item_code)
            add_transaction(
                conn, tx_date, company_id, item_code, tx_type, quantity, unit_price, tx_category
            )
            seen.add(signature)
            added += 1
        except (ValueError, TypeError, IndexError, sqlite3.IntegrityError):
            failed += 1
    return added, duplicated, failed


def list_transactions(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """엑셀 내보내기용 전체 거래내역 (분류, 거래처명, 날짜, 구분, 품번, 수량 순)."""
    return conn.execute(
        "SELECT t.tx_category, c.company_name, t.tx_date, t.tx_type, t.item_code, t.quantity "
        "FROM transactions t JOIN companies c ON c.company_id = t.company_id "
        "ORDER BY t.tx_date DESC, t.tx_id DESC"
    ).fetchall()


def _date_filter_clause(date_from: Optional[str], date_to: Optional[str]) -> Tuple[str, list]:
    clause = ""
    params: list = []
    if date_from:
        clause += " AND t.tx_date >= ?"
        params.append(date_from)
    if date_to:
        clause += " AND t.tx_date <= ?"
        params.append(date_to)
    return clause, params


def item_transactions(
    conn: sqlite3.Connection,
    item_code: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[sqlite3.Row]:
    clause, params = _date_filter_clause(date_from, date_to)
    query = (
        "SELECT c.company_name, t.tx_date, t.tx_type, t.quantity, t.unit_price, t.amount "
        "FROM transactions t JOIN companies c ON c.company_id = t.company_id "
        "WHERE t.item_code = ?" + clause + " ORDER BY t.tx_date DESC, t.tx_id DESC"
    )
    return conn.execute(query, [item_code] + params).fetchall()


def company_transactions(
    conn: sqlite3.Connection,
    company_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[sqlite3.Row]:
    clause, params = _date_filter_clause(date_from, date_to)
    query = (
        "SELECT i.item_code, i.item_name, t.tx_date, t.tx_type, t.quantity, t.unit_price, t.amount "
        "FROM transactions t JOIN items i ON i.item_code = t.item_code "
        "WHERE t.company_id = ?" + clause + " ORDER BY t.tx_date DESC, t.tx_id DESC"
    )
    return conn.execute(query, [company_id] + params).fetchall()


def current_stock(conn: sqlite3.Connection, item_code: str) -> Tuple[float, float, float]:
    """(현재재고, 전체입고합계, 전체출고합계)를 반환한다. 기초재고를 포함한 전체 기간 기준."""
    item = get_item(conn, item_code)
    if item is None:
        raise ValueError(f"존재하지 않는 품번입니다: {item_code}")
    totals = conn.execute(
        "SELECT "
        "COALESCE(SUM(CASE WHEN tx_type = '입고' THEN quantity ELSE 0 END), 0) AS total_in, "
        "COALESCE(SUM(CASE WHEN tx_type = '출고' THEN quantity ELSE 0 END), 0) AS total_out "
        "FROM transactions WHERE item_code = ?",
        (item_code,),
    ).fetchone()
    stock = item["initial_stock"] + totals["total_in"] - totals["total_out"]
    return stock, totals["total_in"], totals["total_out"]
