"""Weather display for Cleveland (read-only)."""

from __future__ import annotations

import httpx

from brain.connectors.base import ConnectorNotConfigured, env_required, is_configured

CONNECTOR = "weather"
ENV_VARS = ["WEATHER_API_KEY"]
CLEVELAND_LAT = 41.4993
CLEVELAND_LON = -81.6944


def configured() -> bool:
    return is_configured(*ENV_VARS)


def fetch_cleveland() -> dict:
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)

    key = env_required("WEATHER_API_KEY", CONNECTOR)
    resp = httpx.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={
            "lat": CLEVELAND_LAT,
            "lon": CLEVELAND_LON,
            "appid": key,
            "units": "imperial",
        },
        timeout=20.0,
    )
    resp.raise_for_status()
    data = resp.json()
    main = data.get("main", {})
    weather = (data.get("weather") or [{}])[0]
    return {
        "temp_f": round(main.get("temp", 0)),
        "conditions": weather.get("description", "").title(),
        "location": "Cleveland, OH",
    }
