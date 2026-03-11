from config import Config
from models.database import get_all_active_alerts, deactivate_alert, get_all_volatility_alert_users
from services.oil_price_service import get_current_prices
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


# Memory cache to prevent volatility spam. 
# Stores the last notified date string (e.g. "2023-10-25") for each oil type
VOLATILITY_CACHE = {}

async def check_volatility(bot):
    """
    Check if oil prices have fluctuated by >2% today.
    Sends notifications to subscribed users if triggered.
    """
    try:
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")

        users = await get_all_volatility_alert_users()
        if not users:
            return

        prices = await get_current_prices()
        
        for oil_type in ["WTI", "BRENT"]:
            data = prices.get(oil_type)
            if not data or data.get("price", 0) == 0:
                continue

            change_pct = data.get("change_percent", 0)
            
            # Check if fluctuation exceeds 2% threshold
            if abs(change_pct) >= 2.0:
                # Check cache to avoid spamming the same alert repeatedly today
                cache_key = f"{oil_type}_{today_str}"
                
                # If we haven't notified about this today, or if the change increased significantly again
                # For simplicity, we just notify once per day when it crosses 2%.
                # More advanced: notify again if crosses 3%, 4% etc.
                last_notified_pct = VOLATILITY_CACHE.get(cache_key, 0)
                
                # Notify if 1) not notified today yet, OR 2) change increased by another 1.5% since last notification
                if last_notified_pct == 0 or abs(change_pct) >= abs(last_notified_pct) + 1.5:
                    VOLATILITY_CACHE[cache_key] = change_pct
                    
                    name = Config.OIL_NAMES.get(oil_type, oil_type)
                    trend = "TĂNG MẠNH 🟢" if change_pct > 0 else "GIẢM MẠNH 🔴"
                    
                    message = (
                        f"⚡ <b>CẢNH BÁO BIẾN ĐỘNG {name}</b>\n\n"
                        f"Thị trường đang {trend}!\n"
                        f"💰 Giá hiện tại: <b>${data['price']:.2f}</b>\n"
                        f"📉 Biến động: <b>{change_pct:+.2f}%</b>\n\n"
                        f"<i>Tắt cảnh báo: /volatility off</i>"
                    )
                    
                    for user in users:
                        try:
                            await bot.send_message(
                                chat_id=user["chat_id"],
                                text=message,
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.error(f"Failed to send volatility alert to {user['chat_id']}: {e}")
                            
                    logger.info(f"Volatility alert sent for {oil_type}: {change_pct:+.2f}%")
                    
    except Exception as e:
        logger.error(f"Error checking volatility: {e}")
