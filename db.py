import os
from urllib.parse import urlparse
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
    inspect  # For table inspection in test
)
from dotenv import load_dotenv

load_dotenv()  # Load DATABASE_URL from .env for local development

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# If not set, fall back to Railway public PostgreSQL URL for testing
if not DATABASE_URL:
    DATABASE_URL = "postgresql+psycopg2://postgres:bvXCbVMYdQZVfJdsYgvRlOCWZaMrEvzC@gondola.proxy.rlwy.net:32273/railway"

# Ensure it's using psycopg2 driver (add +psycopg2 if missing)
parsed_url = urlparse(DATABASE_URL)
if parsed_url.scheme == 'postgresql':
    if '+psycopg2' not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://')

# Debug: Print the DATABASE_URL to verify it's correct (remove this in production)
print(f"Using DATABASE_URL: {DATABASE_URL}")

# Parse to detect if local or remote
parsed_url = urlparse(DATABASE_URL)
is_postgres = parsed_url.scheme.startswith('postgresql')
is_local = 'localhost' in parsed_url.hostname or '127.0.0.1' in parsed_url.hostname

if is_postgres:
    if is_local:
        # Local PostgreSQL: Disable SSL (common for local setups)
        connect_args = {"sslmode": "disable"}
        print("Detected local PostgreSQL: SSL disabled.")
    else:
        # Remote PostgreSQL (e.g., Railway): Require SSL
        connect_args = {"sslmode": "require"}
        print("Detected remote PostgreSQL: SSL required.")
    # For the async database (databases library), use the same URL
    async_database_url = DATABASE_URL
else:
    # Fallback to SQLite if needed (but we expect PostgreSQL)
    connect_args = {}
    async_database_url = "sqlite:///./tao.db"
    print("Using SQLite fallback.")

# Async database connection (used in app)
database = Database(async_database_url)

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
engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args=connect_args
)

# Optional: Test function to verify connection
def test_connection():
    connection = None
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Database connection successful!")
            print(f"Database type: {result.scalar()}")
            # Check if tables exist (for PostgreSQL)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"Existing tables: {tables}")
    except Exception as e:
        print(f"Database connection or inspection failed: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    test_connection()