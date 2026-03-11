from datetime import datetime
from typing import Optional


def format_price(price: float) -> str:
    """Format price with dollar sign and 2 decimal places."""
    return f"${price:,.2f}"


def format_change(change: float, change_percent: float) -> str:
    """Format price change with arrow indicator."""
    if change >= 0:
        arrow = "🟢 ▲"
        sign = "+"
    else:
        arrow = "🔴 ▼"
        sign = ""

    return f"{arrow} {sign}{change:.2f} ({sign}{change_percent:.2f}%)"


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format timestamp for display."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%d/%m/%Y %H:%M UTC")


def build_price_message(prices: dict) -> str:
    """Build formatted price message for Telegram (HTML mode)."""
    lines = [
        "🛢️ <b>GIÁ DẦU THÔ THẾ GIỚI</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    for oil_type, data in prices.items():
        name = data.get("name", oil_type)
        price = data.get("price", 0)
        change = data.get("change", 0)
        change_pct = data.get("change_percent", 0)
        unit = data.get("unit", "USD")

        price_str = format_price(price)
        change_str = format_change(change, change_pct)

        lines.append(f"📊 <b>{name}</b>")
        lines.append(f"   💰 {price_str} | {change_str}")
        lines.append(f"   📏 <i>{unit}</i>")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🕐 Cập nhật: {format_timestamp()}")


    return "\n".join(lines)


def build_single_price_message(oil_type: str, data: dict) -> str:
    """Build formatted message for a single oil type."""
    name = data.get("name", oil_type)
    price = data.get("price", 0)
    change = data.get("change", 0)
    change_pct = data.get("change_percent", 0)
    unit = data.get("unit", "USD")
    high = data.get("high", 0)
    low = data.get("low", 0)
    open_price = data.get("open", 0)
    prev_close = data.get("prev_close", 0)

    price_str = format_price(price)
    change_str = format_change(change, change_pct)

    lines = [
        f"🛢️ <b>{name}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 Giá hiện tại: <b>{price_str}</b>",
        f"📈 Thay đổi: {change_str}",
        "",
        f"📊 Mở cửa: {format_price(open_price)}",
        f"🔺 Cao nhất: {format_price(high)}",
        f"🔻 Thấp nhất: {format_price(low)}",
        f"📋 Đóng trước: {format_price(prev_close)}",
        "",
        f"📏 Đơn vị: <i>{unit}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"🕐 Cập nhật: {format_timestamp()}",
    ]

    return "\n".join(lines)


def build_alert_message(oil_type: str, condition: str, target_price: float, 
                        current_price: float, name: str) -> str:
    """Build alert notification message."""
    if condition == "above":
        emoji = "🚀"
        text = "VƯỢT TRÊN"
    else:
        emoji = "📉"
        text = "GIẢM DƯỚI"

    return (
        f"{emoji} <b>CẢNH BÁO GIÁ DẦU!</b>\n\n"
        f"🛢️ <b>{name}</b> đã {text} ngưỡng!\n\n"
        f"💰 Giá hiện tại: <b>{format_price(current_price)}</b>\n"
        f"🎯 Ngưỡng đặt: {format_price(target_price)}\n\n"
        f"🕐 {format_timestamp()}"
    )
