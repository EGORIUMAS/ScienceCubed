from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from database.db import Team, Question, GameState
from config import DATABASE_URL, TG_ADMIN_USERNAME
from .quiz import send_question
from database.db import init_db
Session = init_db(DATABASE_URL)
import json
import time
import threading
from web.app import socketio
import logging as logger

logger.basicConfig(level=logger.INFO)

def is_admin(func):
    async def wrapper(client, message):
        logger.debug(f"Checking admin status for user USERNAME: {message.from_user.username}, expected TG_ADMIN_USERNAME: {TG_ADMIN_USERNAME}")
        if message.from_user.username == TG_ADMIN_USERNAME:
            logger.debug(f"User {message.from_user.username} is admin, proceeding with {func.__name__}")
            await func(client, message)
        else:
            logger.warning(f"User {message.from_user.username} is not admin, rejecting command")
            await message.reply("⛔️ У вас нет прав для выполнения этой команды.")
    return wrapper

@is_admin
async def add_question(client, message):
    logger.debug(f"Processing /add_question command from user {message.from_user.id}")
    try:
        parts = message.text.split('\n', 4)
        if len(parts) < 3:
            await message.reply(
                "❌ Неверный формат. Используйте:\n"
                "/add_question <раунд>\n"
                "<текст вопроса>\n"
                "<правильный ответ>\n"
                "[варианты ответов через запятую для раунда 2]\n"
                "[время в секундах]"
            )
            return

        _, round_num = parts[0].split()
        text = parts[1]
        correct_answer = parts[2]
        options_input = parts[3] if len(parts) > 3 else None
        time_limit = int(parts[4]) if len(parts) > 4 and parts[4].strip().isdigit() else 30

        options = None
        if options_input and int(round_num) == 2:
            opts = [o.strip() for o in options_input.split(',')]
            if len(opts) == 4:
                options = json.dumps({
                    'A': opts[0],
                    'B': opts[1],
                    'C': opts[2],
                    'D': opts[3]
                })
            else:
                await message.reply("❌ Для раунда 2 нужно ровно 4 варианта через запятую.")
                return

        session = Session()
        try:
            new_question = Question(
                round_number=int(round_num),
                text=text,
                correct_answer=correct_answer,
                options=options,
                time_limit=time_limit
            )
            session.add(new_question)
            session.commit()
            await message.reply(f"✅ Вопрос успешно добавлен! Время: {time_limit} сек.")
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error in add_question: {str(e)}", exc_info=True)
        await message.reply(f"❌ Ошибка при добавлении вопроса: {str(e)}")

@is_admin
async def reset_scores(client, message):
    logger.debug(f"Processing /reset_scores command from user {message.from_user.id}")
    session = Session()
    try:
        session.query(Team).update({Team.score: 0})
        session.commit()
        await message.reply("✅ Счет всех команд сброшен!")
    except Exception as e:
        logger.error(f"Error in reset_scores: {str(e)}", exc_info=True)
        await message.reply(f"❌ Ошибка при сбросе счета: {str(e)}")
    finally:
        session.close()

@is_admin
async def start_round(client, message):
    session = Session()
    logger.debug(f"Processing /start_round command from user {message.from_user.id}")
    try:
        round_num = int(message.text.split()[1])
        if round_num not in [1, 2, 3]:
            await message.reply("❌ Номер раунда должен быть 1, 2 или 3")
            return

        questions = session.query(Question).filter_by(round_number=round_num).order_by(Question.id).all()

        if not questions:
            await message.reply("❌ Нет вопросов для этого раунда!")
            return

        gs = session.query(GameState).first()
        if not gs:
            gs = GameState()
            session.add(gs)

        gs.current_round = round_num
        gs.current_question_id = None
        session.commit()

        await message.reply(f"✅ Раунд {round_num} готов! Вопросов: {len(questions)}\nИспользуйте /next_question для запуска первого вопроса.")
    except Exception as e:
        logger.error(f"Error in start_round: {str(e)}", exc_info=True)
        await message.reply(f"❌ Ошибка при запуске раунда: {str(e)}")
    finally:
        session.close()

@is_admin
async def next_question(client, message):
    logger.debug(f"Processing /next_question command from user {message.from_user.id}")
    session = Session()
    try:
        gs = session.query(GameState).first()
        if not gs or gs.current_round == 0:
            await message.reply("❌ Сначала запустите раунд с помощью /start_round")
            return

        round_questions = session.query(Question).filter_by(round_number=gs.current_round).order_by(Question.id).all()

        if gs.current_question_id:
            current_idx = next(i for i, q in enumerate(round_questions) if q.id == gs.current_question_id)
            next_idx = current_idx + 1
            if next_idx >= len(round_questions):
                await message.reply("✅ Раунд завершен!")
                socketio.emit('round_ended', {}, broadcast=True)
                gs.current_round = 0
                gs.current_question_id = None
                session.commit()
                return
            next_q = round_questions[next_idx]
        else:
            next_q = round_questions[0]

        session.query(Question).update({Question.current: False})
        next_q.current = True
        next_q.start_time = int(time.time())
        gs.current_question_id = next_q.id
        session.commit()

        teams = session.query(Team).all()
        for team in teams:
            await send_question(client, next_q.id, team.leader_id)

        socketio.emit('new_question', {
            'id': next_q.id,
            'text': next_q.text,
            'round': next_q.round_number,
            'options': next_q.options,
            'time_limit': next_q.time_limit
        }, broadcast=True)

        def timer_thread(time_limit):
            remaining = time_limit
            while remaining > 0:
                socketio.emit('timer_update', {'time': remaining}, broadcast=True)
                time.sleep(1)
                remaining -= 1
            socketio.emit('timer_end', {}, broadcast=True)

        threading.Thread(target=timer_thread, args=(next_q.time_limit,), daemon=True).start()

        await message.reply(f"✅ Вопрос {next_q.id} запущен! Время: {next_q.time_limit} сек.")
    except Exception as e:
        logger.error(f"Error in next_question: {str(e)}", exc_info=True)
        await message.reply(f"❌ Ошибка: {str(e)}")
    finally:
        session.close()

@is_admin
async def show_results(client, message):
    logger.debug(f"Processing /show_results command from user {message.from_user.id}")
    session = Session()
    try:
        gs = session.query(GameState).first()
        if not gs.current_question_id:
            await message.reply("❌ Нет текущего вопроса")
            return

        question = session.query(Question).get(gs.current_question_id)
        teams = session.query(Team).order_by(Team.score.desc()).all()
        teams_data = [{'id': t.id, 'name': t.name, 'score': t.score} for t in teams]

        socketio.emit('show_results', {
            'correct_answer': question.correct_answer,
            'teams': teams_data
        }, broadcast=True)

        await message.reply("✅ Результаты отображены на сайте! Используйте /next_question для следующего вопроса.")
    except Exception as e:
        logger.error(f"Error in show_results: {str(e)}", exc_info=True)
        await message.reply(f"❌ Ошибка: {str(e)}")
    finally:
        session.close()

@is_admin
async def text_answer_rate(client, callback_query: CallbackQuery):
    logger.debug(f"Processing text_answer_rate callback from user {callback_query.from_user.id}")
    _, question_id, team_id, rate = callback_query.data.split("_")
    session = Session()
    try:
        team = session.query(Team).filter_by(id=team_id).first()
        if team:
            rate_val = int(rate)
            team.score += rate_val
            answers = json.loads(team.answers or '[]')
            answers.append({"id": question_id, "rate": rate_val})
            team.answers = json.dumps(answers)
            session.commit()
            await client.send_message(team.leader_id, f"Ваш ответ на вопрос №{question_id} оценили! Балл: {rate_val}")
    finally:
        session.close()