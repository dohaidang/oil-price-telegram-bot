import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import Config
from services.gold_world_service import get_gold_world_prices, convert_usd_oz_to_vnd_chi
from services.gold_vn_service import get_gold_vn_prices
from services.gold_chart_service import generate_gold_world_chart, generate_gold_vn_chart
from services.vn_price_service import get_usd_vnd_rate
from models.database import (
    upsert_user,
    add_gold_alert,
    get_user_gold_alerts,
    delete_gold_alert,
)
from utils.logger import setup_logger

logger = setup_logger("gold_handler")


# ═════════════════════════════════════════════════════════════
#  Gold Menu
# ═════════════════════════════════════════════════════════════

def _build_gold_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("💰 Giá hiện tại", callback_data="gold_price"),
            InlineKeyboardButton("📈 Biểu đồ", callback_data="gold_chart_menu"),
        ],
        [
            InlineKeyboardButton("🔔 Cảnh báo", callback_data="gold_alert_menu"),
            InlineKeyboardButton("🔄 So sánh TG–VN", callback_data="gold_compare"),
        ],
        [
            InlineKeyboardButton("◀️ Quay lại Market", callback_data="market_back"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def gold_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show gold main menu."""
    text = (
        "🥇 <b>GIÁ VÀNG</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Chọn chức năng:"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            text, parse_mode="HTML", reply_markup=_build_gold_menu()
        )
    else:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=_build_gold_menu()
        )


async def gold_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /gold command — shortcut to gold menu or subcommands."""
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    args = context.args if context.args else []

    if not args:
        await gold_menu(update, context)
        return

    sub = args[0].lower()

    if sub == "price":
        await _gold_price(update, context)
    elif sub == "alert" and len(args) >= 4:
        await _gold_alert_add_from_text(update, context, args[1:])
    elif sub == "alert":
        await _gold_alert_menu(update, context)
    else:
        await gold_menu(update, context)


# ═════════════════════════════════════════════════════════════
#  Gold Price
# ═════════════════════════════════════════════════════════════

async def _gold_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current gold prices (world + VN + conversion)."""
    if update.callback_query:
        await update.callback_query.answer()
        msg = update.callback_query.message
        await msg.edit_text("⏳ Đang tải giá vàng...")
    else:
        msg = await update.message.reply_text("⏳ Đang tải giá vàng...")

    try:
        world_prices, vn_prices, rate_data = await asyncio.gather(
            get_gold_world_prices(),
            get_gold_vn_prices(),
            get_usd_vnd_rate(),
        )

        lines = [
            "🥇 <b>GIÁ VÀNG</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        # World prices
        xau = world_prices.get("XAUUSD", {})
        if xau.get("price", 0) > 0:
            price = xau["price"]
            change = xau.get("change", 0)
            change_pct = xau.get("change_percent", 0)
            arrow = "🟢 ▲" if change >= 0 else "🔴 ▼"
            sign = "+" if change >= 0 else ""

            lines.append("🌍 <b>Thế giới (XAUUSD)</b>")
            lines.append(f"   💰 <b>${price:,.2f}</b>/oz")
            lines.append(f"   {arrow} {sign}{change:.2f} ({sign}{change_pct:.2f}%)")
            lines.append(f"   🔺 Cao: ${xau.get('high', 0):,.2f} | 🔻 Thấp: ${xau.get('low', 0):,.2f}")
            lines.append("")

            # Conversion
            usd_vnd = rate_data.get("sell", 0) if rate_data else 0
            if usd_vnd > 0:
                vnd_per_chi = convert_usd_oz_to_vnd_chi(price, usd_vnd)
                lines.append("💱 <b>Quy đổi tham khảo (VCB)</b>")
                lines.append(f"   🥇 ≈ <b>{vnd_per_chi:,.0f}đ/chỉ</b>")
                lines.append(f"   💵 Tỷ giá: {usd_vnd:,.0f}đ/USD")
                lines.append("")

        # VN prices
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("🇻🇳 <b>Việt Nam (VND/chỉ)</b>")
        lines.append("")

        for brand in Config.GOLD_VN_BRANDS:
            data = vn_prices.get(brand, {})
            buy = data.get("buy", 0)
            sell = data.get("sell", 0)

            if buy > 0 or sell > 0:
                lines.append(f"   🏷️ <b>{brand}</b>")
                lines.append(f"      Mua: <b>{buy:,.0f}đ</b> | Bán: <b>{sell:,.0f}đ</b>")
                lines.append("")
            else:
                lines.append(f"   🏷️ <b>{brand}</b>: ⚠️ Không lấy được dữ liệu")
                lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"🕐 Cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        lines.append("<i>💡 Giá quy đổi chỉ mang tính tham khảo</i>")

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="gold_price_refresh"),
                InlineKeyboardButton("📈 Biểu đồ", callback_data="gold_chart_menu"),
            ],
            [InlineKeyboardButton("◀️ Menu Vàng", callback_data="gold_back")],
        ])

        await msg.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in gold_price: {e}")
        await msg.edit_text("❌ Đã xảy ra lỗi khi tải giá vàng.")


# ═════════════════════════════════════════════════════════════
#  Gold Compare (World vs VN)
# ═════════════════════════════════════════════════════════════

async def _gold_compare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Compare world gold price (converted) vs VN gold price."""
    if update.callback_query:
        await update.callback_query.answer()
        msg = update.callback_query.message
        await msg.edit_text("⏳ Đang so sánh giá vàng TG–VN...")
    else:
        msg = await update.message.reply_text("⏳ Đang so sánh...")

    try:
        world_prices, vn_prices, rate_data = await asyncio.gather(
            get_gold_world_prices(),
            get_gold_vn_prices(),
            get_usd_vnd_rate(),
        )

        xau = world_prices.get("XAUUSD", {})
        usd_vnd = rate_data.get("sell", 0) if rate_data else 0

        lines = [
            "🔄 <b>SO SÁNH GIÁ VÀNG THẾ GIỚI – VIỆT NAM</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        if xau.get("price", 0) > 0 and usd_vnd > 0:
            world_vnd_chi = convert_usd_oz_to_vnd_chi(xau["price"], usd_vnd)
            lines.append(f"🌍 XAUUSD: <b>${xau['price']:,.2f}</b>/oz")
            lines.append(f"💱 Quy đổi VCB: <b>{world_vnd_chi:,.0f}đ/chỉ</b>")
            lines.append("")

            for brand in Config.GOLD_VN_BRANDS:
                data = vn_prices.get(brand, {})
                sell = data.get("sell", 0)
                if sell > 0 and world_vnd_chi > 0:
                    diff = sell - world_vnd_chi
                    diff_pct = (diff / world_vnd_chi) * 100
                    sign = "+" if diff >= 0 else ""
                    emoji = "📈" if diff >= 0 else "📉"

                    lines.append(f"🏷️ <b>{brand}</b> (bán): <b>{sell:,.0f}đ/chỉ</b>")
                    lines.append(f"   {emoji} Chênh lệch: {sign}{diff:,.0f}đ ({sign}{diff_pct:.1f}%)")
                    lines.append("")

            lines.append("━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("<i>💡 Chênh lệch bao gồm thuế, phí, cung-cầu nội địa</i>")
        else:
            lines.append("⚠️ Không đủ dữ liệu để so sánh.")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Menu Vàng", callback_data="gold_back")],
        ])

        await msg.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in gold_compare: {e}")
        await msg.edit_text("❌ Đã xảy ra lỗi khi so sánh.")


# ═════════════════════════════════════════════════════════════
#  Gold Chart
# ═════════════════════════════════════════════════════════════

def _build_chart_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🌍 XAUUSD", callback_data="gold_chart_world_menu")],
        [
            InlineKeyboardButton("🇻🇳 SJC", callback_data="gold_chart_vn_SJC_sell_30"),
            InlineKeyboardButton("🇻🇳 DOJI", callback_data="gold_chart_vn_DOJI_sell_30"),
            InlineKeyboardButton("🇻🇳 PNJ", callback_data="gold_chart_vn_PNJ_sell_30"),
        ],
        [InlineKeyboardButton("◀️ Menu Vàng", callback_data="gold_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def _build_world_chart_periods() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("1 ngày", callback_data="gold_chart_world_1d"),
            InlineKeyboardButton("5 ngày", callback_data="gold_chart_world_5d"),
            InlineKeyboardButton("1 tháng", callback_data="gold_chart_world_1m"),
        ],
        [
            InlineKeyboardButton("3 tháng", callback_data="gold_chart_world_3m"),
            InlineKeyboardButton("6 tháng", callback_data="gold_chart_world_6m"),
            InlineKeyboardButton("1 năm", callback_data="gold_chart_world_1y"),
        ],
        [InlineKeyboardButton("◀️ Quay lại", callback_data="gold_chart_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _gold_chart_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show chart selection menu."""
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "📈 <b>BIỂU ĐỒ GIÁ VÀNG</b>\n\nChọn loại biểu đồ:",
        parse_mode="HTML",
        reply_markup=_build_chart_menu(),
    )


async def _gold_chart_world_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show world chart period selection."""
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "🌍 <b>BIỂU ĐỒ XAUUSD</b>\n\nChọn khung thời gian:",
        parse_mode="HTML",
        reply_markup=_build_world_chart_periods(),
    )


async def _gold_chart_world(update: Update, context: ContextTypes.DEFAULT_TYPE, period: str):
    """Generate and send XAUUSD chart."""
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("⏳ Đang tạo biểu đồ XAUUSD...")

    try:
        buf = await generate_gold_world_chart(period)
        if buf:
            await query.message.reply_photo(
                photo=buf,
                caption=f"🥇 Biểu đồ XAUUSD - {period}",
            )
        else:
            await query.message.edit_text("❌ Không có dữ liệu biểu đồ.")
    except Exception as e:
        logger.error(f"Error generating gold world chart: {e}")
        await query.message.edit_text("❌ Lỗi khi tạo biểu đồ.")


async def _gold_chart_vn(update: Update, context: ContextTypes.DEFAULT_TYPE, brand: str, price_type: str, days: int):
    """Generate and send VN gold chart."""
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(f"⏳ Đang tạo biểu đồ {brand}...")

    try:
        buf = await generate_gold_vn_chart(brand, price_type, days)
        if buf:
            await query.message.reply_photo(
                photo=buf,
                caption=f"🥇 Biểu đồ {brand} ({price_type}) - {days} ngày",
            )
        else:
            await query.message.edit_text(
                f"❌ Chưa có đủ dữ liệu lịch sử cho {brand}.\n"
                "💡 Dữ liệu sẽ được thu thập tự động theo thời gian."
            )
    except Exception as e:
        logger.error(f"Error generating gold VN chart: {e}")
        await query.message.edit_text("❌ Lỗi khi tạo biểu đồ.")


# ═════════════════════════════════════════════════════════════
#  Gold Alert
# ═════════════════════════════════════════════════════════════

async def _gold_alert_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show gold alert management menu."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        msg = query.message
    else:
        msg = update.message

    user_id = update.effective_user.id
    alerts = await get_user_gold_alerts(user_id)

    lines = [
        "🔔 <b>CẢNH BÁO GIÁ VÀNG</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if alerts:
        for a in alerts:
            symbol = a["symbol"]
            cond = "trên" if a["condition"] == "above" else "dưới"

            if symbol == "XAUUSD":
                price_fmt = f"${a['target_price']:,.2f}"
            else:
                price_fmt = f"{a['target_price']:,.0f}đ/chỉ"

            lines.append(f"   #{a['id']} | {symbol} {cond} {price_fmt}")
        lines.append("")
    else:
        lines.append("   Chưa có cảnh báo nào.")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("<b>Cách đặt cảnh báo:</b>")
    lines.append("<code>/gold alert xau above 2400</code>")
    lines.append("<code>/gold alert sjc sell above 8200000</code>")
    lines.append("<code>/gold alert doji buy below 8000000</code>")
    lines.append("")
    lines.append("<b>Xóa cảnh báo:</b>")
    lines.append("<code>/gold alert delete [id]</code>")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Menu Vàng", callback_data="gold_back")],
    ])

    if update.callback_query:
        await msg.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=keyboard)
    else:
        await msg.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=keyboard)


VALID_ALERT_SYMBOLS = {
    "xau": "XAUUSD",
    "xauusd": "XAUUSD",
    "sjc": None,  # needs buy/sell
    "doji": None,
    "pnj": None,
}

VALID_VN_BRANDS = {"sjc", "doji", "pnj"}


async def _gold_alert_add_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE, args: list):
    """Parse and add a gold alert from text args.
    Formats:
      xau above 2400
      sjc sell above 8200000
      doji buy below 8000000
    """
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    msg = update.message

    try:
        raw_symbol = args[0].lower()

        if raw_symbol in ("delete", "del", "xóa", "xoa"):
            if len(args) >= 2:
                alert_id = int(args[1])
                deleted = await delete_gold_alert(alert_id, user.id)
                if deleted:
                    await msg.reply_text(f"✅ Đã xóa cảnh báo vàng #{alert_id}")
                else:
                    await msg.reply_text(f"❌ Không tìm thấy cảnh báo #{alert_id}")
            else:
                await msg.reply_text("❌ Cú pháp: /gold alert delete [id]")
            return

        if raw_symbol in ("list", "ds"):
            await _gold_alert_menu(update, context)
            return

        # Determine symbol
        if raw_symbol in ("xau", "xauusd"):
            symbol = "XAUUSD"
            condition = args[1].lower()
            target_price = float(args[2].replace(",", ""))
        elif raw_symbol in VALID_VN_BRANDS:
            price_type = args[1].lower()  # buy/sell
            if price_type not in ("buy", "sell"):
                await msg.reply_text("❌ Loại giá phải là `buy` hoặc `sell`")
                return
            condition = args[2].lower()
            target_price = float(args[3].replace(",", ""))
            symbol = f"{raw_symbol.upper()}_{price_type.upper()}"
        else:
            await msg.reply_text(
                "❌ Mã không hợp lệ. Hỗ trợ: <code>xau, sjc, doji, pnj</code>",
                parse_mode="HTML",
            )
            return

        if condition not in ("above", "below"):
            await msg.reply_text("❌ Điều kiện phải là `above` hoặc `below`")
            return

        alert_id = await add_gold_alert(user.id, symbol, condition, target_price)

        cond_vn = "vượt trên" if condition == "above" else "giảm dưới"
        if symbol == "XAUUSD":
            price_fmt = f"${target_price:,.2f}"
        else:
            price_fmt = f"{target_price:,.0f}đ/chỉ"

        await msg.reply_text(
            f"✅ Đã đặt cảnh báo vàng #{alert_id}\n"
            f"🥇 {symbol} {cond_vn} {price_fmt}",
            parse_mode="HTML",
        )

    except (IndexError, ValueError):
        await msg.reply_text(
            "❌ Cú pháp không đúng. Ví dụ:\n"
            "<code>/gold alert xau above 2400</code>\n"
            "<code>/gold alert sjc sell above 8200000</code>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Error adding gold alert: {e}")
        await msg.reply_text("❌ Đã xảy ra lỗi khi đặt cảnh báo.")


# ═════════════════════════════════════════════════════════════
#  Callback Router
# ═════════════════════════════════════════════════════════════

async def gold_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all gold_* callbacks."""
    query = update.callback_query
    data = query.data

    if data == "gold_price" or data == "gold_price_refresh":
        await _gold_price(update, context)

    elif data == "gold_compare":
        await _gold_compare(update, context)

    elif data == "gold_chart_menu":
        await _gold_chart_menu(update, context)

    elif data == "gold_chart_world_menu":
        await _gold_chart_world_menu(update, context)

    elif data.startswith("gold_chart_world_"):
        period = data.replace("gold_chart_world_", "")
        if period not in ("menu",):
            await _gold_chart_world(update, context, period)

    elif data.startswith("gold_chart_vn_"):
        parts = data.replace("gold_chart_vn_", "").split("_")
        if len(parts) >= 3:
            brand, price_type, days_str = parts[0], parts[1], parts[2]
            await _gold_chart_vn(update, context, brand, price_type, int(days_str))

    elif data == "gold_alert_menu":
        await _gold_alert_menu(update, context)

    elif data == "gold_back":
        await gold_menu(update, context)
