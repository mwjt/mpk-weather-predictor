import csv
import io
import logging
import zipfile

import psycopg2
import psycopg2.extras

log = logging.getLogger("gtfs_loader")

# filename -> (table, ordered columns to keep)
TABLE_COLUMNS = {
    "agency.txt": ("gtfs_agency", ["agency_id", "agency_name", "agency_url", "agency_timezone"]),
    "routes.txt": ("gtfs_routes", ["route_id", "route_short_name", "route_long_name", "route_type"]),
    "trips.txt": ("gtfs_trips", ["route_id", "service_id", "trip_id", "trip_headsign", "direction_id", "shape_id", "brigade_id", "vehicle_id", "variant_id"]),
    "stops.txt": ("gtfs_stops", ["stop_id", "stop_name", "stop_lat", "stop_lon"]),
    "stop_times.txt": ("gtfs_stop_times", ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"]),
    "calendar.txt": ("gtfs_calendar", ["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"]),
    "calendar_dates.txt": ("gtfs_calendar_dates", ["service_id", "date", "exception_type"]),
    "vehicle_types.txt": ("gtfs_vehicle_types", ["vehicle_type_id", "vehicle_type_name", "vehicle_type_symbol"]),
}
# Intentionally skipped for now: shapes.txt, variants.txt, control_stops.txt,
# contracts_ext.txt, route_types.txt — map-geometry / internal fields we don't need yet.

def load_gtfs_zip(zip_path: str, conn_str: str):
    conn = psycopg2.connect(conn_str)
    conn.autocommit = False
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for filename, (table, columns) in TABLE_COLUMNS.items():
                if filename not in zf.namelist():
                    log.warning(f"{filename} not found in zip, skipping")
                    continue

                with zf.open(filename) as f:
                    text = io.TextIOWrapper(f, encoding="utf-8-sig")
                    reader = csv.DictReader(text)
                    # note: skips the surrogate "id" column present on some tables —
                    # Postgres SERIAL/IDENTITY fills that in automatically
                    insert_cols = [c for c in columns if c != "id"]
                    rows = [
                        tuple(row.get(col) or None for col in insert_cols)
                        for row in reader
                    ]

                cur = conn.cursor()
                cur.execute(f"TRUNCATE TABLE {table}")
                if rows:
                    psycopg2.extras.execute_values(
                        cur,
                        f"INSERT INTO {table} ({', '.join(insert_cols)}) VALUES %s",
                        rows,
                        page_size=5000,
                    )
                cur.close()
                log.info(f"loaded {len(rows)} rows into {table}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()