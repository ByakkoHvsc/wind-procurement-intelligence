from __future__ import annotations

import os
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import DEFAULT_DECISION_HOUR, END_DATE, START_DATE
from .elexon import ElexonAPIError, fetch_month_data, make_decision_frame

app = FastAPI(
    title="Wind Procurement Intelligence API",
    description="January 2026 GB wind generation forecast evaluation using Elexon BMRS data.",
    version="0.1.0",
)
allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache: dict[str, Any] = {}


async def get_frame(decision_hour: int) -> pd.DataFrame:
    key = f"jan-2026-{decision_hour}"
    if key in _cache:
        return _cache[key]
    try:
        actuals, forecasts = await fetch_month_data()
        frame = make_decision_frame(actuals, forecasts, decision_hour=decision_hour)
    except ElexonAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    _cache[key] = frame
    return frame


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, date)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else round(float(value), 3)
    if pd.isna(value):
        return None
    return value


def records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [{k: json_safe(v) for k, v in row.items()} for row in frame.to_dict(orient="records")]


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "wind-procurement-api"}


@app.get("/api/overview")
async def overview(decision_hour: int = Query(DEFAULT_DECISION_HOUR, ge=0, le=23)):
    frame = await get_frame(decision_hour)
    if frame.empty:
        return {
            "period": {"from": START_DATE.isoformat(), "to_exclusive": END_DATE.isoformat()},
            "decision_hour_uk": decision_hour,
            "data_status": "no_matched_data",
            "message": "No matched actual/eligible forecast intervals were returned. Check Elexon API availability and the decision cutoff assumption.",
            "metrics": {"matched_intervals": 0, "mae_mw": None, "rmse_mw": None, "bias_mw": None, "mape_pct": None},
            "series": [],
        }
    actual = frame["actual_mw"].astype(float)
    forecast = frame["forecast_mw"].astype(float)
    error = forecast - actual
    nonzero = actual.abs() > 1.0  # MAPE is unstable at/near zero; threshold is disclosed.
    metrics = {
        "matched_intervals": int(len(frame)),
        "mae_mw": float(np.mean(np.abs(error))),
        "rmse_mw": float(np.sqrt(np.mean(np.square(error)))),
        "bias_mw": float(np.mean(error)),
        "mape_pct": float(np.mean(np.abs(error[nonzero] / actual[nonzero])) * 100) if nonzero.any() else None,
        "mape_intervals": int(nonzero.sum()),
        "mean_actual_mw": float(actual.mean()),
        "mean_forecast_mw": float(forecast.mean()),
        "overforecast_intervals": int((error > 0).sum()),
        "underforecast_intervals": int((error < 0).sum()),
    }
    daily = frame.assign(delivery_date=frame["startTime"].dt.tz_convert("Europe/London").dt.strftime("%Y-%m-%d"))
    daily_summary = daily.groupby("delivery_date").agg(
        actual_mw=("actual_mw", "mean"), forecast_mw=("forecast_mw", "mean"), mae_mw=("absolute_error_mw", "mean"), intervals=("startTime", "count")
    ).reset_index()
    return {
        "period": {"from": START_DATE.isoformat(), "to_exclusive": END_DATE.isoformat()},
        "decision_hour_uk": decision_hour,
        "timezone": "Europe/London",
        "data_status": "ok",
        "assumptions": [
            "Decision cutoff defaults to 10:00 UK local time on the day before delivery; this is a configurable pilot assumption.",
            "Forecasts published after the cutoff are excluded, preventing look-ahead bias.",
            "MAPE excludes intervals with absolute actual generation <= 1 MW; MAE and RMSE remain the primary error measures.",
            "Only Elexon FUELHH records with fuelType=WIND and WINDFOR records are used.",
        ],
        "metrics": metrics,
        "daily": records(daily_summary),
        "series": records(frame[["startTime", "actual_mw", "forecast_mw", "publishTime", "decision_cutoff", "error_mw", "absolute_error_mw"]]),
    }


@app.post("/api/cache/clear")
def clear_cache():
    _cache.clear()
    return {"status": "cleared"}
