# db.py

import os
from databases import Database
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    Float,
    String,
    DateTime,
    Boolean,
    create_engine,
    text,
)
from dotenv import load_dotenv

load_dotenv()  # Load DATABASE_URL from .env

# Default to SQLite if not set
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tao.db")

# Async database connection (used in app)
database = Database(DATABASE_URL)

# Shared metadata for Alembic and SQLAlchemy
metadata = MetaData()

# Trades table
trades = Table(
    "trades",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("buy_price", Float, nullable=False),
    Column("sell_price", Float, nullable=False),
    Column("stop", Float, nullable=False),
    Column("direction", String, nullable=False),
    Column("pnl", Float, nullable=False),
    Column("r_multiple", Float, nullable=False),
    Column("timestamp", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

# Users table
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("email", String, unique=True, index=True, nullable=False),
    Column("hashed_password", String, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("is_active", Boolean, nullable=False, server_default=text("1")),
)

# Sync engine for migrations and metadata.create_all
engine = create_engine(DATABASE_URL, echo=True)
