from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from services.oil_price_service import get_current_prices, get_single_price, get_valid_oil_types
from utils.formatter import build_price_message, build_single_price_message
from utils.logger import setup_logger

logger = setup_logger("price_handler")


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /price command - show oil prices."""
    args = context.args

    # Send "loading" message
    loading_msg = await update.message.reply_text("⏳ Đang tải dữ liệu giá dầu...")

    try:
        if args:
            # Single oil type: /price wti
            oil_type = args[0].upper()

            if oil_type not in get_valid_oil_types():
                valid_types = ", ".join([f"<code>{t.lower()}</code>" for t in get_valid_oil_types()])
                await loading_msg.edit_text(
                    f"❌ Loại dầu không hợp lệ: <code>{oil_type}</code>\n\n"
                    f"Các loại hợp lệ: {valid_types}",
                    parse_mode="HTML",
                )
                return

            data = await get_single_price(oil_type)
            if data and data.get("price", 0) > 0:
                message = build_single_price_message(oil_type, data)
            else:
                message = f"❌ Không thể lấy giá cho {oil_type}. Vui lòng thử lại sau."

            # Add back button
            keyboard = [[InlineKeyboardButton("📊 Xem tất cả", callback_data="cmd_price")]]
            await loading_msg.edit_text(
                message,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        else:
            # All prices: /price
            prices = await get_current_prices()

            if prices:
                message = build_price_message(prices)
            else:
                message = "❌ Không thể lấy dữ liệu giá dầu. Vui lòng thử lại sau."

            # Add buttons for individual prices
            keyboard = []
            row = []
            for i, oil_type in enumerate(get_valid_oil_types()):
                from config import Config
                name = Config.OIL_NAMES.get(oil_type, oil_type).split(" ", 1)[-1]
                row.append(
                    InlineKeyboardButton(name, callback_data=f"price_{oil_type.lower()}")
                )
                if len(row) == 2 or i == len(get_valid_oil_types()) - 1:
                    keyboard.append(row)
                    row = []

            keyboard.append([InlineKeyboardButton("🔄 Làm mới", callback_data="cmd_price_refresh")])

            await loading_msg.edit_text(
                message,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    except Exception as e:
        logger.error(f"Error in price_command: {e}")
        await loading_msg.edit_text(
            "❌ Đã xảy ra lỗi. Vui lòng thử lại sau.",
            parse_mode="HTML",
        )


async def price_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle price inline button callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "cmd_price" or data == "cmd_price_refresh":
        # Show all prices
        force = data == "cmd_price_refresh"
        prices = await get_current_prices(force_refresh=force)

        if prices:
            message = build_price_message(prices)
        else:
            message = "❌ Không thể lấy dữ liệu giá dầu."

        keyboard = []
        row = []
        for i, oil_type in enumerate(get_valid_oil_types()):
            from config import Config
            name = Config.OIL_NAMES.get(oil_type, oil_type).split(" ", 1)[-1]
            row.append(
                InlineKeyboardButton(name, callback_data=f"price_{oil_type.lower()}")
            )
            if len(row) == 2 or i == len(get_valid_oil_types()) - 1:
                keyboard.append(row)
                row = []

        keyboard.append([InlineKeyboardButton("🔄 Làm mới", callback_data="cmd_price_refresh")])

        await query.edit_message_text(
            message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("price_"):
        # Single oil type
        oil_type = data.replace("price_", "").upper()
        price_data = await get_single_price(oil_type)

        if price_data and price_data.get("price", 0) > 0:
            message = build_single_price_message(oil_type, price_data)
        else:
            message = f"❌ Không thể lấy giá cho {oil_type}."

        keyboard = [[InlineKeyboardButton("⬅️ Quay lại", callback_data="cmd_price")]]
        await query.edit_message_text(
            message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
