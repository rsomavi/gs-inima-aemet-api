# GS Inima Development Challenge — Antarctica Weather API

A web service that retrieves, caches, and serves historical weather data from AEMET's (Spanish Meteorological Agency) Antarctic weather stations, with a frontend for querying and visualizing the data. Built as a technical case study for GS Inima's Business Development / Analytical team, evaluating feasibility of a wind farm in Antarctica.

## Live demo

- **Frontend:** https://gs-inima-aemet-api-frontend.onrender.com
- **Backend API:** https://gs-inima-aemet-api.onrender.com/api

> Note: both are on Render's free tier. The backend spins down after inactivity (first request after idling can take up to ~50s to respond), and its SQLite cache resets on every redeploy/restart (see [`docs/known-limitations.md`](docs/known-limitations.md)).

## What this does

- Fetches 10-minute-resolution weather observations (temperature, pressure, wind speed) for two Antarctic stations (Gabriel de Castilla, Juan Carlos I) from AEMET's OpenData API.
- Caches observations locally in SQLite to avoid re-hitting AEMET for data already retrieved, using gap detection so only missing sub-ranges are fetched.
- Supports optional aggregation (none/hourly/daily/monthly), variable filtering, and timezone-aware output (Europe/Madrid, CET/CEST, DST-safe).
- Provides a Vue 3 + TypeScript frontend with a query form, results table, and chart.

## Tech stack

- **Backend:** Django + Django REST Framework, SQLite
- **Frontend:** Vue 3, TypeScript, Vite, Chart.js

See [`docs/architecture.md`](docs/architecture.md) for why these were chosen over the FastAPI/Flask + React suggested in the original brief.

## Running locally

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set AEMET_API_KEY (get one at https://opendata.aemet.es/centrodedescargas/inicio,
# using a personal email address — corporate accounts have been observed to be blocked)
python manage.py migrate
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/`.

Run the backend test suite:

```bash
python manage.py test weather
```

Optional: run the adversarial smoke test scripts (from the repo root, with the server running):

```bash
python scripts/smoke_test_validation.py    # local validation edge cases, no AEMET calls
python scripts/smoke_test_live_aemet.py     # hits the real AEMET API — uses your quota
```

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

The app will be available at `http://localhost:5173`.

Run the frontend test suite:

```bash
npm run test:unit
```

> The frontend expects the backend to be running at `http://localhost:8000`. CORS is pre-configured for `http://localhost:5173` in `backend/config/settings.py`.

## Documentation

Detailed design decisions and reasoning live in [`docs/`](docs/):

- [`docs/architecture.md`](docs/architecture.md) — overall design, stack choices
- [`docs/timezone-handling.md`](docs/timezone-handling.md) — UTC storage, Europe/Madrid output, DST behavior, the `location` parameter
- [`docs/caching-strategy.md`](docs/caching-strategy.md) — gap detection, upsert, why SQLite as-is
- [`docs/aggregation.md`](docs/aggregation.md) — hourly/daily/monthly aggregation and the Madrid-calendar-day rule
- [`docs/known-limitations.md`](docs/known-limitations.md) — things intentionally left out or worth knowing about, including AEMET's ~1-month range limit and how it was discovered and handled

## Project structure

```
backend/    Django REST API (see backend/README.md for backend-only notes)
frontend/   Vue 3 + TypeScript app (see frontend/README.md for frontend-only notes)
scripts/    Adversarial smoke test scripts (not part of the automated test suite)
docs/       Design decisions and detailed reasoning
```