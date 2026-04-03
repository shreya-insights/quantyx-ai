# Local development steps

Use this checklist with **`SETUP.md`** for full detail (MySQL, Redis, Windows vs macOS).

## 1. Environment files

- Copy **`.env.example`** → **`.env`** at the repo root; copy the same values into **`backend/.env`** (or symlink / duplicate).
- Copy **`frontend/.env.example`** → **`frontend/.env`**.
- For **`ALLOWED_ORIGINS`**, use a **JSON array** in `.env`, for example:  
  `ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]`  
  (The Vite dev server in this repo is configured for **port 3000** in `frontend/vite.config.ts`.)

## 2. Database

- Create MySQL database and user per **`SETUP.md`** (or `docker compose up -d mysql redis` if you use Docker).
- From **`backend/`** with the virtualenv activated: **`alembic upgrade head`**.

## 3. Backend (terminal 1)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000 — Docs: http://localhost:8000/docs

## 4. Frontend (terminal 2)

```powershell
cd frontend
npm install
npm run dev
```

- Dev URL is printed by Vite (this project defaults to **http://localhost:3000/**).

## 5. Python 3.13 note

If `pip install -r requirements.txt` tries to **compile** `pandas` / `numpy` and fails (no MSVC), use **Python 3.11+ with wheels** or the versions pinned in `backend/requirements.txt` that ship **cp313** Windows wheels.
