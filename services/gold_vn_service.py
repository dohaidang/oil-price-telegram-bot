import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from config import Config
from models.database import insert_gold_vn_price
from utils.logger import setup_logger

logger = setup_logger("gold_vn_service")

_vn_gold_cache: dict = {}
_vn_gold_cache_time: Optional[datetime] = None
VN_GOLD_CACHE_TTL = timedelta(minutes=5)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

LUONG_TO_CHI = 10  # 1 lượng = 10 chỉ


def _parse_price(text: str) -> int:
    """Parse Vietnamese price format: '29.520' or '29,520' or '29520000' -> int."""
    text = text.strip().replace("₫", "").replace("đ", "").replace("VNĐ", "").strip()
    cleaned = re.sub(r"[.,\s]", "", text)
    try:
        return int(cleaned)
    except (ValueError, TypeError):
        return 0


def _normalize_to_chi(price: int, unit_hint: str = "") -> int:
    """Normalize price to VND/chỉ.
    SJC/DOJI/PNJ typically show prices in VND/lượng (millions).
    If price > 1,000,000 and looks like per-lượng, divide by 10.
    """
    if price <= 0:
        return 0

    hint = unit_hint.lower()
    if "chỉ" in hint:
        return price

    # Prices shown as e.g. "8,250" meaning 8,250,000 VND/lượng
    # or "82,500,000" VND/lượng
    if price < 100_000:
        # Likely in thousands (e.g. 8250 = 8,250,000 VND/lượng)
        price_per_luong = price * 1000
    elif price < 1_000_000:
        # Likely in ten-thousands (e.g. 82500 = 82,500,000?) — unlikely
        price_per_luong = price * 1000
    else:
        price_per_luong = price

    return price_per_luong // LUONG_TO_CHI


# ═════════════════════════════════════════════════════════════
#  SJC Scraper
# ═════════════════════════════════════════════════════════════

def _scrape_sjc() -> dict:
    """Scrape SJC gold prices from sjc.com.vn."""
    result = {"buy": 0, "sell": 0, "source": "sjc.com.vn", "update_time": ""}

    try:
        url = Config.GOLD_VN_SOURCES["SJC"]
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=HEADERS)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                name = cells[0].get_text(strip=True).lower()
                if "sjc" in name and ("1l" in name or "miếng" in name or "lượng" in name or "1 lượng" in name):
                    buy_raw = _parse_price(cells[1].get_text(strip=True))
                    sell_raw = _parse_price(cells[2].get_text(strip=True))

                    result["buy"] = _normalize_to_chi(buy_raw)
                    result["sell"] = _normalize_to_chi(sell_raw)
                    break

        if result["buy"] == 0 and result["sell"] == 0:
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 3:
                    name = cells[0].get_text(strip=True).lower()
                    if "sjc" in name:
                        buy_raw = _parse_price(cells[1].get_text(strip=True))
                        sell_raw = _parse_price(cells[2].get_text(strip=True))
                        if buy_raw > 0:
                            result["buy"] = _normalize_to_chi(buy_raw)
                            result["sell"] = _normalize_to_chi(sell_raw)
                            break

        result["update_time"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        logger.info(f"SJC: buy={result['buy']}, sell={result['sell']}")

    except Exception as e:
        logger.error(f"Error scraping SJC: {e}")

    return result


# ═════════════════════════════════════════════════════════════
#  DOJI Scraper
# ═════════════════════════════════════════════════════════════

def _scrape_doji() -> dict:
    """Scrape DOJI gold prices from doji.vn."""
    result = {"buy": 0, "sell": 0, "source": "doji.vn", "update_time": ""}

    try:
        url = Config.GOLD_VN_SOURCES["DOJI"]
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=HEADERS)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                name = cells[0].get_text(strip=True).lower()
                if "sjc" in name or ("vàng miếng" in name) or ("1l" in name):
                    buy_raw = _parse_price(cells[1].get_text(strip=True))
                    sell_raw = _parse_price(cells[2].get_text(strip=True))
                    if buy_raw > 0:
                        result["buy"] = _normalize_to_chi(buy_raw)
                        result["sell"] = _normalize_to_chi(sell_raw)
                        break

        result["update_time"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        logger.info(f"DOJI: buy={result['buy']}, sell={result['sell']}")

    except Exception as e:
        logger.error(f"Error scraping DOJI: {e}")

    return result


# ═════════════════════════════════════════════════════════════
#  PNJ Scraper
# ═════════════════════════════════════════════════════════════

def _scrape_pnj() -> dict:
    """Scrape PNJ gold prices from pnj.com.vn."""
    result = {"buy": 0, "sell": 0, "source": "pnj.com.vn", "update_time": ""}

    try:
        url = Config.GOLD_VN_SOURCES["PNJ"]
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=HEADERS)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                name = cells[0].get_text(strip=True).lower()
                if "sjc" in name or "vàng miếng" in name:
                    buy_raw = _parse_price(cells[1].get_text(strip=True))
                    sell_raw = _parse_price(cells[2].get_text(strip=True))
                    if buy_raw > 0:
                        result["buy"] = _normalize_to_chi(buy_raw)
                        result["sell"] = _normalize_to_chi(sell_raw)
                        break

        result["update_time"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        logger.info(f"PNJ: buy={result['buy']}, sell={result['sell']}")

    except Exception as e:
        logger.error(f"Error scraping PNJ: {e}")

    return result


# ═════════════════════════════════════════════════════════════
#  Main API
# ═════════════════════════════════════════════════════════════

SCRAPERS = {
    "SJC": _scrape_sjc,
    "DOJI": _scrape_doji,
    "PNJ": _scrape_pnj,
}


def _fetch_all_gold_vn() -> dict:
    """Fetch gold VN prices from all brands (synchronous)."""
    result = {}
    for brand in Config.GOLD_VN_BRANDS:
        scraper = SCRAPERS.get(brand)
        if scraper:
            data = scraper()
            result[brand] = data
    return result


async def get_gold_vn_prices(force_refresh: bool = False) -> dict:
    """Get gold VN prices with caching. Returns {brand: {buy, sell, source, update_time}}."""
    global _vn_gold_cache, _vn_gold_cache_time

    if (
        not force_refresh
        and _vn_gold_cache
        and _vn_gold_cache_time
        and datetime.now() - _vn_gold_cache_time < VN_GOLD_CACHE_TTL
    ):
        logger.debug("Returning cached gold VN prices")
        return _vn_gold_cache

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch_all_gold_vn)

    # Check if the new scrape produced any usable data
    has_data = any(
        (v.get("sell", 0) > 0) or (v.get("buy", 0) > 0) for v in data.values()
    )
    if has_data:
        _vn_gold_cache = data
        _vn_gold_cache_time = datetime.now()
        return data

    # If no data but we have previous cache, fall back to cached values
    if _vn_gold_cache:
        logger.warning("Gold VN scrape returned no data; falling back to cached values")
        return _vn_gold_cache

    # No cache and no data — return raw (zeros) result
    return data


async def snapshot_gold_vn_to_db():
    """Fetch current gold VN prices and save to DB for historical charting."""
    data = await get_gold_vn_prices(force_refresh=True)

    for brand, prices in data.items():
        for price_type in ("buy", "sell"):
            price_val = prices.get(price_type, 0)
            if price_val > 0:
                await insert_gold_vn_price(
                    brand=brand,
                    price_type=price_type,
                    price_per_chi=price_val,
                    source=prices.get("source", ""),
                )

    logger.info("Gold VN prices snapshot saved to DB")
