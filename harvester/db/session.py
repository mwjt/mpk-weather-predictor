import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mpk:mpk@localhost:5432/mpk_harvester")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)