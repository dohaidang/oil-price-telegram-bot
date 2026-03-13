import asyncio
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf

from config import Config
from utils.logger import setup_logger

logger = setup_logger("silver_world_service")

_cache: dict = {}
_cache_time: Optional[datetime] = None
CACHE_TTL = timedelta(minutes=Config.UPDATE_INTERVAL)


def _fetch_silver_world_prices() -> dict:
    """Fetch silver world prices from Yahoo Finance (synchronous)."""
    result = {}

    tickers_str = " ".join(Config.SILVER_WORLD_TICKERS.values())
    logger.info(f"Fetching silver prices for: {tickers_str}")

    try:
        tickers = yf.Tickers(tickers_str)

        for silver_type, ticker_symbol in Config.SILVER_WORLD_TICKERS.items():
            try:
                ticker = tickers.tickers[ticker_symbol]
                info = ticker.fast_info

                current_price = info.get("lastPrice", 0) or info.get("last_price", 0)
                prev_close = info.get("previousClose", 0) or info.get("previous_close", 0)

                if not current_price:
                    hist = ticker.history(period="2d")
                    if not hist.empty:
                        current_price = hist["Close"].iloc[-1]
                        if len(hist) > 1:
                            prev_close = hist["Close"].iloc[-2]

                change = current_price - prev_close if prev_close else 0
                change_pct = (change / prev_close * 100) if prev_close else 0

                hist_today = ticker.history(period="1d")
                high = hist_today["High"].iloc[-1] if not hist_today.empty else current_price
                low = hist_today["Low"].iloc[-1] if not hist_today.empty else current_price
                open_price = hist_today["Open"].iloc[-1] if not hist_today.empty else current_price

                result[silver_type] = {
                    "name": Config.SILVER_WORLD_NAMES.get(silver_type, silver_type),
                    "price": round(current_price, 4),
                    "change": round(change, 4),
                    "change_percent": round(change_pct, 2),
                    "high": round(high, 4),
                    "low": round(low, 4),
                    "open": round(open_price, 4),
                    "prev_close": round(prev_close, 4),
                    "unit": Config.SILVER_WORLD_UNITS.get(silver_type, "USD/oz"),
                    "ticker": ticker_symbol,
                    "timestamp": datetime.now(),
                }

                logger.info(f"{silver_type}: ${current_price:.4f} ({change:+.4f})")

            except Exception as e:
                logger.error(f"Error fetching {silver_type} ({ticker_symbol}): {e}")
                result[silver_type] = {
                    "name": Config.SILVER_WORLD_NAMES.get(silver_type, silver_type),
                    "price": 0, "change": 0, "change_percent": 0,
                    "high": 0, "low": 0, "open": 0, "prev_close": 0,
                    "unit": Config.SILVER_WORLD_UNITS.get(silver_type, "USD/oz"),
                    "ticker": ticker_symbol,
                    "error": str(e),
                }

    except Exception as e:
        logger.error(f"Error fetching silver tickers: {e}")

    return result


async def get_silver_world_prices(force_refresh: bool = False) -> dict:
    """Get silver world prices with caching."""
    global _cache, _cache_time

    if (
        not force_refresh
        and _cache
        and _cache_time
        and datetime.now() - _cache_time < CACHE_TTL
    ):
        logger.debug("Returning cached silver world prices")
        return _cache

    loop = asyncio.get_event_loop()
    prices = await loop.run_in_executor(None, _fetch_silver_world_prices)

    _cache = prices
    _cache_time = datetime.now()
    return prices


def _fetch_silver_history(ticker_symbol: str, period: str = "1mo") -> list:
    """Fetch historical silver price data (synchronous)."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            return []

        data = []
        for date, row in hist.iterrows():
            data.append({
                "date": date.to_pydatetime(),
                "open": round(row["Open"], 4),
                "high": round(row["High"], 4),
                "low": round(row["Low"], 4),
                "close": round(row["Close"], 4),
                "volume": int(row["Volume"]),
            })
        return data

    except Exception as e:
        logger.error(f"Error fetching silver history for {ticker_symbol}: {e}")
        return []


async def get_silver_world_history(symbol: str = "XAGUSD", period: str = "1mo") -> list:
    """Get historical silver price data."""
    ticker_symbol = Config.SILVER_WORLD_TICKERS.get(symbol.upper())
    if not ticker_symbol:
        return []

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_silver_history, ticker_symbol, period)


def convert_usd_oz_to_vnd_chi(usd_per_oz: float, usd_vnd_rate: float) -> int:
    """Convert USD/oz to VND/chỉ using VCB rate.
    1 chỉ = 3.75g, 1 troy oz = 31.1035g
    Same formula as gold — units are identical.
    """
    if usd_per_oz <= 0 or usd_vnd_rate <= 0:
        return 0
    vnd_per_oz = usd_per_oz * usd_vnd_rate
    vnd_per_chi = vnd_per_oz * (Config.CHI_GRAMS / Config.TROY_OZ_GRAMS)
    return round(vnd_per_chi)
