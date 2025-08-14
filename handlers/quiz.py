from pyrogram import Client, filters
from database.db import Team, Player, Question
from config import DATABASE_URL
from database.db import init_db
Session = init_db(DATABASE_URL)
import asyncio
import json


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


@Client.on_callback_query(filters.regex("^answer_"))
async def handle_answer(client, callback_query):
    _, question_id, answer = callback_query.data.split('_')
    question_id = int(question_id)

    session = Session()

    # Проверка, не истекло ли время
    question = session.query(Question).get(question_id)
    if not question:
        await callback_query.answer("Вопрос не найден!")
        return

    # Сохранение ответа
    new_answer = Answer(
        player_id=callback_query.from_user.id,
        question_id=question_id,
        answer_text=answer,
        is_correct=(answer == question.correct_answer)
    )
    session.add(new_answer)
    session.commit()

    await callback_query.answer("Ваш ответ принят!")