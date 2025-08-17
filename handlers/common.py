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
/join_team - Присоединиться к существующей команде

❓ Викторина:
/status - Показать статус текущей игры
/leaderboard - Таблица лидеров

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
- Время на ответ: 30 секунд
- 1 балл за правильный ответ

2️⃣ Раунд 2: Множественный выбор
- Вопросы с вариантами A, B, C, D
- Время на ответ: 45 секунд
- 2 балла за правильный ответ

3️⃣ Раунд 3: Текстовые ответы
- Нужно написать правильный ответ текстом
- Время на ответ: 60 секунд
- 3 балла за правильный ответ

⚠️ Общие правила:
- Один ответ от команды на каждый вопрос
- После истечения времени ответы не принимаются
- Запрещено использование сторонних источников
"""
    await message.reply(rules_text)


#@RateLimiter(seconds=5)
async def status_command(client, message):
    session = Session()
    try:
        team = session.query(Team).filter_by(leader_id=message.from_user.id).first()
        if not team:
            await message.reply("Вы не зарегистрированы в игре. Используйте /start для регистрации.")
            return

        current_question = session.query(Question).order_by(Question.id.desc()).first()

        status_text = f"""
📊 Статус игры:

👥 Ваша команда: {team.name}
🎯 Текущий счет: {team.score or 0} очков
👥 Участников в команде: {len(json.loads(team.players))}

"""
        if current_question:
            status_text += f"❓ Текущий раунд: {current_question.round_number}\n"

        await message.reply(status_text)
    finally:
        session.close()


#@RateLimiter(seconds=5)
async def leaderboard_command(client, message):
    session = Session()
    try:
        teams = session.query(Team).order_by(Team.score.desc()).all()

        if not teams:
            await message.reply("Пока нет зарегистрированных команд.")
            return

        leaderboard_text = "🏆 Таблица лидеров:\n\n"
        for i, team in enumerate(teams, 1):
            leaderboard_text += f"{i}. {team.name}: {team.score or 0} очков\n"

        await message.reply(leaderboard_text)
    finally:
        session.close()