from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import Config
from services.chart_service import generate_chart, get_valid_periods
from services.oil_price_service import get_valid_oil_types
from utils.logger import setup_logger

logger = setup_logger("chart_handler")


async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /chart command - generate price charts."""
    args = context.args

    if not args:
        # Show chart menu
        keyboard = []
        for oil_type in get_valid_oil_types():
            name = Config.OIL_NAMES.get(oil_type, oil_type)
            keyboard.append([
                InlineKeyboardButton(
                    f"{name} - 1 tháng",
                    callback_data=f"chart_{oil_type.lower()}_1m",
                )
            ])
        keyboard.append([
            InlineKeyboardButton(
                "📊 So sánh tất cả - 1 tháng",
                callback_data="chart_all_1m",
            )
        ])

        msg_target = update.effective_message
        await msg_target.reply_text(
            "📈 <b>BIỂU ĐỒ GIÁ DẦU</b>\n\n"
            "Chọn loại dầu bên dưới hoặc gõ lệnh:\n"
            "<code>/chart wti 1m</code>\n"
            "<code>/chart brent 3m</code>\n"
            "<code>/chart all 1y</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Parse arguments
    oil_type_arg = args[0].lower()
    period = args[1].lower() if len(args) > 1 else "1m"

    if period not in get_valid_periods():
        valid_periods = ", ".join([f"<code>{p}</code>" for p in get_valid_periods()])
        await update.message.reply_text(
            f"❌ Khung thời gian không hợp lệ: <code>{period}</code>\n\n"
            f"Các khung hợp lệ: {valid_periods}",
            parse_mode="HTML",
        )
        return

    # Determine oil types to chart
    if oil_type_arg == "all":
        oil_types = get_valid_oil_types()
    else:
        oil_type = oil_type_arg.upper()
        if oil_type not in get_valid_oil_types():
            valid_types = ", ".join([f"<code>{t.lower()}</code>" for t in get_valid_oil_types()])
            await update.message.reply_text(
                f"❌ Loại dầu không hợp lệ: <code>{oil_type_arg}</code>\n\n"
                f"Các loại hợp lệ: {valid_types}, <code>all</code>",
                parse_mode="HTML",
            )
            return
        oil_types = [oil_type]

    # Send loading message
    loading_msg = await update.message.reply_text("⏳ Đang tạo biểu đồ...")

    try:
        chart_buf = await generate_chart(oil_types, period)

        if chart_buf:
            # Build period selection keyboard
            keyboard = _build_period_keyboard(oil_type_arg)

            await loading_msg.delete()
            await update.message.reply_photo(
                photo=chart_buf,
                caption=f"📈 Biểu đồ giá dầu - {period.upper()}",
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
            )
        else:
            await loading_msg.edit_text(
                "❌ Không có dữ liệu để tạo biểu đồ. Vui lòng thử lại.",
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Error in chart_command: {e}")
        await loading_msg.edit_text(
            "❌ Đã xảy ra lỗi khi tạo biểu đồ.",
            parse_mode="HTML",
        )


async def chart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chart inline button callbacks."""
    query = update.callback_query
    await query.answer("⏳ Đang tạo biểu đồ...")

    data = query.data  # chart_{oil_type}_{period}
    parts = data.replace("chart_", "").rsplit("_", 1)

    if len(parts) != 2:
        return

    oil_type_arg = parts[0]
    period = parts[1]

    if oil_type_arg == "all":
        oil_types = get_valid_oil_types()
    else:
        oil_types = [oil_type_arg.upper()]

    try:
        chart_buf = await generate_chart(oil_types, period)

        if chart_buf:
            keyboard = _build_period_keyboard(oil_type_arg)

            # Send new photo (can't edit to photo)
            await query.message.reply_photo(
                photo=chart_buf,
                caption=f"📈 Biểu đồ giá dầu - {period.upper()}",
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
            )
        else:
            await query.message.reply_text(
                "❌ Không có dữ liệu để tạo biểu đồ.",
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Error in chart_callback: {e}")
        await query.message.reply_text(
            "❌ Đã xảy ra lỗi khi tạo biểu đồ.",
            parse_mode="HTML",
        )


def _build_period_keyboard(oil_type_arg: str) -> list:
    """Build period selection keyboard."""
    periods = [("1D", "1d"), ("5D", "5d"), ("1M", "1m"), ("3M", "3m"), ("6M", "6m"), ("1Y", "1y")]

    keyboard = [[
        InlineKeyboardButton(
            label,
            callback_data=f"chart_{oil_type_arg}_{period}",
        )
        for label, period in periods
    ]]

    return keyboard
