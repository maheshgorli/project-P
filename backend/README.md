# Backend

**Required working directory:** repo root (the folder that contains `backend/`, `frontend/`, `venv/`)

**Required startup command (always run from repo root):**
```
venv\Scripts\uvicorn backend.app.main:app --reload
```

Running uvicorn from inside `backend/` or `backend/app/` will break the absolute imports
(`from backend.app.routers...`) and cause an `ImportError` on startup.
