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
    create_engine,
    text,
)
from dotenv import load_dotenv

load_dotenv()  # load DATABASE_URL from .env

DATABASE_URL = os.getenv("DATABASE_URL")
database = Database(DATABASE_URL)

metadata = MetaData()

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
    Column(
        "timestamp",
        DateTime,
        nullable=False,
        server_default=text("now()")    # ← auto-populate on insert
    ),
)

# sync engine, used for migrations or metadata.create_all(engine)
engine = create_engine(DATABASE_URL)
