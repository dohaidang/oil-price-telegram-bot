from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from models.database import upsert_user
from utils.logger import setup_logger

logger = setup_logger("help_handler")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    keyboard = [
        [
            InlineKeyboardButton("📊 Giá dầu", callback_data="cmd_price"),
            InlineKeyboardButton("📈 Biểu đồ", callback_data="cmd_chart_menu"),
        ],
        [
            InlineKeyboardButton("🔔 Cảnh báo", callback_data="cmd_alert_list"),
            InlineKeyboardButton("📰 Phân tích", callback_data="cmd_news"),
        ],
        [
            InlineKeyboardButton("❓ Trợ giúp", callback_data="cmd_help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"👋 Xin chào <b>{user.first_name}</b>!\n\n"
        "🛢️ Tôi là <b>Oil Price Bot</b> - trợ lý theo dõi giá dầu thô toàn cầu.\n\n"
        "📊 Tôi có thể giúp bạn:\n"
        "  • Xem giá dầu thời gian thực\n"
        "  • Tạo biểu đồ xu hướng giá\n"
        "  • Đặt cảnh báo khi giá đạt ngưỡng\n"
        "  • Phân tích tình hình thị trường\n\n"
        "👇 <b>Chọn chức năng bên dưới hoặc gõ lệnh:</b>"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "📖 <b>HƯỚNG DẪN SỬ DỤNG</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 <b>Xem giá dầu:</b>\n"
        "  /price - Tất cả loại dầu\n"
        "  /price wti - Giá WTI chi tiết\n"
        "  /price brent - Giá Brent chi tiết\n\n"
        "📈 <b>Biểu đồ:</b>\n"
        "  /chart wti 1m - WTI 1 tháng\n"
        "  /chart brent 3m - Brent 3 tháng\n"
        "  /chart all 1y - Tất cả 1 năm\n\n"
        "⏱️ <b>Khung thời gian:</b>\n"
        "  1d, 5d, 1m, 3m, 6m, 1y, 2y, 5y\n\n"
        "🔔 <b>Cảnh báo giá:</b>\n"
        "  /alert wti above 80 - Báo khi WTI > $80\n"
        "  /alert brent below 75 - Báo khi Brent < $75\n"
        "  /alert list - Xem danh sách cảnh báo\n"
        "  /alert delete 1 - Xóa cảnh báo #1\n\n"
        "📰 <b>Phân tích:</b>\n"
        "  /news - Tổng quan thị trường\n\n"
        "🛢️ <b>Các loại dầu:</b>\n"
        "  <code>wti</code> - WTI Crude Oil\n"
        "  <code>brent</code> - Brent Crude Oil\n"
        "  <code>natural_gas</code> - Khí tự nhiên\n"
        "  <code>heating_oil</code> - Dầu sưởi\n"
        "  <code>gasoline</code> - Xăng RBOB\n"
    )

    await update.message.reply_text(help_text, parse_mode="HTML")
