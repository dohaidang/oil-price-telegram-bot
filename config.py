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
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

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

    # ─── Gold Configuration ──────────────────────────────────
    GOLD_WORLD_TICKERS = {
        "XAUUSD": "XAUUSD=X",
    }

    GOLD_WORLD_NAMES = {
        "XAUUSD": "🥇 Vàng (XAUUSD)",
    }

    GOLD_WORLD_UNITS = {
        "XAUUSD": "USD/oz",
    }

    GOLD_VN_BRANDS = ["SJC", "DOJI", "PNJ"]

    GOLD_VN_SOURCES = {
        # SJC: public online price table
        "SJC": "https://sjc.com.vn/gia-vang-online",
        # DOJI: new online price portal
        "DOJI": "https://giavang.doji.vn/trangchu.html",
        # PNJ: consolidated gold price page (kept as-is; may redirect internally)
        "PNJ": "https://www.pnj.com.vn/blog/gia-vang/",
    }

    # 1 troy oz = 31.1035g, 1 chỉ = 3.75g
    TROY_OZ_GRAMS = 31.1035
    CHI_GRAMS = 3.75

    GOLD_VN_SNAPSHOT_INTERVAL: int = int(os.getenv("GOLD_VN_SNAPSHOT_INTERVAL", "60"))

    # ─── Silver Configuration ────────────────────────────────
    SILVER_WORLD_TICKERS = {
        "XAGUSD": "XAGUSD=X",
    }

    SILVER_WORLD_NAMES = {
        "XAGUSD": "🥈 Bạc (XAGUSD)",
    }

    SILVER_WORLD_UNITS = {
        "XAGUSD": "USD/oz",
    }

    SILVER_VN_BRANDS = ["SJC", "DOJI", "PNJ"]

    SILVER_VN_SOURCES = {
        # SJC: same page as gold, search for "bạc" rows
        "SJC": "https://sjc.com.vn/giavang/textContent.php",
        # DOJI: dedicated silver page (may not exist — graceful fallback)
        "DOJI": "https://www.doji.vn/bang-gia-bac/",
        # PNJ: gold/silver combined page (search for silver rows)
        "PNJ": "https://www.pnj.com.vn/blog/gia-vang/",
    }

    SILVER_VN_SNAPSHOT_INTERVAL: int = int(os.getenv("SILVER_VN_SNAPSHOT_INTERVAL", "60"))

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required. Set it in .env file.")
        return True
