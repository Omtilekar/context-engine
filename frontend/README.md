# ContextEngine Frontend

React, Vite, TypeScript, Tailwind dashboard for the local ContextEngine demo.

## Local UI

```powershell
cd C:\Om\Codes\context_engine
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }

make local-up
make local-migrate
make demo-local

cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The UI calls the backend at `VITE_API_BASE_URL`, which defaults
to `http://localhost:8000`.

## Docker Compose

```powershell
cd C:\Om\Codes\context_engine
make local-full-up
```

This starts PostgreSQL, the FastAPI backend, and the Vite frontend. The backend remains on
`http://localhost:8000`; the frontend is exposed at `http://localhost:5173`.

## Checks

```powershell
cd frontend
npm install
npm run build
npm run lint
```

## Environment

```powershell
VITE_API_BASE_URL=http://localhost:8000
```
