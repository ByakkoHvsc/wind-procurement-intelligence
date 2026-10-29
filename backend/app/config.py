from datetime import date

API_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 2, 1)  # exclusive
UK_TIMEZONE = "Europe/London"
DEFAULT_DECISION_HOUR = 10  # illustrative assumption; configurable in API
REQUEST_TIMEOUT_SECONDS = 45
