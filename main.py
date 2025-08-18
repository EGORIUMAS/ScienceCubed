from pyrogram import Client
from web.app import create_app, start_web_server
from database.db import init_db
from config import API_ID, API_HASH, BOT_TOKEN, DATABASE_URL
from handlers import register_handlers
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Client(
    "quiz_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Инициализация базы данных
Session = init_db(DATABASE_URL)

# Инициализация веб-приложения
app = create_app(Session)

def run_flask():
    """Запуск Flask приложения в отдельном потоке"""
    start_web_server(app)

if __name__ == "__main__":
    logger.info("Запускаю Flask...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask запущен")

    register_handlers(bot)

    logger.info("Запускаю бота...")
    bot.run()