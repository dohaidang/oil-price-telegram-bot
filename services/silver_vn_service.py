import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from config import Config
from models.database import insert_silver_vn_price
from utils.logger import setup_logger

logger = setup_logger("silver_vn_service")

_vn_silver_cache: dict = {}
_vn_silver_cache_time: Optional[datetime] = None
VN_SILVER_CACHE_TTL = timedelta(minutes=15)

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
    Silver prices are typically shown in VND/lượng (100g) or VND/chỉ (3.75g).
    """
    if price <= 0:
        return 0

    hint = unit_hint.lower()
    if "chỉ" in hint:
        return price

    if price < 100_000:
        price_per_luong = price * 1000
    else:
        price_per_luong = price

    return price_per_luong // LUONG_TO_CHI


# ═════════════════════════════════════════════════════════════
#  SJC Scraper (silver rows)
# ═════════════════════════════════════════════════════════════

def _scrape_sjc_silver() -> dict:
    """Scrape SJC silver prices from sjc.com.vn.
    The same page has gold and silver. We look for rows containing 'bạc'.
    """
    result = {"buy": 0, "sell": 0, "source": "sjc.com.vn", "update_time": ""}

    try:
        url = Config.SILVER_VN_SOURCES["SJC"]
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=HEADERS)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                name = cells[0].get_text(strip=True).lower()
                # Look for silver keyword
                if "bạc" in name or "bac" in name or "ag" in name:
                    buy_raw = _parse_price(cells[1].get_text(strip=True))
                    sell_raw = _parse_price(cells[2].get_text(strip=True))
                    if buy_raw > 0 or sell_raw > 0:
                        result["buy"] = _normalize_to_chi(buy_raw)
                        result["sell"] = _normalize_to_chi(sell_raw)
                        break

        result["update_time"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        if result["buy"] == 0 and result["sell"] == 0:
            logger.info("SJC silver: no data found on page")
        else:
            logger.info(f"SJC silver: buy={result['buy']}, sell={result['sell']}")

    except Exception as e:
        logger.error(f"Error scraping SJC silver: {e}")

    return result


# ═════════════════════════════════════════════════════════════
#  DOJI Scraper (silver page)
# ═════════════════════════════════════════════════════════════

def _scrape_doji_silver() -> dict:
    """Scrape DOJI silver prices from doji.vn/bang-gia-bac/.
    If the page doesn't exist or has no data, returns zeros gracefully.
    """
    result = {"buy": 0, "sell": 0, "source": "doji.vn", "update_time": ""}

    try:
        url = Config.SILVER_VN_SOURCES["DOJI"]
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=HEADERS)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                name = cells[0].get_text(strip=True).lower()
                if "bạc" in name or "bac" in name or "ag" in name or len(cells[0].get_text(strip=True)) > 0:
                    buy_raw = _parse_price(cells[1].get_text(strip=True))
                    sell_raw = _parse_price(cells[2].get_text(strip=True))
                    if buy_raw > 0:
                        result["buy"] = _normalize_to_chi(buy_raw)
                        result["sell"] = _normalize_to_chi(sell_raw)
                        break

        result["update_time"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        if result["buy"] == 0:
            logger.info("DOJI silver: no data found")
        else:
            logger.info(f"DOJI silver: buy={result['buy']}, sell={result['sell']}")

    except httpx.HTTPStatusError as e:
        # Page may return 404 — not a critical error
        logger.info(f"DOJI silver page not available ({e.response.status_code})")
    except Exception as e:
        logger.error(f"Error scraping DOJI silver: {e}")

    return result


# ═════════════════════════════════════════════════════════════
#  PNJ Scraper (silver rows in gold page)
# ═════════════════════════════════════════════════════════════

def _scrape_pnj_silver() -> dict:
    """Scrape PNJ silver prices from pnj.com.vn.
    Look for rows containing 'bạc' on the gold+silver combined page.
    """
    result = {"buy": 0, "sell": 0, "source": "pnj.com.vn", "update_time": ""}

    try:
        url = Config.SILVER_VN_SOURCES["PNJ"]
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=HEADERS)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                name = cells[0].get_text(strip=True).lower()
                if "bạc" in name or "bac" in name:
                    buy_raw = _parse_price(cells[1].get_text(strip=True))
                    sell_raw = _parse_price(cells[2].get_text(strip=True))
                    if buy_raw > 0:
                        result["buy"] = _normalize_to_chi(buy_raw)
                        result["sell"] = _normalize_to_chi(sell_raw)
                        break

        result["update_time"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        if result["buy"] == 0:
            logger.info("PNJ silver: no data found on page")
        else:
            logger.info(f"PNJ silver: buy={result['buy']}, sell={result['sell']}")

    except Exception as e:
        logger.error(f"Error scraping PNJ silver: {e}")

    return result


# ═════════════════════════════════════════════════════════════
#  Main API
# ═════════════════════════════════════════════════════════════

SCRAPERS = {
    "SJC": _scrape_sjc_silver,
    "DOJI": _scrape_doji_silver,
    "PNJ": _scrape_pnj_silver,
}


def _fetch_all_silver_vn() -> dict:
    """Fetch silver VN prices from all brands (synchronous)."""
    result = {}
    for brand in Config.SILVER_VN_BRANDS:
        scraper = SCRAPERS.get(brand)
        if scraper:
            data = scraper()
            result[brand] = data
    return result


async def get_silver_vn_prices(force_refresh: bool = False) -> dict:
    """Get silver VN prices with caching. Returns {brand: {buy, sell, source, update_time}}.
    Brands with no data return buy=0, sell=0 — handler shows 'chưa có dữ liệu bạc'.
    """
    global _vn_silver_cache, _vn_silver_cache_time

    if (
        not force_refresh
        and _vn_silver_cache
        and _vn_silver_cache_time
        and datetime.now() - _vn_silver_cache_time < VN_SILVER_CACHE_TTL
    ):
        logger.debug("Returning cached silver VN prices")
        return _vn_silver_cache

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch_all_silver_vn)

    # Cache even if all zeros — avoids hammering unresponsive pages
    _vn_silver_cache = data
    _vn_silver_cache_time = datetime.now()

    return data


async def snapshot_silver_vn_to_db():
    """Fetch current silver VN prices and save to DB for historical charting.
    Only saves rows where price > 0.
    """
    data = await get_silver_vn_prices(force_refresh=True)

    saved = 0
    for brand, prices in data.items():
        for price_type in ("buy", "sell"):
            price_val = prices.get(price_type, 0)
            if price_val > 0:
                await insert_silver_vn_price(
                    brand=brand,
                    price_type=price_type,
                    price_per_chi=price_val,
                    source=prices.get("source", ""),
                )
                saved += 1

    logger.info(f"Silver VN prices snapshot saved to DB ({saved} rows)")
