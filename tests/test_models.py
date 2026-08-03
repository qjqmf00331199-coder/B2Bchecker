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


def test_add_transaction_rejects_negative_quantity(conn, sample):
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


def test_import_transactions_resolves_price_and_autoregisters_master_data(conn, sample):
    added, duplicated, failed = models.import_transactions(
        conn,
        [
            ("재료비", "A상사", "2026-08-01", "입고", "ITEM-001", 10),  # 단가는 자동 계산
            ("가공비", "신규거래처", "2026-08-02", "입고", "NEW-ITEM", 3),  # 거래처/품목 자동 등록
            ("재료비", "A상사", "2026-08-03", "출고", "ITEM-001", None),  # 수량 누락 -> 0으로 처리
            ("재료비", "A상사", "2026-08-04", "", "ITEM-001", 5),  # 구분 누락 -> 실패
        ],
    )
    assert added == 3
    assert duplicated == 0
    assert failed == 1
    assert "신규거래처" in {c["company_name"] for c in models.list_companies(conn)}
    assert models.get_item(conn, "NEW-ITEM") is not None
    stock, total_in, total_out = models.current_stock(conn, "ITEM-001")
    assert total_in == 10
    assert total_out == 0


def test_import_transactions_blank_fields_become_placeholder(conn, sample):
    added, duplicated, failed = models.import_transactions(
        conn, [("", "", "", "입고", "", 7)]
    )
    assert added == 1
    assert duplicated == 0
    assert failed == 0
    assert "미기재" in {c["company_name"] for c in models.list_companies(conn)}
    assert models.get_item(conn, "미기재") is not None


def test_import_transactions_skips_exact_duplicates(conn, sample):
    row = ("재료비", "A상사", "2026-08-01", "입고", "ITEM-001", 10)
    added1, duplicated1, failed1 = models.import_transactions(conn, [row])
    added2, duplicated2, failed2 = models.import_transactions(conn, [row])
    assert (added1, duplicated1, failed1) == (1, 0, 0)
    assert (added2, duplicated2, failed2) == (0, 1, 0)
    stock, total_in, total_out = models.current_stock(conn, "ITEM-001")
    assert total_in == 10
