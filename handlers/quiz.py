from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.db import Team, Question, Answer
from config import DATABASE_URL, TG_ADMIN_USERNAME
from database.db import init_db
Session = init_db(DATABASE_URL)
import asyncio
import json
import time


async def send_question(client, question_id, chat_id):
    session = Session()
    question = session.query(Question).get(question_id)

    if not question:
        return

    if question.round_number == 1:
        # Раунд 1: Правда/Ложь
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Правда", callback_data=f"answer_{question_id}_true"),
                InlineKeyboardButton("Ложь", callback_data=f"answer_{question_id}_false")
            ]
        ])
    elif question.round_number == 2:
        # Раунд 2: Варианты A, B, C, D
        options = json.loads(question.options)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(opt, callback_data=f"answer_{question_id}_{opt}")
             for opt in ['A', 'B', 'C', 'D']]
        ])
    else:
        # Раунд 3: Текстовый ответ
        keyboard = None

    # Отправка вопроса
    message = await client.send_message(
        chat_id,
        f"Вопрос:\n{question.text}",
        reply_markup=keyboard
    )

    # Запуск таймера
    await asyncio.sleep(question.time_limit)

    # Деактивация кнопок после истечения времени
    if keyboard:
        await message.edit_reply_markup(None)

    await client.send_message(
        chat_id,
        "Время истекло! Ответы больше не принимаются."
    )


async def handle_answer(client, callback_query):
    _, question_id, answer = callback_query.data.split('_')
    question_id = int(question_id)

    session = Session()

    team = session.query(Team).filter_by(leader_id=callback_query.from_user.id).first()

    # Проверка, не истекло ли время
    question = session.query(Question).get(question_id)
    if time.time() > question.start_time + question.time_limit:
        await callback_query.answer("Время вышло!")
        return

    # Сохранение ответа
    new_answer = Answer(
        team_id=team.id,
        question_id=question_id,
        answer_text=answer,
        is_correct=(answer == question.correct_answer)
    )
    session.add(new_answer)

    rate = 0
    if answer == question.correct_answer:
        team.score += 1
        rate = 1
    team.answers = json.dumps(json.loads(team.answers).append({"id": question_id, "rate": rate}))

    session.commit()

    session.close()

    await callback_query.answer("Ваш ответ принят!")

async def handle_text_answer(client, message):
    session = Session()

    team = session.query(Team).find_by(leader_id=message.from_user.id).first()

    try:
        question = session.query(Question).find_by(current=True).first()
    except:
        await message.reply("Сейчас вопросов нет!")
        return
    if question.round_number != 3:
        await message.reply("Сейчас текстовых вопросов нет!")
        return
    if time.time() > question.start_time + question.time_limit:
        await message.answer("Время вышло!")
        return


    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("0 баллов", callback_data=f"answer_{question.id}_{team.id}_0"),
            InlineKeyboardButton("1 балл", callback_data=f"answer_{question.id}_{team.id}_1"),
            InlineKeyboardButton("2 балла", callback_data=f"answer_{question.id}_{team.id}_2")
        ]
    ])
    message = await client.send_message(
        TG_ADMIN_USERNAME,
        f"Ответ:\n{message.text}",
        reply_markup=keyboard
    )