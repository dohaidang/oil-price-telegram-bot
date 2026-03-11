import asyncio
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf

from config import Config
from utils.logger import setup_logger

logger = setup_logger("oil_price_service")

# In-memory cache
_cache: dict = {}
_cache_time: Optional[datetime] = None
CACHE_TTL = timedelta(minutes=Config.UPDATE_INTERVAL)


def _fetch_current_prices() -> dict:
    """Fetch current oil prices from Yahoo Finance (synchronous)."""
    result = {}

    tickers_str = " ".join(Config.OIL_TICKERS.values())
    logger.info(f"Fetching prices for: {tickers_str}")

    try:
        tickers = yf.Tickers(tickers_str)

        for oil_type, ticker_symbol in Config.OIL_TICKERS.items():
            try:
                ticker = tickers.tickers[ticker_symbol]
                info = ticker.fast_info

                current_price = info.get("lastPrice", 0) or info.get("last_price", 0)
                prev_close = info.get("previousClose", 0) or info.get("previous_close", 0)

                # If fast_info doesn't work well, try history
                if not current_price:
                    hist = ticker.history(period="2d")
                    if not hist.empty:
                        current_price = hist["Close"].iloc[-1]
                        if len(hist) > 1:
                            prev_close = hist["Close"].iloc[-2]

                change = current_price - prev_close if prev_close else 0
                change_pct = (change / prev_close * 100) if prev_close else 0

                # Get today's high/low/open
                hist_today = ticker.history(period="1d")
                high = hist_today["High"].iloc[-1] if not hist_today.empty else current_price
                low = hist_today["Low"].iloc[-1] if not hist_today.empty else current_price
                open_price = hist_today["Open"].iloc[-1] if not hist_today.empty else current_price

                result[oil_type] = {
                    "name": Config.OIL_NAMES.get(oil_type, oil_type),
                    "price": round(current_price, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_pct, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "open": round(open_price, 2),
                    "prev_close": round(prev_close, 2),
                    "unit": Config.OIL_UNITS.get(oil_type, "USD"),
                    "ticker": ticker_symbol,
                    "timestamp": datetime.now(),
                }

                logger.info(f"{oil_type}: ${current_price:.2f} ({change:+.2f})")

            except Exception as e:
                logger.error(f"Error fetching {oil_type} ({ticker_symbol}): {e}")
                result[oil_type] = {
                    "name": Config.OIL_NAMES.get(oil_type, oil_type),
                    "price": 0,
                    "change": 0,
                    "change_percent": 0,
                    "high": 0,
                    "low": 0,
                    "open": 0,
                    "prev_close": 0,
                    "unit": Config.OIL_UNITS.get(oil_type, "USD"),
                    "ticker": ticker_symbol,
                    "error": str(e),
                }

    except Exception as e:
        logger.error(f"Error fetching tickers: {e}")

    return result


async def get_current_prices(force_refresh: bool = False) -> dict:
    """Get current oil prices with caching."""
    global _cache, _cache_time

    # Return cached data if still valid
    if (
        not force_refresh
        and _cache
        and _cache_time
        and datetime.now() - _cache_time < CACHE_TTL
    ):
        logger.debug("Returning cached prices")
        return _cache

    # yfinance is synchronous, run in thread pool
    loop = asyncio.get_event_loop()
    prices = await loop.run_in_executor(None, _fetch_current_prices)

    # Update cache
    _cache = prices
    _cache_time = datetime.now()

    return prices


async def get_single_price(oil_type: str) -> Optional[dict]:
    """Get price for a single oil type."""
    oil_type = oil_type.upper()

    if oil_type not in Config.OIL_TICKERS:
        return None

    prices = await get_current_prices()
    return prices.get(oil_type)


def _fetch_historical_data(ticker_symbol: str, period: str = "1mo") -> list:
    """Fetch historical price data (synchronous)."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            return []

        data = []
        for date, row in hist.iterrows():
            data.append({
                "date": date.to_pydatetime(),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            })

        return data

    except Exception as e:
        logger.error(f"Error fetching historical data for {ticker_symbol}: {e}")
        return []


async def get_historical_data(oil_type: str, period: str = "1mo") -> list:
    """Get historical price data for an oil type."""
    oil_type = oil_type.upper()
    ticker_symbol = Config.OIL_TICKERS.get(oil_type)

    if not ticker_symbol:
        return []

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_historical_data, ticker_symbol, period)


def get_valid_oil_types() -> list:
    """Get list of valid oil type keys."""
    return list(Config.OIL_TICKERS.keys())


def get_oil_name(oil_type: str) -> str:
    """Get display name for an oil type."""
    return Config.OIL_NAMES.get(oil_type.upper(), oil_type)
