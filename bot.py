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
from handlers.news_handler import news_command, build_news_message
from handlers.vn_handler import vn_command, vn_callback
from handlers.subscription_handler import daily_command, volatility_command
from services.alert_service import check_alerts, check_volatility
from services.vn_price_service import check_price_change, get_vn_fuel_prices, get_usd_vnd_rate
from services.oil_price_service import get_current_prices
from models.database import get_all_vn_alert_users, get_all_daily_alert_users
from utils.logger import setup_logger
from datetime import time, timezone

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
        BotCommand("alert", "Quản lý cảnh báo giá mục tiêu"),
        BotCommand("news", "Phân tích thị trường"),
        BotCommand("daily", "Đăng ký nhận bản tin 7h sáng"),
        BotCommand("volatility", "Đăng ký cảnh báo biến động giá mạnh"),
        BotCommand("help", "Trợ giúp"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered")


async def alert_job(context):
    """Scheduled job to check price alerts and volatility."""
    logger.debug("Running alert and volatility check...")
    triggered = await check_alerts(context.bot)
    if triggered:
        logger.info(f"Triggered {len(triggered)} active alert(s): {triggered}")
        
    # Also check volatility
    await check_volatility(context.bot)

async def daily_report_job(context):
    """Scheduled daily job to send market report at 7:00 AM."""
    logger.info("Running daily 7AM report job...")
    users = await get_all_daily_alert_users()
    if not users:
        return
        
    try:
        import asyncio
        prices, vn_data, rate_data = await asyncio.gather(
            get_current_prices(),
            get_vn_fuel_prices(),
            get_usd_vnd_rate(),
        )
        
        if prices:
            message = build_news_message(prices, vn_data, rate_data)
            
            # Add a good morning header
            report_msg = f"🌅 <b>BẢN TIN DẦU MỎ BUỔI SÁNG</b>\n\n{message}"
            
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user["chat_id"],
                        text=report_msg,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Failed to send daily report to user {user['chat_id']}: {e}")
            
            logger.info(f"Daily report sent to {len(users)} users.")
    except Exception as e:
        logger.error(f"Error in daily_report_job: {e}")

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
    application.add_handler(CommandHandler("daily", daily_command))
    application.add_handler(CommandHandler("volatility", volatility_command))

    # Register callback query handlers
    application.add_handler(CallbackQueryHandler(price_callback, pattern=r"^(cmd_price|cmd_price_refresh|price_)"))
    application.add_handler(CallbackQueryHandler(chart_callback, pattern=r"^chart_"))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: help_command(update, context),
        pattern=r"^cmd_help$",
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: start_command(update, context),
        pattern=r"^cmd_start$",
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: news_command(update, context), 
        pattern=r"^cmd_news$",
    ))
    application.add_handler(CallbackQueryHandler(vn_callback, pattern=r"^cmd_vn_"))
    
    # Helper to wrap subscription commands with args
    async def handle_sub_callback(update, context, cmd_func, action):
        # Inject args into context so the command handler sees them
        context.args = [action] if action else []
        await cmd_func(update, context)

    # Callback handlers for daily and volatility from main menu
    application.add_handler(CallbackQueryHandler(
        lambda update, context: handle_sub_callback(update, context, daily_command, None),
        pattern=r"^cmd_daily$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: handle_sub_callback(update, context, daily_command, "on"),
        pattern=r"^cmd_daily_on$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: handle_sub_callback(update, context, daily_command, "off"),
        pattern=r"^cmd_daily_off$"
    ))
    
    application.add_handler(CallbackQueryHandler(
        lambda update, context: handle_sub_callback(update, context, volatility_command, None),
        pattern=r"^cmd_volatility$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: handle_sub_callback(update, context, volatility_command, "on"),
        pattern=r"^cmd_volatility_on$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: handle_sub_callback(update, context, volatility_command, "off"),
        pattern=r"^cmd_volatility_off$"
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
        
        # Schedule daily 7 AM report (00:00 UTC = 07:00 VN Time)
        job_queue.run_daily(
            daily_report_job,
            time=time(hour=0, minute=0, tzinfo=timezone.utc),
            name="daily_7am_report"
        )
        logger.info("Daily 7AM report scheduled")

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

    # Keep alive server for Render
    from keep_alive import keep_alive
    keep_alive()

    # Start polling
    logger.info("Bot is running! Press Ctrl+C to stop.")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
