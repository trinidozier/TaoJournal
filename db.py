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

# Users table — updated to match your expanded registration model
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("first_name", String, nullable=False),
    Column("last_name", String, nullable=False),
    Column("billing_address", String, nullable=False),
    Column("email", String, unique=True, index=True, nullable=False),
    Column("hashed_password", String, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("is_active", Boolean, nullable=False, server_default=text("TRUE")),
)

# Strategies table
strategies = Table(
    "strategies",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_email", String, nullable=False),
    Column("name", String(255), nullable=False),
    Column("description", String, nullable=True),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)

# Trade rules table
trade_rules = Table(
    "trade_rules",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("strategy_id", Integer, nullable=False),
    Column("rule_type", String(50), nullable=False),  # 'entry' or 'exit'
    Column("rule_text", String, nullable=False),
    Column("trade_id", Integer, nullable=True),  # Links to specific trade
    Column("followed", Boolean, server_default=text("FALSE"), nullable=False),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)

# Sync engine for migrations and metadata.create_all
engine = create_engine(DATABASE_URL, echo=True)