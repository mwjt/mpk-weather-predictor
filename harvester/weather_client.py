import httpx
from datetime import datetime, timezone

IMGW_URL = "https://danepubliczne.imgw.pl/api/data/synop/station/wroclaw"

async def fetch_weather() -> dict | None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(IMGW_URL)
        resp.raise_for_status()
        payload = resp.json()

    if not payload:
        return None

    return {
        "station_id": payload["id_stacji"],
        "station_name": payload["stacja"],
        "temperature_c": float(payload["temperatura"]) if payload["temperatura"] else None,
        "wind_speed": float(payload["predkosc_wiatru"]) if payload["predkosc_wiatru"] else None,
        "wind_direction": payload["kierunek_wiatru"],
        "humidity_pct": float(payload["wilgotnosc_wzgledna"]) if payload["wilgotnosc_wzgledna"] else None,
        "precipitation_mm": float(payload["suma_opadu"]) if payload["suma_opadu"] else None,
        "pressure_hpa": float(payload["cisnienie"]) if payload["cisnienie"] else None,
        "measurement_date": payload["data_pomiaru"],
        "measurement_hour": payload["godzina_pomiaru"],
        "fetched_at": datetime.now(timezone.utc),
    }