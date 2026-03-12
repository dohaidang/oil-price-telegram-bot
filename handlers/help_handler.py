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
            InlineKeyboardButton("🇻🇳 Giá VN", callback_data="cmd_vn_refresh"),
        ],
        [
            InlineKeyboardButton("📈 Biểu đồ", callback_data="cmd_chart_menu"),
            InlineKeyboardButton("📰 Phân tích", callback_data="cmd_news"),
        ],
        [
            InlineKeyboardButton("🌅 Bản tin Sáng", callback_data="cmd_daily"),
            InlineKeyboardButton("⚡ Biến động", callback_data="cmd_volatility"),
        ],
        [
            InlineKeyboardButton("🔔 Cảnh báo", callback_data="cmd_alert_list"),
            InlineKeyboardButton("❓ Trợ giúp", callback_data="cmd_help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"👋 Xin chào <b>{user.first_name}</b>!\n\n"
        "🛢️ Tôi là <b>Oil Price Bot</b> - trợ lý theo dõi giá dầu thô toàn cầu.\n\n"
        "📊 Tôi có thể giúp bạn:\n"
        "  • Xem giá dầu thế giới thời gian thực\n"
        "  • 🇻🇳 Giá xăng dầu Việt Nam (Petrolimex)\n"
        "  • Tạo biểu đồ xu hướng giá\n"
        "  • Đặt cảnh báo khi giá đạt ngưỡng\n"
        "  • Phân tích tác động giá thế giới → giá VN\n\n"
        "👇 <b>Chọn chức năng bên dưới hoặc gõ lệnh:</b>"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            welcome_text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    else:
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
        "📊 <b>Giá dầu thế giới:</b>\n"
        "  /price - Tất cả loại dầu\n"
        "  /price wti - Giá WTI chi tiết\n"
        "  /price brent - Giá Brent chi tiết\n\n"
        "🇻🇳 <b>Giá xăng dầu Việt Nam:</b>\n"
        "  /vn - Giá Petrolimex hiện tại\n"
        "  /vn compare - So sánh VN vs thế giới\n\n"
        "📈 <b>Biểu đồ:</b>\n"
        "  /chart wti 1m - WTI 1 tháng\n"
        "  /chart brent 3m - Brent 3 tháng\n"
        "  /chart all 1y - Tất cả 1 năm\n\n"
        "⏱️ <b>Khung thời gian:</b>\n"
        "  1d, 5d, 1m, 3m, 6m, 1y, 2y, 5y\n\n"
        "🔔 <b>Cảnh báo giá:</b>\n"
        "  /alert wti above 80 - Báo khi WTI &gt; $80\n"
        "  /alert vn on - Bật thông báo giá VN mới\n"
        "  /alert list - Xem danh sách cảnh báo\n"
        "  /alert delete 1 - Xóa cảnh báo #1\n\n"
        "📰 <b>Bản tin & Phân tích:</b>\n"
        "  /news - Tổng quan thị trường + tác động đến VN\n"
        "  /daily - Đăng ký bản tin sáng hàng ngày\n"
        "  /volatility - Báo động khi giá biến động mạnh\n\n"
        "🛢️ <b>Các loại dầu:</b>\n"
        "  <code>wti</code> - WTI Crude Oil\n"
        "  <code>brent</code> - Brent Crude Oil\n"
        "  <code>natural_gas</code> - Khí tự nhiên\n"
        "  <code>heating_oil</code> - Dầu sưởi\n"
        "  <code>gasoline</code> - Xăng RBOB\n"
    )

    keyboard = [
        [
            InlineKeyboardButton("📊 Giá dầu", callback_data="cmd_price"),
            InlineKeyboardButton("🇻🇳 Giá VN", callback_data="cmd_vn_refresh"),
        ],
        [
            InlineKeyboardButton("📈 Biểu đồ", callback_data="cmd_chart_menu"),
            InlineKeyboardButton("📰 Phân tích", callback_data="cmd_news"),
        ],
        [
            InlineKeyboardButton("🌅 Bản tin Sáng", callback_data="cmd_daily"),
            InlineKeyboardButton("⚡ Biến động", callback_data="cmd_volatility"),
        ],
        [
            InlineKeyboardButton("🔔 Cảnh báo", callback_data="cmd_alert_list"),
            InlineKeyboardButton("⬅️ Bảng điều khiển", callback_data="cmd_start"),
        ],
    ]

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            help_text, 
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            help_text, 
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
