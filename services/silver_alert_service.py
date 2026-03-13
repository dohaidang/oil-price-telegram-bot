from datetime import datetime

from models.database import get_all_active_silver_alerts, deactivate_silver_alert
from services.silver_world_service import get_silver_world_prices
from services.silver_vn_service import get_silver_vn_prices
from utils.logger import setup_logger

logger = setup_logger("silver_alert_service")

# Maps alert symbol to how we resolve the current price
# XAGUSD -> silver_world_service
# SJC_BUY, SJC_SELL, DOJI_BUY, ... -> silver_vn_service
VN_SYMBOL_MAP = {}
for _brand in ("SJC", "DOJI", "PNJ"):
    for _ptype in ("BUY", "SELL"):
        VN_SYMBOL_MAP[f"{_brand}_{_ptype}"] = (_brand, _ptype.lower())


def _format_silver_alert_message(symbol: str, condition: str, target: float, current: float) -> str:
    """Build alert notification message for silver."""
    if condition == "above":
        emoji = "🚀"
        text = "VƯỢT TRÊN"
    else:
        emoji = "📉"
        text = "GIẢM DƯỚI"

    is_vn = symbol in VN_SYMBOL_MAP

    if is_vn:
        price_fmt = f"{current:,.0f}đ/chỉ"
        target_fmt = f"{target:,.0f}đ/chỉ"
        label = symbol.replace("_", " ")
    else:
        price_fmt = f"${current:,.4f}/oz"
        target_fmt = f"${target:,.4f}/oz"
        label = symbol

    return (
        f"{emoji} <b>CẢNH BÁO GIÁ BẠC!</b>\n\n"
        f"🥈 <b>{label}</b> đã {text} ngưỡng!\n\n"
        f"💰 Giá hiện tại: <b>{price_fmt}</b>\n"
        f"🎯 Ngưỡng đặt: {target_fmt}\n\n"
        f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )


async def _resolve_price(symbol: str, world_prices: dict, vn_prices: dict) -> float:
    """Resolve current price for a given alert symbol."""
    if symbol == "XAGUSD":
        data = world_prices.get("XAGUSD", {})
        return data.get("price", 0)

    vn_info = VN_SYMBOL_MAP.get(symbol)
    if vn_info:
        brand, ptype = vn_info
        brand_data = vn_prices.get(brand, {})
        return brand_data.get(ptype, 0)

    return 0


async def check_silver_alerts(bot) -> list:
    """Check all active silver alerts against current prices.
    Returns list of triggered alert IDs.
    """
    triggered = []

    try:
        alerts = await get_all_active_silver_alerts()
        if not alerts:
            return triggered

        world_prices = await get_silver_world_prices()
        vn_prices = await get_silver_vn_prices()

        for alert in alerts:
            symbol = alert["symbol"]
            target_price = alert["target_price"]
            condition = alert["condition"]

            current_price = await _resolve_price(symbol, world_prices, vn_prices)
            if current_price <= 0:
                continue

            should_trigger = False
            if condition == "above" and current_price >= target_price:
                should_trigger = True
            elif condition == "below" and current_price <= target_price:
                should_trigger = True

            if should_trigger:
                try:
                    message = _format_silver_alert_message(
                        symbol, condition, target_price, current_price
                    )
                    await bot.send_message(
                        chat_id=alert["chat_id"],
                        text=message,
                        parse_mode="HTML",
                    )
                    await deactivate_silver_alert(alert["id"])
                    triggered.append(alert["id"])

                    logger.info(
                        f"Silver alert #{alert['id']} triggered: {symbol} {condition} "
                        f"{target_price} (current: {current_price})"
                    )
                except Exception as e:
                    logger.error(f"Error sending silver alert #{alert['id']}: {e}")

    except Exception as e:
        logger.error(f"Error checking silver alerts: {e}")

    return triggered
