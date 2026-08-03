import logging
from datetime import date, timedelta
from sqlalchemy import text
from db.session import engine

log = logging.getLogger("partitioning")

def ensure_partition_exists(target_date: date):
    partition_name = f"vehicle_positions_{target_date.strftime('%Y_%m_%d')}"
    start = target_date
    end = target_date + timedelta(days=1)

    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {partition_name}
            PARTITION OF vehicle_positions
            FOR VALUES FROM ('{start}') TO ('{end}')
        """))
    log.info(f"ensured partition {partition_name} exists")

def ensure_upcoming_partitions(days_ahead: int = 3):
    today = date.today()
    for i in range(days_ahead):
        ensure_partition_exists(today + timedelta(days=i))