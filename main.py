import gevent.monkey
gevent.monkey.patch_all()

from pyrogram import Client
from web.app import create_app, start_web_server
from database.db import init_db
from config import API_ID, API_HASH, BOT_TOKEN, DATABASE_URL
from handlers import register_handlers
from threading import Thread
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Client(
    "quiz_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

Session = init_db(DATABASE_URL)
app = create_app(Session)

def run_flask():
    logger.info("Запускаю Flask...")
    start_web_server(app)

if __name__ == "__main__":
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask поток запущен")

    register_handlers(bot)
    logger.info("Запускаю бота...")
    try:
        bot.run()
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}", exc_info=True)
        # flask_process.terminate() <-- Эту строку можно убрать, т.к. поток-демон сам завершится
        raise