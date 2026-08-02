import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import db, models


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    yield connection
    connection.close()


@pytest.fixture
def sample(conn):
    company_a = models.add_company(conn, "A상사", "010-1111-2222")
    company_b = models.add_company(conn, "B물산")
    models.add_item(conn, "ITEM-001", "볼트", default_unit_price=100, initial_stock=50)
    return {"company_a": company_a, "company_b": company_b}


def test_schema_creates_empty_tables(conn):
    assert models.list_companies(conn) == []
    assert models.list_items(conn) == []


def test_resolve_unit_price_fallback_to_default(conn, sample):
    price = models.resolve_unit_price(conn, sample["company_a"], "ITEM-001")
    assert price == 100


def test_resolve_unit_price_uses_company_override(conn, sample):
    models.set_company_price(conn, sample["company_a"], "ITEM-001", 150)
    price_a = models.resolve_unit_price(conn, sample["company_a"], "ITEM-001")
    price_b = models.resolve_unit_price(conn, sample["company_b"], "ITEM-001")
    assert price_a == 150
    assert price_b == 100  # B사는 여전히 기본단가 사용


def test_set_company_price_upsert_overwrites(conn, sample):
    models.set_company_price(conn, sample["company_a"], "ITEM-001", 150)
    models.set_company_price(conn, sample["company_a"], "ITEM-001", 200)
    price = models.resolve_unit_price(conn, sample["company_a"], "ITEM-001")
    assert price == 200


def test_add_transaction_computes_amount(conn, sample):
    tx_id = models.add_transaction(
        conn, "2026-08-01", sample["company_a"], "ITEM-001", "입고", 10, 100
    )
    row = conn.execute("SELECT amount FROM transactions WHERE tx_id = ?", (tx_id,)).fetchone()
    assert row["amount"] == 1000


def test_add_transaction_allows_negative_unit_price(conn, sample):
    tx_id = models.add_transaction(
        conn, "2026-08-01", sample["company_a"], "ITEM-001", "출고", 5, -20
    )
    row = conn.execute("SELECT amount FROM transactions WHERE tx_id = ?", (tx_id,)).fetchone()
    assert row["amount"] == -100


def test_add_transaction_rejects_non_positive_quantity(conn, sample):
    with pytest.raises(ValueError):
        models.add_transaction(conn, "2026-08-01", sample["company_a"], "ITEM-001", "입고", 0, 100)
    with pytest.raises(ValueError):
        models.add_transaction(conn, "2026-08-01", sample["company_a"], "ITEM-001", "입고", -5, 100)


def test_add_transaction_rejects_invalid_type(conn, sample):
    with pytest.raises(ValueError):
        models.add_transaction(conn, "2026-08-01", sample["company_a"], "ITEM-001", "폐기", 5, 100)


def test_current_stock_calculation(conn, sample):
    # 기초재고 50
    models.add_transaction(conn, "2026-08-01", sample["company_a"], "ITEM-001", "입고", 30, 100)
    models.add_transaction(conn, "2026-08-02", sample["company_b"], "ITEM-001", "출고", 20, 100)
    stock, total_in, total_out = models.current_stock(conn, "ITEM-001")
    assert total_in == 30
    assert total_out == 20
    assert stock == 50 + 30 - 20  # 60


def test_item_transactions_date_filter(conn, sample):
    models.add_transaction(conn, "2026-07-01", sample["company_a"], "ITEM-001", "입고", 10, 100)
    models.add_transaction(conn, "2026-08-01", sample["company_a"], "ITEM-001", "입고", 20, 100)
    models.add_transaction(conn, "2026-08-15", sample["company_a"], "ITEM-001", "출고", 5, 100)

    all_rows = models.item_transactions(conn, "ITEM-001")
    assert len(all_rows) == 3

    filtered = models.item_transactions(conn, "ITEM-001", date_from="2026-08-01", date_to="2026-08-31")
    assert len(filtered) == 2
    assert all(row["tx_date"] >= "2026-08-01" for row in filtered)


def test_company_transactions_joins_item_name(conn, sample):
    models.add_transaction(conn, "2026-08-01", sample["company_a"], "ITEM-001", "입고", 10, 100)
    rows = models.company_transactions(conn, sample["company_a"])
    assert len(rows) == 1
    assert rows[0]["item_name"] == "볼트"


def test_import_companies_adds_and_skips_duplicates(conn, sample):
    added, skipped = models.import_companies(
        conn, [("A상사", "dup"), ("C상사", "010-3333-4444"), (None, None)]
    )
    assert added == 1
    assert skipped == 1
    assert len(models.list_companies(conn)) == 3


def test_import_items_adds_and_applies_defaults(conn, sample):
    added, skipped = models.import_items(
        conn, [("ITEM-001", "볼트", 100, 50), ("ITEM-002", "너트"), ("ITEM-003", None)]
    )
    assert added == 1  # ITEM-001 already exists -> skipped, ITEM-002 added, ITEM-003 missing name -> skipped
    assert skipped == 2
    item2 = models.get_item(conn, "ITEM-002")
    assert item2["default_unit_price"] == 0
    assert item2["initial_stock"] == 0


def test_import_transactions_resolves_price_and_rejects_unknown_company(conn, sample):
    added, failed = models.import_transactions(
        conn,
        [
            ("2026-08-01", "A상사", "ITEM-001", "입고", 10),  # 단가 생략 -> 기본단가 100 사용
            ("2026-08-02", "존재하지않는거래처", "ITEM-001", "출고", 5, 100),
        ],
    )
    assert added == 1
    assert failed == 1
    stock, total_in, total_out = models.current_stock(conn, "ITEM-001")
    assert total_in == 10
    assert total_out == 0
