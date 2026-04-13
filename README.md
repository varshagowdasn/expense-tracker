# Paisa — Expense Tracker

A minimal full-stack personal expense tracker built with FastAPI (Python) and vanilla HTML/CSS/JS.

**Live demo:** https://your-frontend.github.io/expense-tracker  
**Backend API:** https://your-backend.onrender.com  
**API Docs:** https://your-backend.onrender.com/docs

---

## Features

- ✅ Create expenses with amount, category, description, date
- ✅ View all expenses in a clean table
- ✅ Filter by category (chip controls)
- ✅ Sort by date (newest / oldest)
- ✅ Live total for current filtered view
- ✅ Category breakdown summary
- ✅ Idempotent POST — safe to retry on network failures or double-clicks
- ✅ Input validation (positive amounts, required fields)
- ✅ Loading skeleton and error states
- ✅ Correct money handling (integer paise arithmetic, no float errors)

---

## Project Structure

```
expense-tracker/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI app, CORS, startup
│   │   ├── database.py      # SQLite setup, get_connection()
│   │   ├── models.py        # Pydantic schemas, money conversion
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── expenses.py  # POST /expenses, GET /expenses
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_expenses.py # Unit + integration tests
│   ├── requirements.txt
│   ├── run.py               # Local dev entry point
│   └── render.yaml          # Render.com deployment config
│
└── frontend/
    └── index.html           # Single-file UI (no build step)
```

---

## Key Design Decisions

### Money Handling
Amounts are stored as **INTEGER paise** (1 rupee = 100 paise) in SQLite to eliminate floating-point precision errors. The API layer converts between paise and rupee strings using Python's `Decimal` type with `ROUND_HALF_UP`. Clients always send and receive amounts as decimal strings (e.g. `"1234.50"`), never raw floats.

### Idempotency
`POST /expenses` accepts an optional `idempotency_key` (UUID) from the client. If the same key is submitted again (double-click, page reload, network retry), the server returns the original record instead of creating a duplicate. The key has a `UNIQUE` constraint in SQLite with a race-condition guard. The frontend generates a fresh UUID per submission and resets it only on success.

### Persistence: SQLite
SQLite was chosen because:
- Zero configuration, single file, survives process restarts
- ACID compliant with WAL mode for concurrent reads
- Built into Python — no extra dependency
- Trivially replaceable with Postgres via SQLAlchemy (just swap the connection string)

For production scale, swap `database.py` for SQLAlchemy + Postgres.

### Frontend
Pure HTML + CSS + Vanilla JS with no build step. The UI is a single file deployable anywhere (GitHub Pages, Netlify, S3). The `API_BASE` constant auto-detects localhost vs production.

---

## Running Locally

### Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend

```bash
# Just open frontend/index.html in a browser, or:
cd frontend
python -m http.server 3000
# Open http://localhost:3000
```

### Tests

```bash
cd backend
pip install pytest httpx
pytest tests/ -v
```

---

## API Reference

### `POST /expenses`
```json
{
  "amount": "250.50",
  "category": "Food",
  "description": "Lunch",
  "date": "2024-03-15",
  "idempotency_key": "uuid-optional"
}
```
Returns the created expense. Idempotent if `idempotency_key` is provided.

### `GET /expenses`
Query params:
- `category` — filter by category (Food, Transport, etc.)
- `sort` — `date_desc` (default) or `date_asc`

Returns:
```json
{
  "expenses": [...],
  "total": "1234.50",
  "count": 7
}
```

### `GET /expenses/categories`
Returns list of valid categories.

---

## Deployment

### Backend → Render.com (free tier)
1. Push repo to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Set **Root directory** to `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Frontend → GitHub Pages
1. Go to repo **Settings → Pages**
2. Set source to `main` branch, `/frontend` folder
3. Your UI is live at `https://<username>.github.io/<repo>/`
4. Update `API_BASE` in `frontend/index.html` to point to your Render URL

---

## Trade-offs (due to timebox)

| What | Decision |
|---|---|
| Auth | Not implemented — any user sees all expenses |
| Pagination | Not implemented — full list returned |
| Delete/Edit | Not implemented — add-only for now |
| Multi-user | Single shared data store |
| Rate limiting | Not implemented |
| HTTPS enforced | Deferred to platform (Render handles TLS) |

---

## What I Intentionally Did Not Do
- User authentication / sessions
- Edit or delete expenses
- Pagination (small data set assumption)
- Frontend build tooling (kept it a single deployable file)
- Real-time updates (polling or websockets)
