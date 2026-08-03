from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class VehiclePosition(Base):
    __tablename__ = "vehicle_positions"
    __table_args__ = (
        {"postgresql_partition_by": "RANGE (fetched_at)"},
    )
    id = Column(Integer, primary_key=True)
    line_name = Column(String)
    vehicle_type = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    raw_k = Column(BigInteger)  # MPK's internal marker, unclear semantics, store raw
    fetched_at = Column(DateTime(timezone=True), primary_key=True, index=True)  # must be part of PK for partitioning

class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"
    id = Column(Integer, primary_key=True)
    station_id = Column(String)
    temperature_c = Column(Float)
    wind_speed = Column(Float)
    wind_direction = Column(Float)
    humidity_pct = Column(Float)
    precipitation_mm = Column(Float)
    pressure_hpa = Column(Float)
    measurement_date = Column(String)
    measurement_hour = Column(String)
    fetched_at = Column(DateTime(timezone=True), index=True)

class GtfsMeta(Base):
    __tablename__ = "gtfs_meta"
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer)
    loaded_at = Column(DateTime(timezone=True))

class GtfsAgency(Base):
    __tablename__ = "gtfs_agency"
    agency_id = Column(String, primary_key=True)
    agency_name = Column(String)
    agency_url = Column(String)
    agency_timezone = Column(String)

class GtfsRoute(Base):
    __tablename__ = "gtfs_routes"
    route_id = Column(String, primary_key=True)
    route_short_name = Column(String)
    route_long_name = Column(String)
    route_type = Column(String)

class GtfsTrip(Base):
    __tablename__ = "gtfs_trips"
    trip_id = Column(String, primary_key=True)
    route_id = Column(String, index=True)
    service_id = Column(String, index=True)
    trip_headsign = Column(String)
    direction_id = Column(Integer)
    shape_id = Column(String)
    brigade_id = Column(String)
    vehicle_id = Column(String)   # FK-ish to gtfs_vehicle_types.vehicle_type_id
    variant_id = Column(String)

class GtfsStop(Base):
    __tablename__ = "gtfs_stops"
    stop_id = Column(String, primary_key=True)
    stop_name = Column(String)
    stop_lat = Column(Float)
    stop_lon = Column(Float)

class GtfsStopTime(Base):
    __tablename__ = "gtfs_stop_times"
    id = Column(Integer, primary_key=True)  # surrogate — (trip_id, stop_sequence) is the natural key
    trip_id = Column(String, index=True)
    arrival_time = Column(String)     # kept as GTFS text (can exceed 24:00:00), parse later when needed
    departure_time = Column(String)
    stop_id = Column(String, index=True)
    stop_sequence = Column(Integer)

class GtfsCalendar(Base):
    __tablename__ = "gtfs_calendar"
    service_id = Column(String, primary_key=True)
    monday = Column(Integer)
    tuesday = Column(Integer)
    wednesday = Column(Integer)
    thursday = Column(Integer)
    friday = Column(Integer)
    saturday = Column(Integer)
    sunday = Column(Integer)
    start_date = Column(String)
    end_date = Column(String)

class GtfsCalendarDate(Base):
    __tablename__ = "gtfs_calendar_dates"
    id = Column(Integer, primary_key=True)
    service_id = Column(String, index=True)
    date = Column(String)
    exception_type = Column(Integer)

class GtfsVehicleType(Base):
    __tablename__ = "gtfs_vehicle_types"
    vehicle_type_id = Column(String, primary_key=True)
    vehicle_type_name = Column(String)
    vehicle_type_symbol = Column(String)   # "S"/"P"/"M"/"m" — bus vs tram distinction lives here via trips.vehicle_id