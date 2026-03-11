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
from services.alert_service import check_alerts
from utils.logger import setup_logger

logger = setup_logger("bot")


async def post_init(application: Application):
    """Post-initialization: setup database and bot commands."""
    # Initialize database
    await init_db()

    # Set bot commands menu
    commands = [
        BotCommand("start", "Khởi động bot"),
        BotCommand("price", "Xem giá dầu hiện tại"),
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
