import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings:
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    ZERODHA_API_KEY: str = os.environ.get("ZERODHA_API_KEY", "")
    ZERODHA_API_SECRET: str = os.environ.get("ZERODHA_API_SECRET", "")


settings = Settings()

