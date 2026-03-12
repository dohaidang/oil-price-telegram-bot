import asyncio
import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from services.silver_world_service import get_silver_world_history
from models.database import get_silver_vn_history
from utils.logger import setup_logger

logger = setup_logger("silver_chart_service")

DARK_BG = "#1a1a2e"
CHART_BG = "#16213e"
GRID_COLOR = "#2a2a4a"
TEXT_COLOR = "#e0e0e0"
SILVER_COLOR = "#C0C0C0"    # classic silver
SILVER_COLOR_2 = "#A8A8A8"  # slightly darker for buy line

PERIOD_MAP = {
    "1d": "1d",
    "5d": "5d",
    "1m": "1mo",
    "3m": "3mo",
    "6m": "6mo",
    "1y": "1y",
}

PERIOD_LABELS = {
    "1d": "1 ngày",
    "5d": "5 ngày",
    "1m": "1 tháng",
    "3m": "3 tháng",
    "6m": "6 tháng",
    "1y": "1 năm",
}

DAYS_MAP = {
    "7": 7,
    "30": 30,
    "90": 90,
    "180": 180,
    "365": 365,
}


async def generate_silver_world_chart(period: str = "1m") -> io.BytesIO | None:
    """Generate XAGUSD price chart."""
    yf_period = PERIOD_MAP.get(period, "1mo")
    period_label = PERIOD_LABELS.get(period, period)

    data = await get_silver_world_history("XAGUSD", yf_period)
    if not data:
        return None

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=DARK_BG)
    ax.set_facecolor(CHART_BG)

    ax.plot(df["date"], df["close"], color=SILVER_COLOR, linewidth=2, label="XAGUSD", alpha=0.9)
    ax.fill_between(df["date"], df["close"], alpha=0.15, color=SILVER_COLOR)

    max_idx = df["close"].idxmax()
    min_idx = df["close"].idxmin()
    ax.annotate(
        f"${df['close'][max_idx]:.4f}",
        xy=(df["date"][max_idx], df["close"][max_idx]),
        fontsize=8, color=SILVER_COLOR, fontweight="bold", ha="center", va="bottom",
    )
    ax.annotate(
        f"${df['close'][min_idx]:.4f}",
        xy=(df["date"][min_idx], df["close"][min_idx]),
        fontsize=8, color=SILVER_COLOR, fontweight="bold", ha="center", va="top",
    )

    ax.set_title(
        f"🥈 Biểu Đồ Giá Bạc XAGUSD - {period_label}",
        fontsize=16, fontweight="bold", color=TEXT_COLOR, pad=15,
    )
    ax.set_xlabel("Ngày", fontsize=11, color=TEXT_COLOR)
    ax.set_ylabel("Giá (USD/oz)", fontsize=11, color=TEXT_COLOR)
    ax.grid(True, alpha=0.3, color=GRID_COLOR, linestyle="--")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=45)
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)

    ax.legend(loc="upper left", fontsize=10, facecolor=CHART_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)

    fig.text(
        0.99, 0.01,
        f"Silver Price Bot • {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        fontsize=8, color=TEXT_COLOR, alpha=0.5, ha="right", va="bottom",
    )

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    buf.seek(0)
    plt.close(fig)

    logger.info(f"Silver world chart generated - period: {period}")
    return buf


async def generate_silver_vn_chart(
    brand: str = "SJC",
    price_type: str = "sell",
    days: int = 30,
) -> io.BytesIO | None:
    """Generate silver VN price chart from DB history."""
    history = await get_silver_vn_history(brand, price_type, days)
    if not history or len(history) < 2:
        return None

    df = pd.DataFrame(history)
    df["fetched_at"] = pd.to_datetime(df["fetched_at"])

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=DARK_BG)
    ax.set_facecolor(CHART_BG)

    color = SILVER_COLOR if price_type == "sell" else SILVER_COLOR_2
    label = f"{brand} ({price_type.capitalize()})"

    ax.plot(df["fetched_at"], df["price_per_chi"], color=color, linewidth=2, label=label, alpha=0.9)
    ax.fill_between(df["fetched_at"], df["price_per_chi"], alpha=0.15, color=color)

    max_idx = df["price_per_chi"].idxmax()
    min_idx = df["price_per_chi"].idxmin()
    ax.annotate(
        f"{df['price_per_chi'][max_idx]:,.0f}đ",
        xy=(df["fetched_at"][max_idx], df["price_per_chi"][max_idx]),
        fontsize=8, color=color, fontweight="bold", ha="center", va="bottom",
    )
    ax.annotate(
        f"{df['price_per_chi'][min_idx]:,.0f}đ",
        xy=(df["fetched_at"][min_idx], df["price_per_chi"][min_idx]),
        fontsize=8, color=color, fontweight="bold", ha="center", va="top",
    )

    ax.set_title(
        f"🥈 Biểu Đồ Giá Bạc {brand} ({price_type.capitalize()}) - {days} ngày",
        fontsize=16, fontweight="bold", color=TEXT_COLOR, pad=15,
    )
    ax.set_xlabel("Ngày", fontsize=11, color=TEXT_COLOR)
    ax.set_ylabel("Giá (VND/chỉ)", fontsize=11, color=TEXT_COLOR)
    ax.grid(True, alpha=0.3, color=GRID_COLOR, linestyle="--")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=45)
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)

    ax.legend(loc="upper left", fontsize=10, facecolor=CHART_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)

    fig.text(
        0.99, 0.01,
        f"Silver Price Bot • {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        fontsize=8, color=TEXT_COLOR, alpha=0.5, ha="right", va="bottom",
    )

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    buf.seek(0)
    plt.close(fig)

    logger.info(f"Silver VN chart generated - {brand} {price_type} {days}d")
    return buf
