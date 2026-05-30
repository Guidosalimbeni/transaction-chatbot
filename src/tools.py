"""LangChain tools exposed to the agent.

These are thin adapters over data.py. The split is deliberate: the data
layer stays framework-agnostic and testable; the tools layer is what the
agent imports.
"""
from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool

from . import data


@tool
def get_balance(customer_id: str) -> dict:
    """Return the current account balance for a customer.

    Args:
        customer_id: The customer's ID (e.g. 'C001').
    """
    return data.get_balance(customer_id)


@tool
def get_transactions(
    customer_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """List recent transactions for a customer, optionally filtered.

    Args:
        customer_id: The customer's ID (e.g. 'C001').
        start_date: ISO date 'YYYY-MM-DD'. Optional.
        end_date: ISO date 'YYYY-MM-DD'. Optional.
        category: Filter by category (e.g. 'Groceries', 'Subscription'). Optional.
        limit: Max number of transactions to return (default 20).
    """
    return data.get_transactions(
        customer_id=customer_id,
        start_date=start_date,
        end_date=end_date,
        category=category,
        limit=limit,
    )


@tool
def search_transactions(
    customer_id: str,
    merchant: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    description_contains: Optional[str] = None,
) -> dict:
    """Search a customer's transactions by merchant, amount range, or text in the description.

    Use this when the user asks about a specific merchant ('did I pay Netflix?')
    or wants to find transactions matching a partial description.

    Args:
        customer_id: The customer's ID.
        merchant: Substring match against merchant name. Optional.
        min_amount: Minimum absolute amount. Optional.
        max_amount: Maximum absolute amount. Optional.
        description_contains: Substring match against the raw bank description. Optional.
    """
    return data.search_transactions(
        customer_id=customer_id,
        merchant=merchant,
        min_amount=min_amount,
        max_amount=max_amount,
        description_contains=description_contains,
    )


@tool
def find_unfamiliar_charges(customer_id: str) -> dict:
    """Find transactions that the customer might not recognise.

    Returns transactions where the merchant is unknown or the description
    looks cryptic (e.g. 'SP* MERIDIAN CO', 'CRYPTO*BITX'). Use this when
    the user asks about suspicious or unfamiliar charges.

    Args:
        customer_id: The customer's ID.
    """
    return data.find_unfamiliar_charges(customer_id)


# Exported as a list for easy binding to the agent.
ALL_TOOLS = [
    get_balance,
    get_transactions,
    search_transactions,
    find_unfamiliar_charges,
]
