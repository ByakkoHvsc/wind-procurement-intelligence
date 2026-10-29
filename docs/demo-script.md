# Demo recording script (target 8–9 minutes total)

Record one continuous screen capture if practical. Keep the complete video under 10 minutes. Do not claim that hosted deployment or live data retrieval has succeeded until you have verified it on screen.

## Part 1 — Client presentation (target 4:00; max 5:00)

**0:00–0:30 | Business problem**
“Wind generation is uncertain, while day-ahead procurement decisions have to be made before delivery. This pilot gives the desk one view of the latest forecast that was actually available at its decision cutoff and how that forecast performed against outturn.”

**0:30–1:20 | Dashboard overview**
Show the January 2026 range, 30-minute resolution, cutoff selector and KPI cards. Explain that the default cutoff is 10:00 UK local time on the previous day and is a pilot assumption to be confirmed with the desk.

**1:20–2:20 | Forecast and actual comparison**
Point to the forecast-versus-actual chart and error series. Explain that the interval table records delivery time, forecast publication time, cutoff, forecast MW, actual MW and signed error.

**2:20–3:15 | Accuracy metrics**
Explain MAE as average absolute miss, RMSE as a metric that penalizes large misses, and bias as whether forecasts systematically overstate or understate wind. Mention that MAPE is excluded around zero actuals because percentage errors become unstable.

**3:15–4:00 | Decision value and limitations**
“An under-forecast can mean less wind is available than expected; an over-forecast can mean the desk expects more renewable supply than arrives. These signals help quantify uncertainty, but this pilot does not issue a buy quantity because demand, prices, other generation and operational constraints were intentionally excluded.”

## Part 2 — Technical review (target 4:30; max 5:00)

**0:00–0:45 | Architecture**
Show the repository tree: React/Vite frontend, FastAPI backend, Elexon client and Docker Compose. Explain that the frontend calls `/api/overview` and does not access Elexon directly.

**0:45–1:45 | Data pipeline**
Open `backend/app/elexon.py`. Explain chunked publication-time requests, parsing timestamps as UTC, filtering `FUELHH` to `fuelType=WIND`, restricting delivery `startTime` to January 2026, and selecting forecast vintages by `publishTime`.

**1:45–2:40 | Avoiding look-ahead bias**
Show `make_decision_frame`. For each delivery interval, the code computes the previous-day cutoff in `Europe/London`, converts it to UTC, excludes forecasts published after that cutoff, and chooses the latest remaining publication. Explain why matching a later forecast would overstate decision-time knowledge.

**2:40–3:25 | Metrics and frontend**
Show `backend/app/main.py` for MAE/RMSE/bias/MAPE and `frontend/src/ui/Dashboard.jsx` for charts, cutoff selection and table. Mention MAPE's `abs(actual) > 1 MW` filter.

**3:25–4:05 | Quality and deployment**
Run `python -m unittest discover -s tests -v` from `backend/`, show Docker Compose, then show `/api/health` and `/docs`. Explain retry handling, API cache, CORS configuration, and the Vercel frontend + Render backend deployment plan.

**4:05–4:30 | Limitations / handover**
State that live Elexon responses, completeness, historical publication windows, the actual desk cutoff, and hosted deployment must be validated. Explain the app is a pilot decision-support tool, not an automated trading recommendation.
