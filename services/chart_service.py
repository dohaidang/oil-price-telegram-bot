import asyncio
import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from config import Config
from services.oil_price_service import get_historical_data
from utils.logger import setup_logger

logger = setup_logger("chart_service")

# Chart style
DARK_BG = "#1a1a2e"
CHART_BG = "#16213e"
GRID_COLOR = "#2a2a4a"
TEXT_COLOR = "#e0e0e0"
COLORS = ["#00d4ff", "#ff6b6b", "#ffd93d", "#6bcb77", "#a855f7"]

# Period mapping for yfinance
PERIOD_MAP = {
    "1d": "1d",
    "5d": "5d",
    "7d": "5d",     # yfinance doesn't have 7d, use 5d
    "1m": "1mo",
    "30d": "1mo",
    "3m": "3mo",
    "90d": "3mo",
    "6m": "6mo",
    "1y": "1y",
    "2y": "2y",
    "5y": "5y",
}

PERIOD_LABELS = {
    "1d": "1 ngày",
    "5d": "5 ngày",
    "7d": "7 ngày",
    "1m": "1 tháng",
    "30d": "30 ngày",
    "3m": "3 tháng",
    "90d": "90 ngày",
    "6m": "6 tháng",
    "1y": "1 năm",
    "2y": "2 năm",
    "5y": "5 năm",
}


async def generate_chart(
    oil_types: list[str],
    period: str = "1m",
) -> io.BytesIO | None:
    """
    Generate a price chart for one or more oil types.
    Returns a BytesIO buffer containing the PNG image.
    """
    yf_period = PERIOD_MAP.get(period, "1mo")
    period_label = PERIOD_LABELS.get(period, period)

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=DARK_BG)
    ax.set_facecolor(CHART_BG)

    has_data = False

    for i, oil_type in enumerate(oil_types):
        oil_type = oil_type.upper()
        data = await get_historical_data(oil_type, yf_period)

        if not data:
            logger.warning(f"No historical data for {oil_type}")
            continue

        has_data = True
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        color = COLORS[i % len(COLORS)]
        name = Config.OIL_NAMES.get(oil_type, oil_type)

        # Plot line
        ax.plot(
            df["date"],
            df["close"],
            color=color,
            linewidth=2,
            label=name,
            alpha=0.9,
        )

        # Fill area under the line
        ax.fill_between(
            df["date"],
            df["close"],
            alpha=0.1,
            color=color,
        )

        # Annotate min/max
        max_idx = df["close"].idxmax()
        min_idx = df["close"].idxmin()

        ax.annotate(
            f"${df['close'][max_idx]:.2f}",
            xy=(df["date"][max_idx], df["close"][max_idx]),
            fontsize=8,
            color=color,
            fontweight="bold",
            ha="center",
            va="bottom",
        )
        ax.annotate(
            f"${df['close'][min_idx]:.2f}",
            xy=(df["date"][min_idx], df["close"][min_idx]),
            fontsize=8,
            color=color,
            fontweight="bold",
            ha="center",
            va="top",
        )

    if not has_data:
        plt.close(fig)
        return None

    # Styling
    ax.set_title(
        f"📈 Biểu Đồ Giá Dầu - {period_label}",
        fontsize=16,
        fontweight="bold",
        color=TEXT_COLOR,
        pad=15,
    )
    ax.set_xlabel("Ngày", fontsize=11, color=TEXT_COLOR)
    ax.set_ylabel("Giá (USD)", fontsize=11, color=TEXT_COLOR)

    # Grid
    ax.grid(True, alpha=0.3, color=GRID_COLOR, linestyle="--")

    # Date formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=45)

    # Tick colors
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)

    # Legend
    legend = ax.legend(
        loc="upper left",
        fontsize=10,
        facecolor=CHART_BG,
        edgecolor=GRID_COLOR,
        labelcolor=TEXT_COLOR,
    )

    # Watermark
    fig.text(
        0.99, 0.01,
        f"Oil Price Bot • {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        fontsize=8,
        color=TEXT_COLOR,
        alpha=0.5,
        ha="right",
        va="bottom",
    )

    plt.tight_layout()

    # Save to buffer
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    buf.seek(0)
    plt.close(fig)

    logger.info(f"Chart generated for {oil_types} - period: {period}")
    return buf


def get_valid_periods() -> list[str]:
    """Get list of valid period keys."""
    return list(PERIOD_MAP.keys())
