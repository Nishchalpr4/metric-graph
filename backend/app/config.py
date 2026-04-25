import os
from dotenv import load_dotenv

load_dotenv()

# Database URL must be set in .env or Render environment variable
_raw_url: str = os.getenv("DATABASE_URL", "")
if not _raw_url:
    raise ValueError("❌ ERROR: DATABASE_URL not found in environment or .env file!")

# Fix 1: SQLAlchemy requires 'postgresql://' not 'postgres://'
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)

# Fix 2: Strip 'channel_binding=require' - not supported by SQLAlchemy/psycopg2
if "channel_binding=require" in _raw_url:
    _raw_url = _raw_url.replace("&channel_binding=require", "").replace("channel_binding=require&", "").replace("channel_binding=require", "")
    # Clean up trailing ? or & if nothing else remains after stripping
    if _raw_url.endswith("?"):
        _raw_url = _raw_url[:-1]

DATABASE_URL: str = _raw_url

APP_NAME: str = "Causal Financial Knowledge Graph"
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
