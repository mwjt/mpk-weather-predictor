from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from db.session import engine

app = FastAPI()

LOG_FILE = Path(__file__).parent / "logs" / "harvester.log"


def get_stats():
    stats = {}
    with engine.connect() as conn:
        stats["vehicle_positions_total"] = conn.execute(
            text("SELECT count(*) FROM vehicle_positions")
        ).scalar()

        stats["vehicle_positions_last_hour"] = conn.execute(
            text("SELECT count(*) FROM vehicle_positions WHERE fetched_at > now() - interval '1 hour'")
        ).scalar()

        stats["last_vehicle_fetch"] = conn.execute(
            text("SELECT max(fetched_at) FROM vehicle_positions")
        ).scalar()

        stats["weather_snapshots_total"] = conn.execute(
            text("SELECT count(*) FROM weather_snapshots")
        ).scalar()

        stats["last_weather_fetch"] = conn.execute(
            text("SELECT max(fetched_at) FROM weather_snapshots")
        ).scalar()

        stats["gtfs_trips_total"] = conn.execute(
            text("SELECT count(*) FROM gtfs_trips")
        ).scalar()

        gtfs_meta = conn.execute(text("SELECT file_id, loaded_at FROM gtfs_meta LIMIT 1")).first()
        stats["gtfs_file_id"] = gtfs_meta[0] if gtfs_meta else None
        stats["gtfs_loaded_at"] = gtfs_meta[1] if gtfs_meta else None

        partitions = conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE tablename LIKE 'vehicle_positions_%' ORDER BY tablename DESC LIMIT 10"
        )).fetchall()
        stats["recent_partitions"] = [p[0] for p in partitions]

        db_size = conn.execute(text(
            "SELECT pg_size_pretty(pg_database_size(current_database()))"
        )).scalar()
        stats["db_size"] = db_size

    return stats


def get_health_flags(stats: dict) -> list[str]:
    flags = []
    now = datetime.now(timezone.utc)

    if stats["last_vehicle_fetch"] is None or (now - stats["last_vehicle_fetch"]) > timedelta(minutes=5):
        flags.append("⚠️ No vehicle data in the last 5 minutes")

    if stats["last_weather_fetch"] is None or (now - stats["last_weather_fetch"]) > timedelta(minutes=30):
        flags.append("⚠️ No weather data in the last 30 minutes")

    return flags


def tail_log(n_lines: int = 50) -> str:
    if not LOG_FILE.exists():
        return "(no log file found)"
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    return "".join(lines[-n_lines:])


@app.get("/", response_class=HTMLResponse)
def dashboard():
    stats = get_stats()
    flags = get_health_flags(stats)
    log_tail = tail_log()

    flags_html = "".join(f'<div class="flag">{f}</div>' for f in flags) or '<div class="ok">✔ All checks passing</div>'
    partitions_html = "".join(f"<li>{p}</li>" for p in stats["recent_partitions"])

    html = f"""
    <html>
    <head>
        <title>MPK Harvester Dashboard</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: monospace; background: #111; color: #eee; padding: 2rem; }}
            h1 {{ color: #7fd; }}
            .card {{ background: #1c1c1c; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1rem; }}
            .flag {{ color: #f77; }}
            .ok {{ color: #7f7; }}
            table {{ border-collapse: collapse; width: 100%; }}
            td {{ padding: 0.3rem 1rem 0.3rem 0; }}
            pre {{ background: #000; padding: 1rem; overflow-x: auto; max-height: 400px; }}
        </style>
    </head>
    <body>
        <h1>MPK Harvester Dashboard</h1>
        <div class="card">{flags_html}</div>

        <div class="card">
            <h2>Data volume</h2>
            <table>
                <tr><td>Vehicle positions (total)</td><td>{stats['vehicle_positions_total']:,}</td></tr>
                <tr><td>Vehicle positions (last hour)</td><td>{stats['vehicle_positions_last_hour']:,}</td></tr>
                <tr><td>Last vehicle fetch</td><td>{stats['last_vehicle_fetch']}</td></tr>
                <tr><td>Weather snapshots (total)</td><td>{stats['weather_snapshots_total']:,}</td></tr>
                <tr><td>Last weather fetch</td><td>{stats['last_weather_fetch']}</td></tr>
                <tr><td>GTFS trips loaded</td><td>{stats['gtfs_trips_total']:,}</td></tr>
                <tr><td>GTFS file id / loaded at</td><td>{stats['gtfs_file_id']} / {stats['gtfs_loaded_at']}</td></tr>
                <tr><td>DB size</td><td>{stats['db_size']}</td></tr>
            </table>
        </div>

        <div class="card">
            <h2>Recent partitions</h2>
            <ul>{partitions_html}</ul>
        </div>

        <div class="card">
            <h2>Recent log output</h2>
            <pre>{log_tail}</pre>
        </div>

        <p style="color:#666">Auto-refreshes every 30s</p>
    </body>
    </html>
    """
    return html