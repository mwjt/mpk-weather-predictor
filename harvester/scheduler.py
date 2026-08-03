import asyncio
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from mpk_client import fetch_vehicle_positions
from weather_client import fetch_weather
from gtfs_client import get_latest_file_id, download_gtfs_zip
from gtfs_loader import load_gtfs_zip
from db.session import SessionLocal, engine, DATABASE_URL
from db.models import Base, VehiclePosition, WeatherSnapshot, GtfsMeta
from datetime import datetime as dt
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "harvester.log"

formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB per file, keep 5 old ones
)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
log = logging.getLogger("harvester")

Base.metadata.create_all(engine)

async def poll_gtfs():
    try:
        latest_id = await get_latest_file_id()
        with SessionLocal() as session:
            meta = session.query(GtfsMeta).first()
            if meta and meta.file_id == latest_id:
                log.info(f"GTFS file {latest_id} already loaded, skipping")
                return

        log.info(f"New GTFS file detected: {latest_id}, downloading...")
        tmp_zip = f"/tmp/gtfs_{latest_id}.zip"
        await download_gtfs_zip(latest_id, tmp_zip)
        load_gtfs_zip(tmp_zip, DATABASE_URL)

        with SessionLocal() as session:
            session.query(GtfsMeta).delete()
            session.add(GtfsMeta(file_id=latest_id, loaded_at=dt.now(timezone.utc)))
            session.commit()

        os.remove(tmp_zip)
        log.info(f"GTFS file {latest_id} loaded successfully")
    except Exception:
        log.exception("gtfs poll failed")

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
    scheduler.add_job(poll_gtfs, "interval", hours=24, next_run_time=dt.now())
    scheduler.start()
    log.info("scheduler started")
    await asyncio.Event().wait()  # run forever

if __name__ == "__main__":
    asyncio.run(main())