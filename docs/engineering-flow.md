# Engineering Flow

## Frontend

React 18, Vite, React Router, and a small component library under `src/components`.

API calls go through `src/api/client.js`. If the FastAPI service is unavailable, pages use local fallback data so the app does not blank out.

## Backend

FastAPI initializes SQLite on startup, creates required tables, and seeds scenic data through `app/services/seed.py`.

## Local Run

Start backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Start frontend:

```bash
cd frontend
npm install
npm run dev
```
