from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.logger import setup_logger

logger = setup_logger("market_handler")


def _build_market_menu() -> InlineKeyboardMarkup:
    """Build the main /market menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🛢 Dầu", callback_data="market_oil"),
            InlineKeyboardButton("🥇 Vàng", callback_data="market_gold"),
        ],
        [
            InlineKeyboardButton("🥈 Bạc (sắp có)", callback_data="market_soon"),
            InlineKeyboardButton("📈 Cổ phiếu (sắp có)", callback_data="market_soon"),
        ],
        [
            InlineKeyboardButton("₿ Crypto (sắp có)", callback_data="market_soon"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /market command — main entry point for all assets."""
    text = (
        "📊 <b>BẢNG GIÁ THỊ TRƯỜNG</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Chọn loại tài sản bạn muốn xem:"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            text, parse_mode="HTML", reply_markup=_build_market_menu()
        )
    else:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=_build_market_menu()
        )


async def market_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle market menu callbacks."""
    query = update.callback_query
    data = query.data

    if data == "market_oil":
        from handlers.price_handler import price_command
        await price_command(update, context)

    elif data == "market_gold":
        from handlers.gold_handler import gold_menu
        await gold_menu(update, context)

    elif data == "market_soon":
        await query.answer("🔜 Tính năng này sẽ sớm ra mắt!", show_alert=True)

    elif data == "market_back":
        await market_command(update, context)
