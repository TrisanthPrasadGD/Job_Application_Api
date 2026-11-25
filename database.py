import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()
database_url = os.getenv("DATABASE_URL")
database_url = URL.create(
    drivername = "postgresql+psycopg",
    username = "postgres",
    password = os.environ["POSTGRES_PASSWORD"],
    host = "localhost",
    port = 5432,
    database = "job_tracker",
)

engine = create_engine(database_url)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()