import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

settings = Settings()


