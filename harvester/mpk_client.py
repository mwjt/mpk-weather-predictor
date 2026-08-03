import httpx
from datetime import datetime, timezone

MPK_URL = "https://mpk.wroc.pl/bus_position"

# Lines you care about — start with a handful you actually use/pass daily
TRACKED_LINES = ["0", "1", "2", "4", "10", "17", "33", "A", "K"]

async def fetch_vehicle_positions(lines: list[str] = TRACKED_LINES) -> list[dict]:
    """
    MPK's endpoint wants form-encoded busList[][]=<line> repeated per line.
    Returns list of {name, type, x (lat), y (lon), k} per vehicle.
    """
    data = {"busList[][]": lines}
    async with httpx.AsyncClient(verify=False, timeout=10) as client:
        resp = await client.post(MPK_URL, data=data)
        resp.raise_for_status()
        vehicles = resp.json()

    fetched_at = datetime.now(timezone.utc)
    for v in vehicles:
        v["fetched_at"] = fetched_at
    return vehicles