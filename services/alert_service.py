from config import Config
from models.database import get_all_active_alerts, deactivate_alert
from services.oil_price_service import get_current_prices
from utils.formatter import build_alert_message
from utils.logger import setup_logger

logger = setup_logger("alert_service")


async def check_alerts(bot) -> list:
    """
    Check all active alerts against current prices.
    Sends notifications and deactivates triggered alerts.
    Returns list of triggered alert IDs.
    """
    triggered = []

    try:
        alerts = await get_all_active_alerts()
        if not alerts:
            return triggered

        prices = await get_current_prices()

        for alert in alerts:
            oil_type = alert["oil_type"]
            price_data = prices.get(oil_type)

            if not price_data or price_data.get("price", 0) == 0:
                continue

            current_price = price_data["price"]
            target_price = alert["target_price"]
            condition = alert["condition"]

            should_trigger = False
            if condition == "above" and current_price >= target_price:
                should_trigger = True
            elif condition == "below" and current_price <= target_price:
                should_trigger = True

            if should_trigger:
                try:
                    name = Config.OIL_NAMES.get(oil_type, oil_type)
                    message = build_alert_message(
                        oil_type, condition, target_price, current_price, name
                    )

                    await bot.send_message(
                        chat_id=alert["chat_id"],
                        text=message,
                        parse_mode="HTML",
                    )

                    await deactivate_alert(alert["id"])
                    triggered.append(alert["id"])

                    logger.info(
                        f"Alert #{alert['id']} triggered: {oil_type} {condition} "
                        f"${target_price} (current: ${current_price})"
                    )

                except Exception as e:
                    logger.error(f"Error sending alert #{alert['id']}: {e}")

    except Exception as e:
        logger.error(f"Error checking alerts: {e}")

    return triggered
