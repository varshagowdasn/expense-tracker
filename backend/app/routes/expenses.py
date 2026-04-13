"""
Expense API routes.

POST /expenses
  - Accepts idempotency_key for safe client retries (network errors, double-submits).
  - If the same idempotency_key is received again, return the original record (201 → 200).

GET /expenses
  - Optional ?category= filter (exact match)
  - Optional ?sort=date_desc (default) or ?sort=date_asc
"""

import uuid
import sqlite3
from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional

from app.database import get_connection
from app.models import (
    ExpenseCreate,
    ExpenseResponse,
    ExpenseListResponse,
    rupees_to_paise,
    paise_to_rupees_str,
    VALID_CATEGORIES,
)
from decimal import Decimal

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ExpenseResponse)
def create_expense(payload: ExpenseCreate):
    amount_paise = rupees_to_paise(payload.amount)
    expense_id = str(uuid.uuid4())
    idem_key = payload.idempotency_key  # may be None

    with get_connection() as conn:
        # Idempotency: if key supplied and already exists, return existing record
        if idem_key:
            existing = conn.execute(
                "SELECT * FROM expenses WHERE idempotency_key = ?", (idem_key,)
            ).fetchone()
            if existing:
                return ExpenseResponse.from_row(existing)

        try:
            conn.execute(
                """
                INSERT INTO expenses (id, idempotency_key, amount_paise, category, description, date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    expense_id,
                    idem_key,
                    amount_paise,
                    payload.category,
                    payload.description,
                    payload.date.isoformat(),
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            # Race condition on idempotency_key unique constraint
            if idem_key and "UNIQUE" in str(e):
                existing = conn.execute(
                    "SELECT * FROM expenses WHERE idempotency_key = ?", (idem_key,)
                ).fetchone()
                if existing:
                    return ExpenseResponse.from_row(existing)
            raise HTTPException(status_code=409, detail="Conflict: duplicate entry")

    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ?", (expense_id,)
    ).fetchone()
    return ExpenseResponse.from_row(row)


@router.get("", response_model=ExpenseListResponse)
def list_expenses(
    category: Optional[str] = Query(None, description="Filter by category"),
    sort: Optional[str] = Query("date_desc", description="Sort order: date_desc or date_asc"),
):
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {sorted(VALID_CATEGORIES)}",
        )

    sort_clause = "date DESC, created_at DESC"
    if sort == "date_asc":
        sort_clause = "date ASC, created_at ASC"

    query = f"SELECT * FROM expenses"
    params = []

    if category:
        query += " WHERE category = ?"
        params.append(category)

    query += f" ORDER BY {sort_clause}"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    expenses = [ExpenseResponse.from_row(r) for r in rows]

    # Sum in paise to avoid float errors, then convert once
    total_paise = sum(r["amount_paise"] for r in rows)
    total_str = paise_to_rupees_str(total_paise)

    return ExpenseListResponse(
        expenses=expenses,
        total=total_str,
        count=len(expenses),
    )


@router.get("/categories")
def list_categories():
    """Return the list of valid categories."""
    return {"categories": sorted(VALID_CATEGORIES)}
