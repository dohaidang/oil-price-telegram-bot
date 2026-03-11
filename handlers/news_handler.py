from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from services.oil_price_service import get_current_prices, get_historical_data
from utils.formatter import format_price, format_change
from utils.logger import setup_logger

logger = setup_logger("news_handler")


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /news command - market analysis summary."""
    loading_msg = await update.message.reply_text("⏳ Đang phân tích thị trường...")

    try:
        prices = await get_current_prices()

        if not prices:
            await loading_msg.edit_text("❌ Không thể lấy dữ liệu thị trường.")
            return

        lines = [
            "📰 <b>TỔNG QUAN THỊ TRƯỜNG DẦU MỎ</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        # Current prices summary
        lines.append("📊 <b>Giá hiện tại:</b>")
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

        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 <i>Dữ liệu mang tính tham khảo, không phải khuyến nghị đầu tư.</i>")

        await loading_msg.edit_text("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in news_command: {e}")
        await loading_msg.edit_text("❌ Đã xảy ra lỗi khi phân tích thị trường.")
