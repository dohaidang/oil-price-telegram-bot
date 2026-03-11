import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot configuration loaded from environment variables."""

    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # API Keys
    CRUDE_API_KEY: str = os.getenv("CRUDE_API_KEY", "")
    EIA_API_KEY: str = os.getenv("EIA_API_KEY", "")

    # Settings
    UPDATE_INTERVAL: int = int(os.getenv("UPDATE_INTERVAL", "5"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Database
    DB_PATH: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oil_bot.db")

    # Oil type tickers for yfinance
    OIL_TICKERS = {
        "WTI": "CL=F",           # WTI Crude Oil Futures
        "BRENT": "BZ=F",         # Brent Crude Oil Futures
        "NATURAL_GAS": "NG=F",   # Natural Gas Futures
        "HEATING_OIL": "HO=F",   # Heating Oil Futures
        "GASOLINE": "RB=F",      # RBOB Gasoline Futures
    }

    # Display names (Vietnamese)
    OIL_NAMES = {
        "WTI": "🛢️ WTI Crude",
        "BRENT": "🛢️ Brent Crude",
        "NATURAL_GAS": "🔥 Khí tự nhiên",
        "HEATING_OIL": "🏭 Dầu sưởi",
        "GASOLINE": "⛽ Xăng RBOB",
    }

    # Units
    OIL_UNITS = {
        "WTI": "USD/thùng",
        "BRENT": "USD/thùng",
        "NATURAL_GAS": "USD/MMBtu",
        "HEATING_OIL": "USD/gallon",
        "GASOLINE": "USD/gallon",
    }

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required. Set it in .env file.")
        return True
