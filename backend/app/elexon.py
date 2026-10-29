"""Small, defensive client for the public Elexon BMRS API."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pandas as pd

from .config import API_BASE_URL, REQUEST_TIMEOUT_SECONDS, UK_TIMEZONE

UTC = timezone.utc


class ElexonAPIError(RuntimeError):
    pass


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        data = payload.get("data", [])
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    return []


async def _get_json(client: httpx.AsyncClient, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
    url = f"{API_BASE_URL}/{path.lstrip('/')}"
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = await client.get(url, params=params)
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            return _records(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(0.6 * (attempt + 1))
    raise ElexonAPIError(f"Elexon request failed for {path}: {last_error}") from last_error


async def _fetch_publish_day(client: httpx.AsyncClient, dataset: str, day: date) -> list[dict[str, Any]]:
    start = datetime.combine(day, time.min, tzinfo=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    params = {"publishDateTimeFrom": start, "publishDateTimeTo": end}
    # Elexon's stream endpoints return optimized JSON arrays. FUELHH is filtered
    # to WIND after retrieval to avoid depending on server-side enum spelling.
    return await _get_json(client, f"datasets/{dataset}/stream", params)


async def fetch_month_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch actuals and forecast publications around Jan 2026.

    Publication-time windows are chunked into UTC days to keep requests bounded.
    A one-day lookback is included because Jan 1 delivery needs forecasts issued
    on Dec 31. Target intervals are filtered to January after retrieval.
    """
    from_day = date(2025, 12, 31)
    to_day = date(2026, 2, 2)  # exclusive; includes Jan 31 publication day
    days = []
    cursor = from_day
    while cursor < to_day:
        days.append(cursor)
        cursor += timedelta(days=1)

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": "wind-procurement-pilot/1.0"}) as client:
        # Keep concurrency moderate to avoid unnecessary pressure on public API.
        semaphore = asyncio.Semaphore(4)

        async def limited(dataset: str, day: date):
            async with semaphore:
                return await _fetch_publish_day(client, dataset, day)

        actual_batches, forecast_batches = await asyncio.gather(
            asyncio.gather(*(limited("FUELHH", day) for day in days)),
            asyncio.gather(*(limited("WINDFOR", day) for day in days)),
        )

    actual_records = [row for batch in actual_batches for row in batch]
    forecast_records = [row for batch in forecast_batches for row in batch]

    actuals = pd.DataFrame(actual_records)
    forecasts = pd.DataFrame(forecast_records)
    if actuals.empty:
        actuals = pd.DataFrame(columns=["startTime", "fuelType", "generation", "publishTime"])
    if forecasts.empty:
        forecasts = pd.DataFrame(columns=["startTime", "publishTime", "generation"])

    for frame, cols in ((actuals, ["startTime", "publishTime"]), (forecasts, ["startTime", "publishTime"])):
        for col in cols:
            if col in frame.columns:
                frame[col] = pd.to_datetime(frame[col], utc=True, errors="coerce")
        if "generation" in frame.columns:
            frame["generation"] = pd.to_numeric(frame["generation"], errors="coerce")

    if "fuelType" not in actuals.columns:
        raise ElexonAPIError("FUELHH response did not include fuelType; refusing to aggregate unfiltered generation.")
    actuals = actuals[actuals["fuelType"].astype(str).str.upper().eq("WIND")].copy()
    actuals = actuals[actuals["startTime"].notna()].copy()
    forecasts = forecasts[forecasts["startTime"].notna() & forecasts["publishTime"].notna()].copy()

    jan_start = pd.Timestamp("2026-01-01T00:00:00Z")
    feb_start = pd.Timestamp("2026-02-01T00:00:00Z")
    actuals = actuals[(actuals["startTime"] >= jan_start) & (actuals["startTime"] < feb_start)]
    forecasts = forecasts[(forecasts["startTime"] >= jan_start) & (forecasts["startTime"] < feb_start)]

    
    # FUELHH is already national by fuel type. If a correction/revision causes
    # duplicate interval rows, retain the latest published value.
    if "publishTime" in actuals.columns:
        actuals = actuals.sort_values(
            ["startTime", "publishTime"]
        ).drop_duplicates("startTime", keep="last")
    else:
        actuals = actuals.drop_duplicates("startTime", keep="last")

    # Aggregate half-hourly actual generation into hourly mean MW.
    actuals = actuals[["startTime", "generation"]].copy()
    actuals = actuals.set_index("startTime").sort_index()
    actuals = (
        actuals.resample("1h", label="left", closed="left")
        .agg(actual_mw=("generation", "mean"))
        .dropna()
        .reset_index()
    )

    
    # Prepare forecast data.
    forecasts = forecasts[
        ["startTime", "publishTime", "generation"]
    ].rename(columns={"generation": "forecast_mw"})
    forecasts = forecasts.dropna(subset=["forecast_mw"])
    forecasts = forecasts.sort_values(
        ["startTime", "publishTime"]
    ).drop_duplicates(
        ["startTime", "publishTime"], keep="last"
    )

    return actuals, forecasts





def make_decision_frame(actuals: pd.DataFrame, forecasts: pd.DataFrame, decision_hour: int = 10) -> pd.DataFrame:
    """Select latest forecast published by the previous-day decision cutoff.

    Cutoff is local UK time on the day before delivery, converted to UTC. The
    10:00 default is an explicit pilot assumption, not a claim that all traders
    use the same cutoff. The actual delivery interval is matched by startTime.
    """
    if actuals.empty or forecasts.empty:
        return pd.DataFrame(columns=["startTime", "actual_mw", "forecast_mw", "publishTime", "error_mw", "absolute_error_mw", "decision_cutoff"])
    tz = ZoneInfo(UK_TIMEZONE)
    candidates = forecasts.copy()
    candidates["delivery_local_date"] = candidates["startTime"].dt.tz_convert(tz).dt.date
    candidates["decision_cutoff"] = candidates["delivery_local_date"].map(
        lambda d: pd.Timestamp(datetime.combine(d - timedelta(days=1), time(hour=decision_hour), tzinfo=tz)).tz_convert("UTC")
    )
    candidates = candidates[candidates["publishTime"] <= candidates["decision_cutoff"]]
    # Latest eligible publication per delivery interval.
    selected = candidates.sort_values("publishTime").drop_duplicates("startTime", keep="last")
    merged = actuals.merge(selected[["startTime", "forecast_mw", "publishTime", "decision_cutoff"]], on="startTime", how="inner")
    merged["error_mw"] = merged["forecast_mw"] - merged["actual_mw"]
    merged["absolute_error_mw"] = merged["error_mw"].abs()
    return merged.sort_values("startTime").reset_index(drop=True)
