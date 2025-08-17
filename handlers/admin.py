from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from database.db import Team, Question
from config import DATABASE_URL
from database.db import init_db
Session = init_db(DATABASE_URL)
from config import TG_ADMIN_USERNAME
import json


def is_admin(func):
    async def wrapper(client, message):
        if message.from_user.username == TG_ADMIN_USERNAME:
            await func(client, message)
        else:
            await message.reply("⛔️ У вас нет прав для выполнения этой команды.")

    return wrapper


@is_admin
async def add_question(client, message):
    try:
        # Формат: /add_question <раунд> <текст> <правильный_ответ> [варианты]
        parts = message.text.split('\n', 3)
        if len(parts) < 3:
            await message.reply(
                "❌ Неверный формат. Используйте:\n"
                "/add_question <раунд>\n"
                "<текст вопроса>\n"
                "<правильный ответ>\n"
                "[варианты ответов через запятую для раунда 2]"
            )
            return

        _, round_num = parts[0].split()
        text = parts[1]
        correct_answer = parts[2]
        options = parts[3] if len(parts) > 3 else None

        session = Session()
        try:
            new_question = Question(
                round_number=int(round_num),
                text=text,
                correct_answer=correct_answer,
                options=options
            )
            session.add(new_question)
            session.commit()
            await message.reply("✅ Вопрос успешно добавлен!")
        finally:
            session.close()
    except Exception as e:
        await message.reply(f"❌ Ошибка при добавлении вопроса: {str(e)}")


@is_admin
async def reset_scores(client, message):
    session = Session()
    try:
        session.query(Team).update({Team.score: 0})
        session.commit()
        await message.reply("✅ Счет всех команд сброшен!")
    except Exception as e:
        await message.reply(f"❌ Ошибка при сбросе счета: {str(e)}")
    finally:
        session.close()


@is_admin
async def start_round(client, message):
    session = Session()
    try:
        # Формат: /start_round <номер_раунда>
        round_num = int(message.text.split()[1])
        if round_num not in [1, 2, 3]:
            await message.reply("❌ Номер раунда должен быть 1, 2 или 3")
            return

        questions = session.query(Question).filter_by(round_number=round_num).all()

        if not questions:
            await message.reply("❌ Нет вопросов для этого раунда!")
            return

        await message.reply(f"✅ Раунд {round_num} начинается!\nВопросов в раунде: {len(questions)}")
        # Здесь можно добавить логику начала раунда
    except Exception as e:
        await message.reply(f"❌ Ошибка при запуске раунда: {str(e)}")
    finally:
        session.close()

@is_admin
async def text_answer_rate(client, callback_query: CallbackQuery):
    _, question_id, team_id, rate = callback_query.data.split("_")
    session = Session()
    team = session.query(Team).filter_by(id=team_id).first()
    team.score += rate
    team.answers = json.dumps(json.loads(team.answers).append({"id": question_id, "rate": rate}))

    session.commit()

    await client.send_message(team.leader_id, f"Ваш ответ на вопрос №{question_id} оценили! Ваш балл: {rate}")

    session.close()