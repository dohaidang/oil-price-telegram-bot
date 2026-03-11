import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from utils.logger import setup_logger

logger = setup_logger("vn_price_service")

# ─── Cache ───────────────────────────────────────────────────
_vn_cache: dict = {}
_vn_cache_time: Optional[datetime] = None
_rate_cache: dict = {}
_rate_cache_time: Optional[datetime] = None

VN_CACHE_TTL = timedelta(hours=6)
RATE_CACHE_TTL = timedelta(minutes=30)

# ─── URLs ────────────────────────────────────────────────────
PETROLIMEX_URL = "https://www.petrolimex.com.vn/"
VCB_EXCHANGE_RATE_URL = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx?b=68"

# ─── Product display config ─────────────────────────────────
VN_FUEL_NAMES = {
    "Xăng RON 95-V": "⛽ Xăng RON 95-V",
    "Xăng RON 95-III": "⛽ Xăng RON 95-III",
    "Xăng E10 RON 95-III": "⛽ Xăng E10 RON 95-III",
    "Xăng E5 RON 92-II": "⛽ Xăng E5 RON 92",
    "DO 0,001S-V": "🏭 Diesel 0,001S-V",
    "DO 0,05S-II": "🏭 Diesel 0,05S-II",
    "Dầu hỏa 2-K": "🪔 Dầu hỏa",
    # Fallback keys (partial match)
    "RON 95-V": "⛽ Xăng RON 95-V",
    "RON 95-III": "⛽ Xăng RON 95-III",
    "E5 RON 92-II": "⛽ Xăng E5 RON 92",
    "Dầu hỏa": "🪔 Dầu hỏa",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


# ═════════════════════════════════════════════════════════════
#  Petrolimex Scraper
# ═════════════════════════════════════════════════════════════

def _scrape_petrolimex() -> dict:
    """
    Scrape fuel prices from Petrolimex website header table.
    Returns dict with fuel type -> price data.
    """
    result = {
        "prices": {},
        "update_time": "",
        "source": "Petrolimex",
        "error": None,
    }

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(PETROLIMEX_URL, headers=HEADERS)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # ── Strategy 1: Header price table ──
        price_div = soup.find("div", class_="header__pricePetrol")
        if price_div:
            table = price_div.find("table")
            if table:
                rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 3:
                        name = cells[0].get_text(strip=True)
                        price_v1 = cells[1].get_text(strip=True)  # Vùng 1
                        price_v2 = cells[2].get_text(strip=True)  # Vùng 2

                        # Parse price: "29.520" -> 29520
                        price_v1_int = _parse_vn_price(price_v1)
                        price_v2_int = _parse_vn_price(price_v2)

                        if price_v1_int > 0:
                            result["prices"][name] = {
                                "name": VN_FUEL_NAMES.get(name, f"🛢️ {name}"),
                                "price_v1": price_v1_int,
                                "price_v2": price_v2_int,
                                "price_v1_formatted": f"{price_v1_int:,.0f}",
                                "price_v2_formatted": f"{price_v2_int:,.0f}",
                                "unit": "đồng/lít",
                            }

            # Update time
            info_p = price_div.find("p", class_="f-info")
            if info_p:
                result["update_time"] = info_p.get_text(strip=True)

        # ── Strategy 2: Fallback - scan article tables ──
        if not result["prices"]:
            logger.warning("Header table not found, trying article tables...")
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        text = cells[0].get_text(strip=True)
                        if any(kw in text.lower() for kw in ["ron", "diesel", "dầu hỏa", "do 0"]):
                            price_text = cells[1].get_text(strip=True)
                            price_int = _parse_vn_price(price_text)
                            if price_int > 0:
                                result["prices"][text] = {
                                    "name": VN_FUEL_NAMES.get(text, f"🛢️ {text}"),
                                    "price_v1": price_int,
                                    "price_v2": 0,
                                    "price_v1_formatted": f"{price_int:,.0f}",
                                    "price_v2_formatted": "N/A",
                                    "unit": "đồng/lít",
                                }

        if not result["prices"]:
            result["error"] = "Không tìm thấy bảng giá trên website Petrolimex"

        logger.info(f"Scraped {len(result['prices'])} fuel types from Petrolimex")

    except httpx.HTTPError as e:
        result["error"] = f"Lỗi kết nối Petrolimex: {e}"
        logger.error(f"HTTP error scraping Petrolimex: {e}")
    except Exception as e:
        result["error"] = f"Lỗi xử lý dữ liệu: {e}"
        logger.error(f"Error scraping Petrolimex: {e}")

    return result


def _parse_vn_price(text: str) -> int:
    """Parse Vietnamese price format: '29.520' or '29,520' -> 29520."""
    text = text.strip()
    # Remove dots and commas used as thousand separators
    cleaned = re.sub(r"[.,]", "", text)
    try:
        return int(cleaned)
    except (ValueError, TypeError):
        return 0


async def get_vn_fuel_prices(force_refresh: bool = False) -> dict:
    """Get Vietnam fuel prices with 6-hour cache."""
    global _vn_cache, _vn_cache_time

    if (
        not force_refresh
        and _vn_cache
        and _vn_cache.get("prices")
        and _vn_cache_time
        and datetime.now() - _vn_cache_time < VN_CACHE_TTL
    ):
        logger.debug("Returning cached VN fuel prices")
        return _vn_cache

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _scrape_petrolimex)

    if data.get("prices"):
        _vn_cache = data
        _vn_cache_time = datetime.now()

    return data


# ═════════════════════════════════════════════════════════════
#  Vietcombank Exchange Rate
# ═════════════════════════════════════════════════════════════

def _fetch_vcb_exchange_rate() -> dict:
    """Fetch USD/VND exchange rate from Vietcombank XML feed."""
    result = {"buy": 0, "sell": 0, "transfer": 0, "datetime": "", "error": None}

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(VCB_EXCHANGE_RATE_URL, headers=HEADERS)
            response.raise_for_status()

        root = ET.fromstring(response.text)
        dt_elem = root.find("DateTime")
        if dt_elem is not None:
            result["datetime"] = dt_elem.text.strip()

        for exrate in root.findall("Exrate"):
            code = exrate.get("CurrencyCode", "").strip()
            if code == "USD":
                result["buy"] = _parse_vn_price(exrate.get("Buy", "0"))
                result["sell"] = _parse_vn_price(exrate.get("Sell", "0"))
                result["transfer"] = _parse_vn_price(exrate.get("Transfer", "0"))
                break

        if result["sell"] == 0:
            result["error"] = "Không tìm thấy tỷ giá USD"

        logger.info(f"VCB exchange rate - Buy: {result['buy']}, Sell: {result['sell']}")

    except Exception as e:
        result["error"] = f"Lỗi lấy tỷ giá: {e}"
        logger.error(f"Error fetching VCB exchange rate: {e}")

    return result


async def get_usd_vnd_rate(force_refresh: bool = False) -> dict:
    """Get USD/VND exchange rate with 30-min cache."""
    global _rate_cache, _rate_cache_time

    if (
        not force_refresh
        and _rate_cache
        and _rate_cache.get("sell", 0) > 0
        and _rate_cache_time
        and datetime.now() - _rate_cache_time < RATE_CACHE_TTL
    ):
        return _rate_cache

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch_vcb_exchange_rate)

    if data.get("sell", 0) > 0:
        _rate_cache = data
        _rate_cache_time = datetime.now()

    return data


# ═════════════════════════════════════════════════════════════
#  Price change detection (for auto-alert)
# ═════════════════════════════════════════════════════════════

_last_known_update_time: Optional[str] = None


async def check_price_change() -> Optional[dict]:
    """
    Check if Petrolimex has published new prices.
    Returns new price data if changed, None otherwise.
    """
    global _last_known_update_time

    data = await get_vn_fuel_prices(force_refresh=True)

    if data.get("error"):
        return None

    current_update_time = data.get("update_time", "")

    if _last_known_update_time is None:
        _last_known_update_time = current_update_time
        return None

    if current_update_time and current_update_time != _last_known_update_time:
        _last_known_update_time = current_update_time
        logger.info(f"New Petrolimex price detected! Update: {current_update_time}")
        return data

    return None
