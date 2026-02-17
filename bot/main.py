import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    Application
)
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
import uvicorn

# Load local env if exists
load_dotenv()

from . import database as db
from . import handlers

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    logger.error("FATAL: TELEGRAM_BOT_TOKEN is not set. Bot cannot start.")
if not OPENAI_API_KEY:
    logger.warning("WARNING: OPENAI_API_KEY is not set. AI features will be unavailable.")
if not WEBHOOK_URL:
    logger.warning("WARNING: WEBHOOK_URL is not set. Webhook mode might not work correctly.")

# Global app reference for webhook
telegram_app: Application = None

async def telegram_webhook(request):
    """Handle Telegram webhook updates."""
    if not telegram_app:
        return Response(status_code=500)
    
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
    
    return Response(status_code=200)

async def health_check(request):
    """Simple health check endpoint."""
    return JSONResponse({"status": "ok"})

async def startup():
    """App startup logic."""
    global telegram_app
    
    # Init DB
    await db.init_db()
    
    # Build Telegram App
    try:
        telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    except Exception as e:
        logger.error(f"Failed to build Telegram App: {e}")
        return
    
    # Add Handlers
    telegram_app.add_handler(CommandHandler(["start", "menu"], handlers.start_command))
    telegram_app.add_handler(CommandHandler("history", handlers.history_command))
    telegram_app.add_handler(CommandHandler("tipjar", handlers.tipjar_command))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    telegram_app.add_handler(CallbackQueryHandler(handlers.callback_handler))
    
    # Initialize and start (but don't wait for updates here in webhook mode)
    await telegram_app.initialize()
    await telegram_app.start()
    
    # Set Webhook if provided
    if WEBHOOK_URL:
        logger.info(f"Setting webhook to {WEBHOOK_URL}")
        await telegram_app.bot.set_webhook(url=WEBHOOK_URL)
    else:
        logger.warning("WEBHOOK_URL not set. Webhook endpoint will receive updates but token might fail if not registered manually.")

async def shutdown():
    """App shutdown logic."""
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()

async def run_polling():
    """Run in polling mode for local development."""
    await db.init_db()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler(["start", "menu"], handlers.start_command))
    app.add_handler(CommandHandler("history", handlers.history_command))
    app.add_handler(CommandHandler("tipjar", handlers.tipjar_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    app.add_handler(CallbackQueryHandler(handlers.callback_handler))
    
    logger.info("Starting bot in polling mode...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        await app.stop()
        await app.shutdown()

def main():
    """Entry point."""
    if "--polling" in sys.argv:
        asyncio.run(run_polling())
    else:
        # Starlette App for Webhook
        routes = [
            Route("/health", health_check, methods=["GET"]),
            Route("/webhook", telegram_webhook, methods=["POST"]),
        ]
        
        starlette_app = Starlette(
            routes=routes,
            on_startup=[startup],
            on_shutdown=[shutdown],
        )
        
        uvicorn.run(starlette_app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
