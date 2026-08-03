# mpk-weather-predictor

Predicting Wrocław public transit delay risk by correlating live vehicle
position data with weather conditions.

## Idea

MPK Wrocław (trams/buses) publishes live vehicle positions via a public
endpoint, and IMGW (Poland's meteorological institute) publishes public
weather station data. Neither dataset alone tells you much — but combined
and observed over time, they should let us model something useful: how
does weather (rain, wind, temperature, snow) actually affect delay
likelihood on specific lines/routes?

Long-term goal: predict "how likely is my tram/bus to be delayed right
now, given current weather" — and track how good that prediction actually
is over time.

## Project status

Early stage — currently focused on **data collection only**. No
prediction model or frontend yet. The priority right now is running a
reliable 24/7 harvester to build up enough historical data before any
modeling makes sense.

## Structure
- `harvester/` - 24/7 data collection service

Planned, not yet built:
- `backend/` — API + ML model serving
- `frontend/` — dashboard/map showing predictions

## Harvester

The harvester polls two public data sources on a schedule and stores raw
snapshots in Postgres:

- **Vehicle positions** — `POST https://mpk.wroc.pl/bus_position`, polled
  every 60s for a fixed set of tracked lines.
- **Weather** — `GET https://danepubliczne.imgw.pl/api/data/synop/station/wroclaw`,
  polled every 15 minutes.

Designed to run unattended on a small always-on machine (currently an
N100 mini PC running Arch), via a systemd service, with training/modeling
happening separately on a more powerful machine that connects to the same
Postgres instance (e.g. over Tailscale).

### Setup

```bash
cd harvester
./install.sh
```

This creates a venv, installs dependencies, brings up Postgres via
Docker Compose, and installs + starts the `mpk-harvester` systemd service.

### Useful commands

```bash
systemctl status mpk-harvester      # check it's running
journalctl -u mpk-harvester -f      # tail logs
docker compose -f harvester/docker-compose.yml down   # stop postgres
```

### Config

Set `DATABASE_URL` (defaults to a local Postgres instance, see
`docker-compose.yml`) via environment variable or in the systemd unit
file.

### Data collected

- `vehicle_positions` — line, vehicle type, lat/lon, timestamp
- `weather_snapshots` — temperature, wind, humidity, precipitation,
  pressure, timestamp

## Notes / caveats

- The MPK endpoint is undocumented/community-reverse-engineered, not an
  official API — it may change without notice.
- No delay ground-truth is collected yet (only raw positions); deriving
  actual delay events from position data vs. scheduled GTFS timetables
  is a planned next step.
- Data volume needs to reach a meaningful time span (weeks, ideally
  covering varied weather) before any model is worth training.

## License

TBD