# Wind Procurement Intelligence (Pilot)

A React + FastAPI web application for evaluating national GB wind generation forecasts against actual generation for delivery intervals in January 2026. Data is sourced only from Elexon BMRS `FUELHH` (actuals, filtered to `fuelType=WIND`) and `WINDFOR` (forecasts).

> **Pilot caveat:** This is decision support, not a trading system. Demand, non-wind generation, interconnectors, prices, reserve requirements and plant constraints are out of scope, so the app does not issue an exact procurement instruction.

## Features

- Forecast-versus-actual time series at 30-minute resolution.
- Forecast publication timestamp and decision cutoff displayed for matched intervals.
- Configurable previous-day cutoff (default 10:00 Europe/London).
- MAE, RMSE, signed forecast bias and MAPE; MAPE excludes actual values with absolute magnitude <= 1 MW.
- Daily aggregation, error time series, interval table and responsive layout.
- FastAPI health endpoint, bounded API requests, retry handling and in-process response cache.
- Docker Compose local environment.

## Data and methodology

- Actuals endpoint: `https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream`
- Forecasts endpoint: `https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream`
- Target delivery interval: `startTime` in `[2026-01-01T00:00:00Z, 2026-02-01T00:00:00Z)`.
- The pipeline filters actuals to `fuelType == WIND`, matches by `startTime`, and chooses the latest forecast `publishTime` not later than the configured decision cutoff for the day before delivery. Forecasts published after cutoff are excluded to avoid look-ahead bias.
- Default decision cutoff is 10:00 UK local time on the previous day. This is a transparent, configurable pilot assumption; confirm the desk's actual operational decision deadline before using results for a real process.
- If duplicate FUELHH rows exist for a delivery interval, the latest published actual is retained rather than summing revisions. Forecast revisions are deduplicated by delivery interval and publication timestamp.
- MAE and RMSE are the primary metrics. MAPE is reported only for intervals where `abs(actual_mw) > 1` because percentage error is unstable around zero.

### Important data validation note

Elexon endpoint behavior, parameter names, data coverage and historical revisions can change. After launch, inspect `/docs`, check the API response, and validate that the returned intervals and publication timestamps are plausible. The application intentionally returns a visible no-data state instead of fabricating sample measurements.

## Repository layout

```text
.
├── backend/
│   ├── app/
│   │   ├── __init__.py       # Python package marker
│   │   ├── config.py         # Dataset dates, API URL and default cutoff
│   │   ├── elexon.py         # Elexon client, normalization and forecast selection
│   │   └── main.py           # FastAPI routes and metrics
│   ├── tests/                 # Forecast-selection unit tests
│   ├── Dockerfile            # Container image for API
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── ui/Dashboard.jsx  # Dashboard, charts, metrics and data table
│   │   ├── main.jsx          # React entry point
│   │   └── style.css         # Responsive dashboard styles
│   ├── index.html            # Vite HTML entry
│   ├── package.json          # Frontend scripts and dependencies
│   └── vercel.json           # SPA rewrite for Vercel
├── docker-compose.yml        # Local frontend + backend orchestration
├── render.yaml               # Render backend deployment blueprint
├── docs/
│   └── demo-script.md       # Two-part video script, under 10 minutes
└── README.md
```

## Run locally with Docker

Requirements: Docker Desktop or Docker Engine with Compose.

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/health
- Interactive API docs: http://localhost:8000/docs
- Overview endpoint: http://localhost:8000/api/overview?decision_hour=10

The first API request fetches historical records from Elexon and may take some time. Subsequent requests are cached in the running backend process. Use `POST /api/cache/clear` to clear that in-memory cache.

## Run without Docker

### Backend

```bash
cd backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000`. For a hosted API, configure `VITE_API_URL` in the frontend build environment.

## Tests

From the `backend` directory, with dependencies installed:

```bash
python -m unittest discover -s tests -v
```

The unit tests use synthetic fixture rows to verify that forecasts published after the decision cutoff are excluded. They do not replace validation against live Elexon data.

## Deployment

The repository includes deployment configuration, but deployment is **not complete until hosted URLs are added here**. No public deployment or GitHub repository has been created by this local project scaffold.

### Backend on Render

1. Push this repository to GitHub.
2. In Render, create a Blueprint from the repository; it reads `render.yaml` and builds the Dockerfile in `backend/`.
3. After deployment, verify `https://YOUR-API.onrender.com/api/health`.
4. Set the backend environment variable `CORS_ORIGINS` to the exact Vercel frontend origin, e.g. `https://YOUR-FRONTEND.vercel.app`.

### Frontend on Vercel

1. Import the repository into Vercel and set the Root Directory to `frontend`.
2. Set `VITE_API_URL` to the deployed backend origin, e.g. `https://YOUR-API.onrender.com` (no trailing slash).
3. Deploy and verify that the dashboard loads the API. Redeploy after changing build-time environment variables.

**Live application URL:** _Add after deployment._  
**Public GitHub repository:** _Add after repository creation._  
**Unlisted demo video:** _Add after recording and uploading._

## AI-tool disclosure

OpenAI ChatGPT was used to assist with project planning, code drafting, README preparation and review. The implementation should be independently run, tested against live Elexon responses, and reviewed before being used for any operational decision.

## Known limitations / next steps

- Verify actual `FUELHH` and `WINDFOR` query parameters and response shapes against the live API before final submission.
- Validate data completeness and whether the historical publication window captures all forecast vintages needed for every January delivery interval.
- Confirm the procurement team's actual decision cutoff and timezone convention.
- Add automated unit tests using fixture data and integration tests against Elexon.
- For production, use persistent caching, rate-limit-aware backoff, structured logging, and an auditable data snapshot.
- The free-tier backend may sleep or time out while fetching a full month on a cold start; prefetch and persist the January data for the final demo if needed.
