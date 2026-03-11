from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from services.vn_price_service import get_vn_fuel_prices, get_usd_vnd_rate
from services.oil_price_service import get_current_prices
from utils.formatter import format_price
from utils.logger import setup_logger

logger = setup_logger("vn_handler")


async def vn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /vn command - Vietnam fuel prices."""
    args = context.args

    if args and args[0].lower() == "compare":
        await _handle_vn_compare(update)
        return

    loading_msg = await update.message.reply_text("⏳ Đang lấy giá xăng dầu Việt Nam...")

    try:
        data = await get_vn_fuel_prices()

        if data.get("error"):
            await loading_msg.edit_text(
                f"❌ {data['error']}\n\nVui lòng thử lại sau.",
                parse_mode="HTML",
            )
            return

        prices = data["prices"]
        update_time = data.get("update_time", "Không rõ")

        lines = [
            "🇻🇳 <b>GIÁ XĂNG DẦU VIỆT NAM</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "📍 <b>Vùng 1</b> (gần cảng/kho) | <b>Vùng 2</b> (xa cảng/kho)",
            "",
        ]

        for fuel_key, fuel_data in prices.items():
            name = fuel_data["name"]
            p1 = fuel_data["price_v1_formatted"]
            p2 = fuel_data["price_v2_formatted"]
            lines.append(f"{name}")
            lines.append(f"   💰 V1: <b>{p1}đ</b> | V2: <b>{p2}đ</b>")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"🕐 {update_time}")


        keyboard = [
            [
                InlineKeyboardButton("📊 So sánh thế giới", callback_data="cmd_vn_compare"),
                InlineKeyboardButton("🔄 Làm mới", callback_data="cmd_vn_refresh"),
            ],
        ]

        await loading_msg.edit_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        logger.error(f"Error in vn_command: {e}")
        await loading_msg.edit_text(
            "❌ Đã xảy ra lỗi. Vui lòng thử lại sau.",
            parse_mode="HTML",
        )


async def _handle_vn_compare(update: Update):
    """Handle /vn compare - Compare VN prices with world prices in VND."""
    loading_msg = await update.message.reply_text(
        "⏳ Đang so sánh giá xăng VN với thế giới..."
    )

    try:
        # Fetch all data concurrently
        import asyncio
        vn_data, world_prices, rate_data = await asyncio.gather(
            get_vn_fuel_prices(),
            get_current_prices(),
            get_usd_vnd_rate(),
        )

        if vn_data.get("error"):
            await loading_msg.edit_text(f"❌ Lỗi giá VN: {vn_data['error']}")
            return

        if not world_prices:
            await loading_msg.edit_text("❌ Không thể lấy giá dầu thế giới.")
            return

        usd_vnd = rate_data.get("sell", 0)
        if usd_vnd == 0:
            usd_vnd = 25500  # Fallback rate
            rate_note = "(tỷ giá ước tính)"
        else:
            rate_note = f"(Vietcombank bán: {usd_vnd:,.0f}đ)"

        lines = [
            "🌍 <b>SO SÁNH GIÁ XĂNG DẦU VN vs THẾ GIỚI</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"💱 Tỷ giá USD/VND: <b>{usd_vnd:,.0f}đ</b> {rate_note}",
            "",
        ]

        # WTI price in VND per liter (1 barrel = 158.987 liters)
        wti = world_prices.get("WTI", {})
        brent = world_prices.get("BRENT", {})

        if wti.get("price", 0) > 0:
            wti_vnd_per_liter = (wti["price"] / 158.987) * usd_vnd
            lines.append("🛢️ <b>WTI Crude Oil (quy đổi):</b>")
            lines.append(
                f"   💰 {format_price(wti['price'])}/thùng → "
                f"~<b>{wti_vnd_per_liter:,.0f}đ/lít</b> (giá thô)"
            )
            lines.append("")

        if brent.get("price", 0) > 0:
            brent_vnd_per_liter = (brent["price"] / 158.987) * usd_vnd
            lines.append("🛢️ <b>Brent Crude Oil (quy đổi):</b>")
            lines.append(
                f"   💰 {format_price(brent['price'])}/thùng → "
                f"~<b>{brent_vnd_per_liter:,.0f}đ/lít</b> (giá thô)"
            )
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("🇻🇳 <b>Giá bán lẻ VN (Vùng 1):</b>")
        lines.append("")

        vn_prices = vn_data["prices"]
        for fuel_key, fuel_data in vn_prices.items():
            name = fuel_data["name"]
            p1 = fuel_data["price_v1"]
            lines.append(f"   {name}: <b>{p1:,.0f}đ/lít</b>")

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Insight: compare RON95 with Brent converted
        ron95_data = None
        for key, val in vn_prices.items():
            if "RON 95" in key and "III" in key:
                ron95_data = val
                break
            if "RON 95" in key:
                ron95_data = val

        if ron95_data and brent.get("price", 0) > 0:
            brent_vnd = (brent["price"] / 158.987) * usd_vnd
            diff = ron95_data["price_v1"] - brent_vnd
            ratio = ron95_data["price_v1"] / brent_vnd if brent_vnd > 0 else 0

            lines.append("")
            lines.append("📝 <b>Nhận xét:</b>")
            lines.append(
                f"   Giá RON 95-III bán lẻ VN cao hơn giá dầu thô Brent "
                f"khoảng <b>{diff:,.0f}đ/lít</b> (~{ratio:.1f}x)"
            )
            lines.append(
                "   📌 Phần chênh lệch gồm: thuế, phí, chi phí vận chuyển, "
                "lọc dầu, lợi nhuận định mức"
            )

        lines.append("")
        lines.append("💡 <i>Giá dầu thô là giá nguyên liệu, chưa gồm thuế/phí.</i>")

        await loading_msg.edit_text("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in vn compare: {e}")
        await loading_msg.edit_text("❌ Đã xảy ra lỗi khi so sánh giá.")


async def vn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle VN inline button callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "cmd_vn_refresh":
        vn_data = await get_vn_fuel_prices(force_refresh=True)

        if vn_data.get("error"):
            await query.edit_message_text(
                f"❌ {vn_data['error']}",
                parse_mode="HTML",
            )
            return

        prices = vn_data["prices"]
        update_time = vn_data.get("update_time", "Không rõ")

        lines = [
            "🇻🇳 <b>GIÁ XĂNG DẦU VIỆT NAM</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "📍 <b>Vùng 1</b> (gần cảng/kho) | <b>Vùng 2</b> (xa cảng/kho)",
            "",
        ]

        for fuel_key, fuel_data in prices.items():
            name = fuel_data["name"]
            p1 = fuel_data["price_v1_formatted"]
            p2 = fuel_data["price_v2_formatted"]
            lines.append(f"{name}")
            lines.append(f"   💰 V1: <b>{p1}đ</b> | V2: <b>{p2}đ</b>")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"🕐 {update_time}")


        keyboard = [
            [
                InlineKeyboardButton("📊 So sánh thế giới", callback_data="cmd_vn_compare"),
                InlineKeyboardButton("🔄 Làm mới", callback_data="cmd_vn_refresh"),
            ],
        ]

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data == "cmd_vn_compare":
        await query.edit_message_text("⏳ Đang so sánh giá xăng VN với thế giới...")

        import asyncio
        vn_data, world_prices, rate_data = await asyncio.gather(
            get_vn_fuel_prices(),
            get_current_prices(),
            get_usd_vnd_rate(),
        )

        # Re-build compare message (same logic as _handle_vn_compare)
        if vn_data.get("error") or not world_prices:
            await query.edit_message_text("❌ Không thể lấy dữ liệu so sánh.")
            return

        usd_vnd = rate_data.get("sell", 0) or 25500

        lines = [
            "🌍 <b>SO SÁNH GIÁ XĂNG DẦU VN vs THẾ GIỚI</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"💱 Tỷ giá USD/VND: <b>{usd_vnd:,.0f}đ</b>",
            "",
        ]

        wti = world_prices.get("WTI", {})
        brent = world_prices.get("BRENT", {})

        if wti.get("price", 0) > 0:
            wti_vnd = (wti["price"] / 158.987) * usd_vnd
            lines.append(f"🛢️ WTI: {format_price(wti['price'])}/thùng → ~<b>{wti_vnd:,.0f}đ/lít</b>")

        if brent.get("price", 0) > 0:
            brent_vnd = (brent["price"] / 158.987) * usd_vnd
            lines.append(f"🛢️ Brent: {format_price(brent['price'])}/thùng → ~<b>{brent_vnd:,.0f}đ/lít</b>")

        lines.append("")
        lines.append("🇻🇳 <b>Giá bán lẻ VN:</b>")

        for fuel_key, fuel_data in vn_data["prices"].items():
            lines.append(f"   {fuel_data['name']}: <b>{fuel_data['price_v1']:,.0f}đ</b>")

        keyboard = [[InlineKeyboardButton("⬅️ Quay lại", callback_data="cmd_vn_refresh")]]

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
