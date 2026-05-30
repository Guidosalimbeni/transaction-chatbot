"""Sanity tests for the data layer.

Run with: pytest tests/
"""
from src import data


def test_list_customers_returns_four():
    customers = data.list_customers()
    assert len(customers) == 4
    ids = {c["customer_id"] for c in customers}
    assert ids == {"C001", "C002", "C003", "C004"}


def test_get_balance_known_customer():
    result = data.get_balance("C001")
    assert "balance" in result
    assert result["currency"] == "GBP"
    assert result["customer_name"] == "Sarah Mitchell"


def test_get_balance_unknown_customer():
    result = data.get_balance("C999")
    assert "error" in result


def test_get_transactions_sorted_desc():
    result = data.get_transactions("C001", limit=5)
    dates = [t["date"] for t in result["transactions"]]
    assert dates == sorted(dates, reverse=True)


def test_get_transactions_category_filter():
    result = data.get_transactions("C001", category="Groceries")
    assert result["count"] > 0
    for t in result["transactions"]:
        assert t["category"] == "Groceries"


def test_find_unfamiliar_charges_eleanor_has_crypto():
    """Eleanor (C003) has three CRYPTO*BITX charges — fraud demo scenario."""
    result = data.find_unfamiliar_charges("C003")
    crypto_charges = [
        t for t in result["transactions"] if "CRYPTO" in t["raw_description"]
    ]
    assert len(crypto_charges) == 3


def test_search_by_merchant():
    result = data.search_transactions("C001", merchant="Tesco")
    assert result["count"] >= 1
    for t in result["transactions"]:
        assert "Tesco" in t["merchant"]
