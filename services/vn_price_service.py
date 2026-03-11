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
VNEXPRESS_TOPIC_URL = "https://vnexpress.net/chu-de/gia-xang-dau-3580"
WEBTYGIA_URL = "https://webtygia.com/gia-xang-dau.html"
VCB_EXCHANGE_RATE_URL = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx?b=68"

# ─── Product display config ─────────────────────────────────
VN_FUEL_NAMES = {
    # VNExpress names
    "Xăng RON 95-III": "⛽ Xăng RON 95-III",
    "Xăng E5 RON 92": "⛽ Xăng E5 RON 92",
    "Dầu diesel": "🏭 Dầu Diesel",
    "Dầu hoả": "🪔 Dầu hỏa",
    "Dầu hỏa": "🪔 Dầu hỏa",
    # webtygia.com names
    "RON 95-III": "⛽ Xăng RON 95-III",
    "RON 95-V": "⛽ Xăng RON 95-V",
    "E5 RON 92-II": "⛽ Xăng E5 RON 92",
    "DO 0,001S-V": "🏭 Diesel 0,001S-V",
    "DO 0,05S-II": "🏭 Diesel 0,05S-II",
    "hỏa 2-K": "🪔 Dầu hỏa",
    "Dầu hỏa 2-K": "🪔 Dầu hỏa",
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
#  Vietnam Fuel Price Scraper
# ═════════════════════════════════════════════════════════════

def _scrape_vn_prices() -> dict:
    """
    Scrape fuel prices using dual-source strategy:
    1. VNExpress (primary) - latest fuel price article with table
    2. webtygia.com (fallback) - Petrolimex prices with Vùng 1/2
    """
    # Try VNExpress first
    result = _scrape_vnexpress()
    if result.get("prices"):
        return result

    # Fallback to webtygia.com
    logger.info("VNExpress failed, trying webtygia.com fallback...")
    return _scrape_webtygia()


def _scrape_vnexpress() -> dict:
    """Scrape fuel prices from latest VNExpress article."""
    result = {
        "prices": {},
        "update_time": "",
        "source": "VNExpress / Petrolimex",
        "error": None,
    }

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            # Step 1: Find latest fuel price article from topic page
            resp = client.get(VNEXPRESS_TOPIC_URL, headers=HEADERS)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # Find article links containing fuel price keywords
        article_url = None
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = a.get_text(strip=True).lower()
            if ("gia-xang" in href or "giá xăng" in title) and (
                "tăng" in title or "giảm" in title or "không đổi" in title
                or "điều chỉnh" in title
            ):
                if href.startswith("http"):
                    article_url = href
                elif href.startswith("/"):
                    article_url = f"https://vnexpress.net{href}"
                break

        if not article_url:
            result["error"] = "Không tìm thấy bài viết giá xăng trên VNExpress"
            return result

        logger.info(f"Found VNExpress article: {article_url}")

        # Step 2: Scrape the article for price table
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp2 = client.get(article_url, headers=HEADERS)
            resp2.raise_for_status()

        article_soup = BeautifulSoup(resp2.text, "lxml")

        # Find price table (typically: Mặt hàng | Giá mới | Thay đổi)
        tables = article_soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    name = cells[0].get_text(strip=True)
                    price_text = cells[1].get_text(strip=True)

                    # Skip header
                    if "mặt hàng" in name.lower() or "sản phẩm" in name.lower():
                        continue

                    price_int = _parse_vn_price(price_text)
                    if price_int > 0:
                        # Get price change if available
                        change_text = ""
                        if len(cells) >= 3:
                            change_text = cells[2].get_text(strip=True)

                        display_name = _get_display_name(name)

                        result["prices"][name] = {
                            "name": display_name,
                            "price_v1": price_int,
                            "price_v2": 0,  # VNExpress doesn't show Vùng 2
                            "price_v1_formatted": f"{price_int:,.0f}",
                            "price_v2_formatted": "—",
                            "change": change_text,
                            "unit": "đồng/lít",
                        }

        # Extract update time from article title or meta
        title_el = article_soup.find("h1") or article_soup.find("title")
        date_el = article_soup.find("span", class_="date")
        if date_el:
            result["update_time"] = date_el.get_text(strip=True)
        elif title_el:
            title_text = title_el.get_text(strip=True)
            date_match = re.search(r'\d{1,2}/\d{1,2}', title_text)
            if date_match:
                result["update_time"] = f"Giá xăng ngày {date_match.group()}"

        if not result["update_time"]:
            result["update_time"] = f"Cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M')}"

        if result["prices"]:
            logger.info(f"Scraped {len(result['prices'])} fuel types from VNExpress")
        else:
            result["error"] = "Không tìm thấy bảng giá trong bài viết VNExpress"

    except Exception as e:
        result["error"] = f"Lỗi scrape VNExpress: {e}"
        logger.error(f"Error scraping VNExpress: {e}")

    return result


def _scrape_webtygia() -> dict:
    """Fallback: Scrape fuel prices from webtygia.com."""
    result = {
        "prices": {},
        "update_time": "",
        "source": "Petrolimex (via webtygia.com)",
        "error": None,
    }

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(WEBTYGIA_URL, headers=HEADERS)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        tables = soup.find_all("table")

        if tables:
            fuel_table = tables[0]
            rows = fuel_table.find_all("tr")
            data_count = 0

            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 3:
                    name = cells[0].get_text(strip=True)
                    price_v1_text = cells[1].get_text(strip=True)
                    price_v2_text = cells[2].get_text(strip=True)

                    if "sản phẩm" in name.lower() or "vùng" in name.lower():
                        continue

                    price_v1_int = _parse_vn_price(price_v1_text)
                    price_v2_int = _parse_vn_price(price_v2_text)

                    if price_v1_int > 0:
                        display_name = _get_display_name(name)

                        result["prices"][name] = {
                            "name": display_name,
                            "price_v1": price_v1_int,
                            "price_v2": price_v2_int,
                            "price_v1_formatted": f"{price_v1_int:,.0f}",
                            "price_v2_formatted": f"{price_v2_int:,.0f}",
                            "unit": "đồng/lít",
                        }
                        data_count += 1

                    if data_count >= 5:
                        break

        result["update_time"] = f"Cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M')}"

        if not result["prices"]:
            result["error"] = "Không tìm thấy bảng giá xăng dầu"

        logger.info(f"Scraped {len(result['prices'])} fuel types from webtygia.com")

    except Exception as e:
        result["error"] = f"Lỗi scrape webtygia: {e}"
        logger.error(f"Error scraping webtygia: {e}")

    return result


def _get_display_name(name: str) -> str:
    """Get emoji display name for a fuel product."""
    display_name = VN_FUEL_NAMES.get(name)
    if not display_name:
        for key, val in VN_FUEL_NAMES.items():
            if key in name or name in key:
                display_name = val
                break
    return display_name or f"🛢️ {name}"


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
    data = await loop.run_in_executor(None, _scrape_vn_prices)

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
