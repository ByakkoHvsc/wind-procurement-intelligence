# Wind Procurement Intelligence (Pilot)

**Author:** Harshvardhan Singh Chauhan

A React + FastAPI dashboard comparing Great Britain wind generation forecasts with actual generation for January 2026 using Elexon BMRS data.

## Live Demo

- **Dashboard:** [Open Application](https://wind-procurement-intelligence-eta.vercel.app/)
- **API Health:** [Check Backend](https://wind-procurement-api-rmxz.onrender.com/api/health)
- **GitHub:** [View Repository](https://github.com/ByakkoHvsc/wind-procurement-intelligence)
- **Demo Video:** Coming soon.

## Features

- Forecast-versus-actual generation charts.
- Configurable previous-day forecast cutoff.
- MAE, RMSE, forecast bias, and MAPE metrics.
- Daily summaries and forecast error analysis.
- Responsive dashboard and FastAPI backend.
- Docker Compose development environment.

## Tech Stack

React · Vite · Python · FastAPI · pandas · Docker · Elexon BMRS API

## Methodology

Actual generation comes from `FUELHH`, filtered to wind, and is aggregated from half-hourly records into hourly mean MW values. Forecasts come from `WINDFOR`.

The application selects the latest forecast published before the configured previous-day cutoff, defaulting to 10:00 UK time. Forecasts published after the cutoff are excluded to avoid look-ahead bias.

**Pilot results at the default cutoff:**

| Metric | Result |
|---|---:|
| Matched intervals | 744 |
| MAE | 2,122.81 MW |
| RMSE | 2,616.69 MW |
| Forecast bias | +1,840.30 MW |
| MAPE | 22.06% |

Results are application-reported and have not been independently audited.

## Run Locally

**Requirements:** Docker and Docker Compose.

```bash
git clone https://github.com/ByakkoHvsc/wind-procurement-intelligence.git
cd wind-procurement-intelligence
docker compose up --build
```

Open the dashboard at `http://localhost:5173` or API documentation at `http://localhost:8000/docs`.

Run backend tests from the project root:

```bash
docker compose exec backend python -m unittest discover -s tests -v
```

## Limitations

This is a decision-support pilot, not a trading system. Demand, market prices, interconnectors, and other operational constraints are outside its scope. Historical data completeness and forecast vintages require further validation.

## Ownership

Copyright © 2026 Harshvardhan Singh Chauhan. All rights reserved.

No permission is granted to copy, modify, redistribute, or commercially exploit the original project code without prior written permission, except where applicable law provides otherwise. Third-party components remain subject to their respective licenses.

## AI Disclosure

OpenAI ChatGPT assisted with project planning, code drafting, and documentation.
