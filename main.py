from pyrogram import Client
from web.app import create_app
from database.db import init_db
from config import API_ID, API_HASH, BOT_TOKEN, DATABASE_URL
import asyncio
from handlers import register_handlers

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


async def main():
    # Регистрация обработчиков
    register_handlers(bot)

    # Запуск бота
    await bot.start()

    # Запуск веб-приложения
    from web.app import start_web_server
    await start_web_server(app)

    # Держим бота запущенным
    await bot.idle()


if __name__ == "__main__":
    asyncio.run(main())