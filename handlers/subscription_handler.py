from telegram import Update
from telegram.ext import ContextTypes

from models.database import (
    subscribe_daily_alert, unsubscribe_daily_alert, is_daily_alert_subscribed,
    subscribe_volatility_alert, unsubscribe_volatility_alert, is_volatility_alert_subscribed
)
from utils.logger import setup_logger

logger = setup_logger("subscription_handler")

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /daily on/off - subscribe to daily 7AM price reports."""
    args = context.args
    chat_id = update.effective_user.id

    if not args:
        is_subscribed = await is_daily_alert_subscribed(chat_id)
        status = "✅ Đang bật" if is_subscribed else "❌ Đang tắt"
        await update.message.reply_text(
            f"🌅 <b>Bản tin sáng hàng ngày (7:00 AM)</b>\n\n"
            f"📌 Trạng thái hiện tại: {status}\n\n"
            f"Bật: <code>/daily on</code>\n"
            f"Tắt: <code>/daily off</code>\n\n"
            f"💡 Khi bật, bot sẽ gửi tóm tắt giá dầu Thế Giới & VN vào 7h sáng mỗi ngày.",
            parse_mode="HTML",
        )
        return

    action = args[0].lower()

    if action == "on":
        await subscribe_daily_alert(chat_id)
        await update.message.reply_text(
            "✅ <b>Đã bật bản tin sáng báo giá hàng ngày!</b>\n"
            "Bot sẽ gửi tóm tắt giá vào lúc 7:00 AM.",
            parse_mode="HTML",
        )
        logger.info(f"User {chat_id} subscribed to daily reports")
    elif action == "off":
        await unsubscribe_daily_alert(chat_id)
        await update.message.reply_text(
            "🔕 <b>Đã tắt bản tin sáng báo giá hàng ngày.</b>",
            parse_mode="HTML",
        )
        logger.info(f"User {chat_id} unsubscribed from daily reports")
    else:
        await update.message.reply_text(
            "❌ Vui lòng sử dụng <code>/daily on</code> hoặc <code>/daily off</code>",
            parse_mode="HTML",
        )

async def volatility_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /volatility on/off - subscribe to >2% price fluctuation alerts."""
    args = context.args
    chat_id = update.effective_user.id

    if not args:
        is_subscribed = await is_volatility_alert_subscribed(chat_id)
        status = "✅ Đang bật" if is_subscribed else "❌ Đang tắt"
        await update.message.reply_text(
            f"⚡ <b>Cảnh báo biến động giá mạnh (>2%)</b>\n\n"
            f"📌 Trạng thái hiện tại: {status}\n\n"
            f"Bật: <code>/volatility on</code>\n"
            f"Tắt: <code>/volatility off</code>\n\n"
            f"💡 Khi bật, bot sẽ báo khẩn cấp nếu giá dầu tăng/giảm mạnh bất thường.",
            parse_mode="HTML",
        )
        return

    action = args[0].lower()

    if action == "on":
        await subscribe_volatility_alert(chat_id)
        await update.message.reply_text(
            "✅ <b>Đã bật cảnh báo biến động giá!</b>\n"
            "Bot sẽ thông báo nếu giá dầu thế giới biến động mạnh (>2%).",
            parse_mode="HTML",
        )
        logger.info(f"User {chat_id} subscribed to volatility alerts")
    elif action == "off":
        await unsubscribe_volatility_alert(chat_id)
        await update.message.reply_text(
            "🔕 <b>Đã tắt cảnh báo biến động giá mạnh.</b>",
            parse_mode="HTML",
        )
        logger.info(f"User {chat_id} unsubscribed from volatility alerts")
    else:
        await update.message.reply_text(
            "❌ Vui lòng sử dụng <code>/volatility on</code> hoặc <code>/volatility off</code>",
            parse_mode="HTML",
        )
