"""
Pydantic models for the Expense Tracker API.

Money handling strategy:
  - Clients send/receive amount as a string decimal (e.g. "1234.50") in rupees.
  - Internally stored as INTEGER paise (₹1 = 100 paise) to avoid float precision issues.
  - Conversion: rupees_str → Decimal → multiply by 100 → int paise (rounded to nearest paisa).
"""

from pydantic import BaseModel, field_validator, model_validator, Field
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import date as DateType
from typing import Optional
import re


VALID_CATEGORIES = {
    "Food", "Transport", "Housing", "Healthcare",
    "Entertainment", "Shopping", "Utilities", "Education", "Other"
}


def rupees_to_paise(amount_str: str) -> int:
    """Convert a rupee string like '1234.50' → integer paise 123450."""
    try:
        d = Decimal(str(amount_str))
    except InvalidOperation:
        raise ValueError(f"Invalid amount: {amount_str!r}")
    if d <= 0:
        raise ValueError("Amount must be positive")
    if d > Decimal("10000000"):  # 1 crore cap
        raise ValueError("Amount too large")
    paise = (d * 100).to_integral_value(rounding=ROUND_HALF_UP)
    return int(paise)


def paise_to_rupees_str(paise: int) -> str:
    """Convert integer paise → formatted rupee string like '1234.50'."""
    d = Decimal(paise) / Decimal(100)
    return str(d.quantize(Decimal("0.01")))


class ExpenseCreate(BaseModel):
    amount: str = Field(..., description="Amount in rupees, e.g. '500.00'")
    category: str
    description: str = ""
    date: DateType
    idempotency_key: Optional[str] = Field(
        None,
        description="Client-generated UUID to make POST safe to retry"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        rupees_to_paise(v)  # will raise ValueError on bad input
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(VALID_CATEGORIES)}")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        return v.strip()[:500]


class ExpenseResponse(BaseModel):
    id: str
    amount: str          # rupee string
    category: str
    description: str
    date: str            # YYYY-MM-DD
    created_at: str

    @classmethod
    def from_row(cls, row) -> "ExpenseResponse":
        return cls(
            id=row["id"],
            amount=paise_to_rupees_str(row["amount_paise"]),
            category=row["category"],
            description=row["description"],
            date=row["date"],
            created_at=row["created_at"],
        )


class ExpenseListResponse(BaseModel):
    expenses: list[ExpenseResponse]
    total: str           # sum of visible expenses in rupees
    count: int
