from pyrogram import Client, filters
from database.db import Team, Question
from config import DATABASE_URL
from database.db import init_db
Session = init_db(DATABASE_URL)
from utils.rate_limiter import RateLimiter
import json


#@RateLimiter(seconds=5)
async def help_command(client, message):
    help_text = """
🤖 Команды бота:

📝 Регистрация:
/start - Начать регистрацию команды

ℹ️ Прочее:
/help - Показать это сообщение
/rules - Правила игры
"""
    await message.reply(help_text)


#@RateLimiter(seconds=5)
async def rules_command(client, message):
    rules_text = """
📜 Правила викторины:

1️⃣ Раунд 1: Правда/Ложь
- Простые вопросы с вариантами "Правда" или "Ложь"
- Время на ответ: 20 секунд
- 1 балл за правильный ответ

2️⃣ Раунд 2: Множественный выбор
- Вопросы с вариантами A, B, C, D
- Время на ответ: 20 секунд
- 1 балл за правильный ответ

3️⃣ Раунд 3: Текстовые ответы
- Нужно написать правильный ответ текстом
- Время на ответ: 30 секунд
- 2 балла за правильный ответ

⚠️ Общие правила:
- Один ответ от команды на каждый вопрос
- После истечения времени ответы не принимаются
- Запрещено использование сторонних источников
"""
    await message.reply(rules_text)