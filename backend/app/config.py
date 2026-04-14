import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_oMzlU85mfZCI@ep-cold-frog-a1jh032w-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
)
APP_NAME: str = "Causal Financial Knowledge Graph"
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
