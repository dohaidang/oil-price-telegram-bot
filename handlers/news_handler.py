from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from services.oil_price_service import get_current_prices
from services.vn_price_service import get_vn_fuel_prices, get_usd_vnd_rate
from utils.formatter import format_price, format_change
from utils.logger import setup_logger

logger = setup_logger("news_handler")


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /news command - market analysis summary."""
    # Support both message and callback query
    if update.callback_query:
        loading_msg = update.callback_query.message
        await update.callback_query.answer()
        await loading_msg.edit_text("⏳ Đang phân tích thị trường...")
    else:
        loading_msg = await update.message.reply_text("⏳ Đang phân tích thị trường...")

    try:
        import asyncio
        prices, vn_data, rate_data = await asyncio.gather(
            get_current_prices(),
            get_vn_fuel_prices(),
            get_usd_vnd_rate(),
        )

        if not prices:
            await loading_msg.edit_text("❌ Không thể lấy dữ liệu thị trường.")
            return

        lines = [
            "📰 <b>TỔNG QUAN THỊ TRƯỜNG DẦU MỎ</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        # Current prices summary
        lines.append("📊 <b>Giá thế giới:</b>")
        for oil_type, data in prices.items():
            if data.get("price", 0) > 0:
                name = data["name"]
                price = format_price(data["price"])
                change = format_change(data["change"], data["change_percent"])
                lines.append(f"  {name}: {price} {change}")
        lines.append("")

        # WTI - Brent spread
        wti_price = prices.get("WTI", {}).get("price", 0)
        brent_price = prices.get("BRENT", {}).get("price", 0)

        if wti_price > 0 and brent_price > 0:
            spread = brent_price - wti_price
            lines.append("📐 <b>Chênh lệch Brent - WTI:</b>")
            lines.append(f"  💰 {format_price(spread)}")
            if spread > 5:
                lines.append("  📝 Spread cao - áp lực lên giá dầu châu Á")
            elif spread < 2:
                lines.append("  📝 Spread thấp - giá dầu toàn cầu tương đồng")
            else:
                lines.append("  📝 Spread ở mức bình thường")
            lines.append("")

        # Trend analysis
        lines.append("📈 <b>Xu hướng:</b>")
        for oil_type in ["WTI", "BRENT"]:
            data = prices.get(oil_type, {})
            if data.get("price", 0) > 0:
                change_pct = data.get("change_percent", 0)
                name = data["name"]

                if change_pct > 2:
                    trend = "🟢 Tăng mạnh"
                elif change_pct > 0:
                    trend = "🟢 Tăng nhẹ"
                elif change_pct > -2:
                    trend = "🔴 Giảm nhẹ"
                else:
                    trend = "🔴 Giảm mạnh"

                lines.append(f"  {name}: {trend} ({change_pct:+.2f}%)")
        lines.append("")

        # ─── Vietnam impact analysis ────────────────────────
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("🇻🇳 <b>TÁC ĐỘNG ĐẾN GIÁ XĂNG VN:</b>")
        lines.append("")

        brent = prices.get("BRENT", {})
        brent_change_pct = brent.get("change_percent", 0)

        if vn_data and not vn_data.get("error") and vn_data.get("prices"):
            # Show current VN price for reference
            ron95 = None
            for key, val in vn_data["prices"].items():
                if "RON 95" in key and "III" in key:
                    ron95 = val
                    break
                if "RON 95" in key:
                    ron95 = val

            if ron95:
                lines.append(f"  ⛽ RON 95-III hiện tại: <b>{ron95['price_v1']:,.0f}đ/lít</b>")
                lines.append(f"  🕐 {vn_data.get('update_time', '')}")
                lines.append("")

        # Impact prediction
        if brent_change_pct > 3:
            lines.append("  🚨 <b>Giá dầu thế giới tăng mạnh!</b>")
            lines.append("  📌 Kỳ điều chỉnh tới giá xăng VN có thể <b>TĂNG</b>")
            lines.append("  💡 Nên đổ xăng sớm nếu gần kỳ điều chỉnh")
        elif brent_change_pct > 1:
            lines.append("  ⬆️ Giá dầu thế giới tăng nhẹ")
            lines.append("  📌 Giá xăng VN có thể tăng nhẹ kỳ tới")
        elif brent_change_pct > -1:
            lines.append("  ↔️ Giá dầu thế giới ổn định")
            lines.append("  📌 Giá xăng VN dự kiến ít biến động")
        elif brent_change_pct > -3:
            lines.append("  ⬇️ Giá dầu thế giới giảm nhẹ")
            lines.append("  📌 Giá xăng VN có thể giảm nhẹ kỳ tới")
        else:
            lines.append("  📉 <b>Giá dầu thế giới giảm mạnh!</b>")
            lines.append("  📌 Kỳ điều chỉnh tới giá xăng VN có thể <b>GIẢM</b>")
            lines.append("  💡 Có thể chờ kỳ điều chỉnh mới trước khi đổ xăng")

        # Exchange rate impact
        usd_vnd = rate_data.get("sell", 0) if rate_data else 0
        if usd_vnd > 0:
            lines.append("")
            lines.append(f"  💱 Tỷ giá USD/VND: <b>{usd_vnd:,.0f}đ</b> (VCB)")

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 <i>Phân tích mang tính tham khảo, không phải khuyến nghị đầu tư.</i>")
        lines.append("📌 <i>Xem giá VN chi tiết: /vn</i>")

        await loading_msg.edit_text("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in news_command: {e}")
        await loading_msg.edit_text("❌ Đã xảy ra lỗi khi phân tích thị trường.")
