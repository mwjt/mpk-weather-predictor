import httpx
from datetime import datetime, timezone
from db.session import SessionLocal
from db.models import GtfsRoute

MPK_URL = "https://mpk.wroc.pl/bus_position"

def get_tracked_lines() -> list[str]:
    with SessionLocal() as session:
        rows = session.query(GtfsRoute.route_short_name).distinct().all()
    return [r[0] for r in rows if r[0]]

async def fetch_vehicle_positions(lines: list[str] | None = None) -> list[dict]:
    if lines is None:
        lines = get_tracked_lines()

    data = {"busList[][]": lines}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(MPK_URL, data=data)
        resp.raise_for_status()
        vehicles = resp.json()

    fetched_at = datetime.now(timezone.utc)
    for v in vehicles:
        v["fetched_at"] = fetched_at
    return vehicles