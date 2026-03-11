from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from models.database import add_alert, get_user_alerts, delete_alert, subscribe_vn_alert, unsubscribe_vn_alert, is_vn_alert_subscribed
from services.oil_price_service import get_valid_oil_types
from utils.formatter import format_price
from utils.logger import setup_logger

logger = setup_logger("alert_handler")


async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /alert command - manage price alerts."""
    args = context.args

    if not args:
        await update.message.reply_text(
            "🔔 <b>CẢNH BÁO GIÁ DẦU</b>\n\n"
            "📝 <b>Cách sử dụng:</b>\n\n"
            "➕ <b>Cảnh báo giá thế giới:</b>\n"
            "  <code>/alert wti above 80</code> - Báo khi WTI > $80\n"
            "  <code>/alert brent below 75</code> - Báo khi Brent < $75\n\n"
            "🇻🇳 <b>Cảnh báo giá VN:</b>\n"
            "  <code>/alert vn on</code> - Bật thông báo giá mới Petrolimex\n"
            "  <code>/alert vn off</code> - Tắt thông báo\n\n"
            "📋 <b>Xem danh sách:</b>\n"
            "  <code>/alert list</code>\n\n"
            "🗑️ <b>Xóa cảnh báo:</b>\n"
            "  <code>/alert delete 1</code>",
            parse_mode="HTML",
        )
        return

    sub_command = args[0].lower()

    # /alert vn on/off
    if sub_command == "vn":
        await _handle_alert_vn(update, args)
        return

    # /alert list
    if sub_command == "list":
        await _handle_alert_list(update)
        return

    # /alert delete <id>
    if sub_command == "delete":
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Vui lòng chỉ định ID: <code>/alert delete 1</code>",
                parse_mode="HTML",
            )
            return

        try:
            alert_id = int(args[1])
        except ValueError:
            await update.message.reply_text(
                "❌ ID không hợp lệ. Sử dụng <code>/alert list</code> để xem ID.",
                parse_mode="HTML",
            )
            return

        await _handle_alert_delete(update, alert_id)
        return

    # /alert <oil_type> <above|below> <price>
    if len(args) < 3:
        await update.message.reply_text(
            "❌ Thiếu tham số.\n\n"
            "Cú pháp: <code>/alert [loại dầu] [above|below] [giá]</code>\n"
            "Ví dụ: <code>/alert wti above 80</code>",
            parse_mode="HTML",
        )
        return

    oil_type = args[0].upper()
    condition = args[1].lower()
    try:
        target_price = float(args[2])
    except ValueError:
        await update.message.reply_text(
            "❌ Giá không hợp lệ. Vui lòng nhập số.",
            parse_mode="HTML",
        )
        return

    # Validate
    if oil_type not in get_valid_oil_types():
        valid_types = ", ".join([f"<code>{t.lower()}</code>" for t in get_valid_oil_types()])
        await update.message.reply_text(
            f"❌ Loại dầu không hợp lệ: <code>{oil_type}</code>\n"
            f"Các loại hợp lệ: {valid_types}",
            parse_mode="HTML",
        )
        return

    if condition not in ("above", "below"):
        await update.message.reply_text(
            "❌ Điều kiện không hợp lệ.\n"
            "Sử dụng <code>above</code> (trên) hoặc <code>below</code> (dưới).",
            parse_mode="HTML",
        )
        return

    if target_price <= 0:
        await update.message.reply_text(
            "❌ Giá phải lớn hơn 0.",
            parse_mode="HTML",
        )
        return

    # Add alert
    chat_id = update.effective_user.id
    alert_id = await add_alert(chat_id, oil_type, condition, target_price)

    name = Config.OIL_NAMES.get(oil_type, oil_type)
    cond_text = "vượt trên" if condition == "above" else "giảm dưới"

    await update.message.reply_text(
        f"✅ <b>Đã tạo cảnh báo #{alert_id}</b>\n\n"
        f"🛢️ {name}\n"
        f"📌 Điều kiện: {cond_text} {format_price(target_price)}\n\n"
        f"🔔 Bot sẽ thông báo khi giá đạt ngưỡng.\n"
        f"📋 Xem danh sách: <code>/alert list</code>",
        parse_mode="HTML",
    )

    logger.info(f"Alert #{alert_id} created: {oil_type} {condition} ${target_price} by user {chat_id}")


async def _handle_alert_list(update: Update):
    """Show user's active alerts."""
    chat_id = update.effective_user.id
    alerts = await get_user_alerts(chat_id)

    if not alerts:
        await update.message.reply_text(
            "📋 Bạn chưa có cảnh báo nào.\n\n"
            "➕ Tạo mới: <code>/alert wti above 80</code>",
            parse_mode="HTML",
        )
        return

    lines = ["🔔 <b>DANH SÁCH CẢNH BÁO</b>", "━━━━━━━━━━━━━━━━━━━━━━", ""]

    for alert in alerts:
        name = Config.OIL_NAMES.get(alert["oil_type"], alert["oil_type"])
        cond_text = "vượt trên" if alert["condition"] == "above" else "giảm dưới"
        lines.append(
            f"🔸 <b>#{alert['id']}</b> | {name}\n"
            f"   📌 Khi {cond_text} {format_price(alert['target_price'])}\n"
        )

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🗑️ Xóa: <code>/alert delete [ID]</code>")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def _handle_alert_delete(update: Update, alert_id: int):
    """Delete an alert."""
    chat_id = update.effective_user.id
    success = await delete_alert(alert_id, chat_id)

    if success:
        await update.message.reply_text(
            f"✅ Đã xóa cảnh báo <b>#{alert_id}</b>",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            f"❌ Không tìm thấy cảnh báo #{alert_id} hoặc không thuộc về bạn.",
            parse_mode="HTML",
        )


async def _handle_alert_vn(update: Update, args: list):
    """Handle /alert vn on/off - subscribe to Petrolimex price updates."""
    chat_id = update.effective_user.id

    if len(args) < 2:
        is_subscribed = await is_vn_alert_subscribed(chat_id)
        status = "✅ Đang bật" if is_subscribed else "❌ Đang tắt"
        await update.message.reply_text(
            f"🇻🇳 <b>Cảnh báo giá xăng VN</b>\n\n"
            f"📌 Trạng thái: {status}\n\n"
            f"Bật: <code>/alert vn on</code>\n"
            f"Tắt: <code>/alert vn off</code>\n\n"
            f"💡 Khi bật, bot sẽ tự động thông báo khi Petrolimex công bố giá mới.",
            parse_mode="HTML",
        )
        return

    action = args[1].lower()

    if action == "on":
        await subscribe_vn_alert(chat_id)
        await update.message.reply_text(
            "✅ <b>Đã bật cảnh báo giá xăng VN!</b>\n\n"
            "🔔 Bot sẽ thông báo khi Petrolimex công bố giá mới.\n"
            "📌 Kiểm tra mỗi 6 giờ.\n\n"
            "Tắt: <code>/alert vn off</code>",
            parse_mode="HTML",
        )
        logger.info(f"User {chat_id} subscribed to VN price alerts")

    elif action == "off":
        await unsubscribe_vn_alert(chat_id)
        await update.message.reply_text(
            "🔕 <b>Đã tắt cảnh báo giá xăng VN.</b>\n\n"
            "Bật lại: <code>/alert vn on</code>",
            parse_mode="HTML",
        )
        logger.info(f"User {chat_id} unsubscribed from VN price alerts")

    else:
        await update.message.reply_text(
            "❌ Sử dụng <code>/alert vn on</code> hoặc <code>/alert vn off</code>",
            parse_mode="HTML",
        )
