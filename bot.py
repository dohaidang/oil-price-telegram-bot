import asyncio
import logging

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from config import Config
from models.database import init_db
from handlers.help_handler import start_command, help_command
from handlers.price_handler import price_command, price_callback
from handlers.chart_handler import chart_command, chart_callback
from handlers.alert_handler import alert_command
from handlers.news_handler import news_command
from handlers.vn_handler import vn_command, vn_callback
from services.alert_service import check_alerts
from services.vn_price_service import check_price_change
from models.database import get_all_vn_alert_users
from utils.logger import setup_logger

logger = setup_logger("bot")


async def post_init(application: Application):
    """Post-initialization: setup database and bot commands."""
    # Initialize database
    await init_db()

    # Set bot commands menu
    commands = [
        BotCommand("start", "Khởi động bot"),
        BotCommand("price", "Xem giá dầu thế giới"),
        BotCommand("vn", "Giá xăng dầu Việt Nam"),
        BotCommand("chart", "Biểu đồ giá dầu"),
        BotCommand("alert", "Quản lý cảnh báo giá"),
        BotCommand("news", "Phân tích thị trường"),
        BotCommand("help", "Trợ giúp"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered")


async def alert_job(context):
    """Scheduled job to check price alerts."""
    logger.debug("Running alert check...")
    triggered = await check_alerts(context.bot)
    if triggered:
        logger.info(f"Triggered {len(triggered)} alert(s): {triggered}")


async def vn_price_alert_job(context):
    """Scheduled job to check for Petrolimex price changes."""
    logger.debug("Checking for VN price changes...")
    try:
        new_data = await check_price_change()
        if new_data and new_data.get("prices"):
            # Notify all users who have VN alerts enabled
            users = await get_all_vn_alert_users()
            if not users:
                return

            lines = [
                "🚨 <b>PETROLIMEX CẬP NHẬT GIÁ MỚI!</b>",
                "━━━━━━━━━━━━━━━━━━━━━━━━",
                "",
            ]
            for fuel_key, fuel_data in new_data["prices"].items():
                name = fuel_data["name"]
                p1 = fuel_data["price_v1_formatted"]
                p2 = fuel_data["price_v2_formatted"]
                lines.append(f"{name}")
                lines.append(f"   💰 V1: <b>{p1}đ</b> | V2: <b>{p2}đ</b>")
                lines.append("")

            lines.append(f"🕐 {new_data.get('update_time', '')}")
            lines.append("\n📌 Xem chi tiết: /vn")
            message = "\n".join(lines)

            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user["chat_id"],
                        text=message,
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {user['chat_id']}: {e}")

            logger.info(f"VN price change notified to {len(users)} users")
    except Exception as e:
        logger.error(f"Error in vn_price_alert_job: {e}")


async def error_handler(update: Update, context):
    """Handle errors."""
    logger.error(f"Exception while handling update: {context.error}", exc_info=context.error)


def main():
    """Main function to start the bot."""
    # Validate config
    Config.validate()

    logger.info("Starting Oil Price Bot...")
    logger.info(f"Update interval: {Config.UPDATE_INTERVAL} minutes")

    # Build application
    application = (
        Application.builder()
        .token(Config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("chart", chart_command))
    application.add_handler(CommandHandler("alert", alert_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("vn", vn_command))

    # Register callback query handlers
    application.add_handler(CallbackQueryHandler(price_callback, pattern=r"^(cmd_price|cmd_price_refresh|price_)"))
    application.add_handler(CallbackQueryHandler(chart_callback, pattern=r"^chart_"))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: help_command(update, context),
        pattern=r"^cmd_help$",
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: news_command(update, context), 
        pattern=r"^cmd_news$",
    ))
    application.add_handler(CallbackQueryHandler(vn_callback, pattern=r"^cmd_vn_"))

    # Register error handler
    application.add_error_handler(error_handler)

    # Schedule alert check job
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(
            alert_job,
            interval=Config.UPDATE_INTERVAL * 60,  # Convert minutes to seconds
            first=60,  # Start after 60 seconds
            name="alert_check",
        )
        logger.info(f"Alert check scheduled every {Config.UPDATE_INTERVAL} minutes")

        # VN price change check every 6 hours
        job_queue.run_repeating(
            vn_price_alert_job,
            interval=6 * 3600,  # 6 hours
            first=120,  # Start after 2 minutes
            name="vn_price_check",
        )
        logger.info("VN price change check scheduled every 6 hours")
    else:
        logger.warning("Job queue not available. Alerts will not be checked automatically.")

    # Start polling
    logger.info("Bot is running! Press Ctrl+C to stop.")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
