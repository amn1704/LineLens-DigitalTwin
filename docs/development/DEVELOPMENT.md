# Run LineLens Phase 1

The original root `README.md` is retained as the supplied NexusTwin showcase reference. This document covers the recreated implementation.

## Prerequisites

- Node.js 20+
- Python 3.11+

## Start locally

Open two terminals from the repository root:

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8102
```

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5176
```

Open `http://127.0.0.1:5176`.

The app deliberately uses ports 8102 and 5176 for this workspace because ports 8000, 8100, 8101, 5173, 5174, and 5175 were occupied by previous local instances during verification.

## Checks

```powershell
cd frontend
npm run build

cd ..\backend
python -m compileall -q app
```

`GET /api/state` returns the simulated automotive floor state. All values are prototype-generated and the app is read-only.
