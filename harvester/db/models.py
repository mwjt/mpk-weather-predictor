from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class VehiclePosition(Base):
    __tablename__ = "vehicle_positions"
    id = Column(Integer, primary_key=True)
    line_name = Column(String)
    vehicle_type = Column(String)  # "tram" / "bus"
    lat = Column(Float)
    lon = Column(Float)
    raw_k = Column(BigInteger)  # MPK's internal marker, unclear semantics, store raw
    fetched_at = Column(DateTime(timezone=True), index=True)

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