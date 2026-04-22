import os
from dotenv import load_dotenv

load_dotenv()

# Database URL must be set in .env - no hardcoded fallback
DATABASE_URL: str = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ ERROR: DATABASE_URL not found in .env file!")

APP_NAME: str = "Causal Financial Knowledge Graph"
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
