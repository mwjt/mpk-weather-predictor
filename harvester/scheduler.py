import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from mpk_client import fetch_vehicle_positions
from weather_client import fetch_weather
from db.session import SessionLocal, engine
from db.models import Base, VehiclePosition, WeatherSnapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("harvester")

Base.metadata.create_all(engine)

async def poll_vehicles():
    try:
        vehicles = await fetch_vehicle_positions()
        with SessionLocal() as session:
            for v in vehicles:
                session.add(VehiclePosition(
                    line_name=v.get("name"),
                    vehicle_type=v.get("type"),
                    lat=v.get("x"),
                    lon=v.get("y"),
                    raw_k=v.get("k"),
                    fetched_at=v.get("fetched_at"),
                ))
            session.commit()
        log.info(f"stored {len(vehicles)} vehicle positions")
    except Exception:
        log.exception("vehicle poll failed")

async def poll_weather():
    try:
        w = await fetch_weather()
        if w is None:
            log.warning("empty weather payload")
            return
        with SessionLocal() as session:
            session.add(WeatherSnapshot(**w))
            session.commit()
        log.info("stored weather snapshot")
    except Exception:
        log.exception("weather poll failed")

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll_vehicles, "interval", seconds=60)
    scheduler.add_job(poll_weather, "interval", minutes=15)
    scheduler.start()
    log.info("scheduler started")
    await asyncio.Event().wait()  # run forever

if __name__ == "__main__":
    asyncio.run(main())