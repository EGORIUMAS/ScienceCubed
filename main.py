import gevent.monkey
gevent.monkey.patch_all()  # Monkey-патчинг в самом начале

from pyrogram import Client
from web.app import create_app, start_web_server
from database.db import init_db
from config import API_ID, API_HASH, BOT_TOKEN, DATABASE_URL
from handlers import register_handlers
from multiprocessing import Process
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота с in-memory сессией
bot = Client(
    "quiz_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True  # Избегаем SQLite для сессий
)

# Инициализация базы данных
Session = init_db(DATABASE_URL)

# Инициализация веб-приложения
app = create_app(Session)

def run_flask():
    """Запуск Flask в отдельном процессе"""
    logger.info("Запускаю Flask...")
    start_web_server(app)

if __name__ == "__main__":
    # Запуск Flask в отдельном процессе
    flask_process = Process(target=run_flask)
    flask_process.start()
    logger.info("Flask процесс запущен")

    # Регистрация обработчиков и запуск бота
    register_handlers(bot)
    logger.info("Запускаю бота...")
    try:
        bot.run()
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}", exc_info=True)
        flask_process.terminate()
        raise