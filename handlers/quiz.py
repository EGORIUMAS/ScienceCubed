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
    try:
        question = session.query(Question).get(question_id)
        if not question:
            return None

        keyboard = None
        if question.round_number == 1:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Правда", callback_data=f"answer_{question_id}_true"),
                    InlineKeyboardButton("Ложь", callback_data=f"answer_{question_id}_false")
                ]
            ])
        elif question.round_number == 2:
            options = json.loads(question.options or '{}')
            # Защита на случай, если options пустые или неправильно
            buttons = []
            for opt in ['A', 'B', 'C', 'D']:
                label = options.get(opt, opt)
                buttons.append([InlineKeyboardButton(f"{opt}: {label}", callback_data=f"answer_{question_id}_{opt}")])
            keyboard = InlineKeyboardMarkup(buttons)

        # Отправляем сообщение и возвращаем объект message, не ожидая таймер
        message = await client.send_message(
            chat_id,
            f"Вопрос:\n{question.text}\nВремя: {question.time_limit} сек.",
            reply_markup=keyboard
        )
        return message
    finally:
        session.close()

async def handle_answer(client, callback_query):
    _, question_id, answer = callback_query.data.split('_')
    question_id = int(question_id)

    session = Session()
    try:
        team = session.query(Team).filter_by(leader_id=callback_query.from_user.id).first()
        if not team:
            await callback_query.answer("Вы не в команде!")
            return

        question = session.query(Question).get(question_id)
        if not question:
            await callback_query.answer("Вопрос не найден!")
            return

        # уже есть ответ?
        existing = session.query(Answer).filter_by(team_id=team.id, question_id=question_id).first()
        if existing:
            await callback_query.answer("Вы уже ответили!")
            return

        if time.time() > (question.start_time or 0) + question.time_limit:
            await callback_query.answer("Время вышло!")
            return

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
        answers = json.loads(team.answers or '[]')
        answers.append({"id": question_id, "rate": rate})
        team.answers = json.dumps(answers)

        session.commit()

        # убираем кнопки у сообщения
        await callback_query.message.edit_reply_markup(None)

        await callback_query.answer("Ваш ответ принят!")
    finally:
        session.close()

async def handle_text_answer(client, message):
    session = Session()
    try:
        team = session.query(Team).filter_by(leader_id=message.from_user.id).first()
        if not team:
            await message.reply("Вы не в команде!")
            return

        question = session.query(Question).filter_by(current=True).first()
        if not question:
            await message.reply("Сейчас вопросов нет!")
            return
        if question.round_number != 3:
            await message.reply("Сейчас текстовых вопросов нет!")
            return
        if time.time() > (question.start_time or 0) + question.time_limit:
            await message.reply("Время вышло!")
            return
        existing = session.query(Answer).filter_by(team_id=team.id, question_id=question.id).first()
        if existing:
            await message.reply("Ответ уже отправлен!")
            return

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("0 баллов", callback_data=f"answer_{question.id}_{team.id}_0"),
                InlineKeyboardButton("1 балл", callback_data=f"answer_{question.id}_{team.id}_1"),
                InlineKeyboardButton("2 балла", callback_data=f"answer_{question.id}_{team.id}_2")
            ]
        ])
        await client.send_message(
            TG_ADMIN_USERNAME,
            f"Ответ от команды {team.name}:\n{message.text}",
            reply_markup=keyboard
        )
    finally:
        session.close()