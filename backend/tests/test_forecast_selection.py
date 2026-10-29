import unittest
import pandas as pd
from app.elexon import make_decision_frame


class ForecastSelectionTests(unittest.TestCase):
    def setUp(self):
        self.actuals = pd.DataFrame({
            "startTime": pd.to_datetime(["2026-01-02T00:00:00Z", "2026-01-02T00:30:00Z"]),
            "actual_mw": [100.0, 80.0],
        })

    def test_selects_latest_forecast_before_previous_day_cutoff(self):
        forecasts = pd.DataFrame({
            "startTime": pd.to_datetime([
                "2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z",
                "2026-01-02T00:30:00Z",
            ]),
            "publishTime": pd.to_datetime([
                "2026-01-01T08:00:00Z", "2026-01-01T09:45:00Z", "2026-01-01T10:15:00Z",
                "2026-01-01T09:00:00Z",
            ]),
            "forecast_mw": [90.0, 105.0, 999.0, 75.0],
        })
        result = make_decision_frame(self.actuals, forecasts, decision_hour=10)
        first = result[result.startTime == pd.Timestamp("2026-01-02T00:00:00Z")].iloc[0]
        self.assertEqual(first.forecast_mw, 105.0)
        self.assertEqual(first.error_mw, 5.0)
        self.assertEqual(len(result), 2)

    def test_excludes_forecasts_after_cutoff(self):
        forecasts = pd.DataFrame({
            "startTime": pd.to_datetime(["2026-01-02T00:00:00Z"]),
            "publishTime": pd.to_datetime(["2026-01-01T10:01:00Z"]),
            "forecast_mw": [999.0],
        })
        result = make_decision_frame(self.actuals.iloc[:1], forecasts, decision_hour=10)
        self.assertTrue(result.empty)


if __name__ == "__main__":
    unittest.main()
