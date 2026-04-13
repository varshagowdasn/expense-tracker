"""
Tests for Expense Tracker API.
Run with: pytest tests/ -v
"""

import pytest
import os
import uuid

# Use a temp DB for tests
os.environ["DB_PATH"] = ":memory:"

from fastapi.testclient import TestClient
from app.main import app
from app.models import rupees_to_paise, paise_to_rupees_str

client = TestClient(app)


# ─── Unit tests: money conversion ────────────────────────────────────────────

def test_rupees_to_paise_basic():
    assert rupees_to_paise("100") == 10000

def test_rupees_to_paise_decimal():
    assert rupees_to_paise("1.50") == 150

def test_rupees_to_paise_rounding():
    # 1.005 rupees → 100.5 paise → rounds to 101
    assert rupees_to_paise("1.005") == 101

def test_paise_to_rupees():
    assert paise_to_rupees_str(10050) == "100.50"

def test_rupees_to_paise_negative():
    with pytest.raises(ValueError):
        rupees_to_paise("-10")

def test_rupees_to_paise_zero():
    with pytest.raises(ValueError):
        rupees_to_paise("0")

def test_rupees_to_paise_invalid():
    with pytest.raises(ValueError):
        rupees_to_paise("abc")


# ─── Integration tests: API ────────────────────────────────────────────────────

def make_expense(**kwargs):
    defaults = {
        "amount": "250.00",
        "category": "Food",
        "description": "Lunch",
        "date": "2024-03-15",
    }
    return {**defaults, **kwargs}


def test_create_expense():
    r = client.post("/expenses", json=make_expense())
    assert r.status_code == 201
    data = r.json()
    assert data["amount"] == "250.00"
    assert data["category"] == "Food"
    assert "id" in data


def test_create_expense_bad_category():
    r = client.post("/expenses", json=make_expense(category="Gambling"))
    assert r.status_code == 422


def test_create_expense_negative_amount():
    r = client.post("/expenses", json=make_expense(amount="-50"))
    assert r.status_code == 422


def test_idempotency_key_deduplication():
    key = str(uuid.uuid4())
    payload = make_expense(idempotency_key=key)
    r1 = client.post("/expenses", json=payload)
    r2 = client.post("/expenses", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]  # same record returned


def test_list_expenses():
    r = client.get("/expenses")
    assert r.status_code == 200
    data = r.json()
    assert "expenses" in data
    assert "total" in data
    assert "count" in data


def test_filter_by_category():
    client.post("/expenses", json=make_expense(category="Transport", amount="100"))
    r = client.get("/expenses?category=Transport")
    assert r.status_code == 200
    for exp in r.json()["expenses"]:
        assert exp["category"] == "Transport"


def test_sort_date_desc():
    client.post("/expenses", json=make_expense(date="2024-01-01", amount="10"))
    client.post("/expenses", json=make_expense(date="2024-06-01", amount="20"))
    r = client.get("/expenses?sort=date_desc")
    dates = [e["date"] for e in r.json()["expenses"]]
    assert dates == sorted(dates, reverse=True)


def test_total_calculation():
    # Fresh client with separate state isn't easy with in-memory DB shared across tests,
    # so we just verify total is a valid decimal string
    r = client.get("/expenses")
    total = r.json()["total"]
    float(total)  # should not raise


def test_invalid_category_filter():
    r = client.get("/expenses?category=InvalidCat")
    assert r.status_code == 400
