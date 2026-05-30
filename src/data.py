"""Data layer — simulates the Core Banking API.

In production these functions would call real banking systems. For the PoC
they read from a CSV. The function signatures are the contract; the
implementation behind them is what would change.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

DATA_PATH = Path(__file__).parent.parent / "data" / "transactions.csv"

# Cache the dataframe in memory — fine for a PoC, not for prod.
_df: Optional[pd.DataFrame] = None


def _load() -> pd.DataFrame:
    global _df
    if _df is None:
        _df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    return _df


def list_customers() -> list[dict]:
    """Return all customers (for the demo UI's customer picker)."""
    df = _load()
    return (
        df[["customer_id", "customer_name", "account_id"]]
        .drop_duplicates()
        .to_dict(orient="records")
    )


def get_balance(customer_id: str) -> dict:
    """Current balance for the customer's account.

    Derived by summing all transactions plus a notional opening balance.
    In production this would call the core banking balance API.
    """
    df = _load()
    cust = df[df["customer_id"] == customer_id]
    if cust.empty:
        return {"error": f"Customer {customer_id} not found."}

    # Notional opening balance so accounts don't look empty.
    OPENING_BALANCE = 1000.00
    balance = OPENING_BALANCE + float(cust["amount"].sum())

    return {
        "customer_id": customer_id,
        "customer_name": cust["customer_name"].iloc[0],
        "account_id": cust["account_id"].iloc[0],
        "balance": round(balance, 2),
        "currency": "GBP",
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def get_transactions(
    customer_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """Recent transactions, optionally filtered by date or category."""
    df = _load()
    cust = df[df["customer_id"] == customer_id].copy()
    if cust.empty:
        return {"error": f"Customer {customer_id} not found."}

    if start_date:
        cust = cust[cust["date"] >= pd.to_datetime(start_date)]
    if end_date:
        cust = cust[cust["date"] <= pd.to_datetime(end_date)]
    if category:
        cust = cust[cust["category"].str.lower() == category.lower()]

    cust = cust.sort_values("date", ascending=False).head(limit)

    return {
        "customer_id": customer_id,
        "count": len(cust),
        "transactions": [
            {
                "txn_id": r["txn_id"],
                "date": r["date"].strftime("%Y-%m-%d"),
                "amount": float(r["amount"]),
                "merchant": r["merchant"],
                "category": r["category"],
                "raw_description": r["raw_description"],
            }
            for _, r in cust.iterrows()
        ],
    }


def search_transactions(
    customer_id: str,
    merchant: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    description_contains: Optional[str] = None,
) -> dict:
    """Free-form search by merchant, amount range, or raw description."""
    df = _load()
    cust = df[df["customer_id"] == customer_id].copy()
    if cust.empty:
        return {"error": f"Customer {customer_id} not found."}

    if merchant:
        cust = cust[cust["merchant"].str.contains(merchant, case=False, na=False)]
    if description_contains:
        cust = cust[
            cust["raw_description"].str.contains(description_contains, case=False, na=False)
        ]
    if min_amount is not None:
        cust = cust[cust["amount"].abs() >= min_amount]
    if max_amount is not None:
        cust = cust[cust["amount"].abs() <= max_amount]

    cust = cust.sort_values("date", ascending=False)

    return {
        "customer_id": customer_id,
        "count": len(cust),
        "transactions": [
            {
                "txn_id": r["txn_id"],
                "date": r["date"].strftime("%Y-%m-%d"),
                "amount": float(r["amount"]),
                "merchant": r["merchant"],
                "category": r["category"],
                "raw_description": r["raw_description"],
            }
            for _, r in cust.iterrows()
        ],
    }


def find_unfamiliar_charges(customer_id: str) -> dict:
    """Return transactions that the customer might not recognise.

    Heuristic for the PoC: merchant is 'Unknown' OR description has the
    classic 'cryptic merchant code' pattern (SP*, AMZ*, CRYPTO*, WWW.).
    A real system would use the customer's own historical patterns + an
    ML classifier.
    """
    df = _load()
    cust = df[df["customer_id"] == customer_id].copy()
    if cust.empty:
        return {"error": f"Customer {customer_id} not found."}

    cryptic_prefixes = ("SP*", "AMZ*", "CRYPTO*", "APL*", "WWW.")
    unfamiliar = cust[
        (cust["merchant"] == "Unknown")
        | (cust["raw_description"].str.startswith(cryptic_prefixes, na=False))
    ].sort_values("date", ascending=False)

    return {
        "customer_id": customer_id,
        "count": len(unfamiliar),
        "transactions": [
            {
                "txn_id": r["txn_id"],
                "date": r["date"].strftime("%Y-%m-%d"),
                "amount": float(r["amount"]),
                "merchant": r["merchant"],
                "raw_description": r["raw_description"],
            }
            for _, r in unfamiliar.iterrows()
        ],
    }
