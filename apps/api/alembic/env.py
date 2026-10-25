from alembic import context
from sqlalchemy import create_engine
from app.settings import ROOT
from dotenv import dotenv_values
import os

url = os.getenv("DATABASE_OWNER_URL") or dotenv_values(ROOT / ".env")["DATABASE_OWNER_URL"]
engine = create_engine(url.replace("postgresql://", "postgresql+psycopg://"), pool_pre_ping=True)
with engine.connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()
