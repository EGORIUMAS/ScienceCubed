from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from database.db import Team, Question, GameState
from config import DATABASE_URL, TG_ADMIN_USERNAME
from .quiz import send_question
from database.db import init_db
Session = init_db(DATABASE_URL)
import json
import time
import os
import asyncio
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

        if not round_questions:
            await message.reply("❌ В этом раунде нет вопросов.")
            return

        if gs.current_question_id:
            # Найти индекс текущего вопроса
            current_idx = next((i for i, q in enumerate(round_questions) if q.id == gs.current_question_id), None)
            if current_idx is None:
                # На случай, если current_question_id не в списке — start from 0
                next_idx = 0
            else:
                next_idx = current_idx + 1

            if next_idx >= len(round_questions):
                await message.reply("✅ Раунд завершен!")
                try:
                    socketio.emit('round_ended', {})
                except Exception as e:
                    logger.error(f"Emit round_ended failed: {e}", exc_info=True)
                gs.current_round = 0
                gs.current_question_id = None
                session.commit()
                return
            next_q = round_questions[next_idx]
        else:
            next_q = round_questions[0]

        # Устанавливаем следующий вопрос как текущий
        session.query(Question).update({Question.current: False})
        next_q.current = True
        next_q.start_time = int(time.time())
        gs.current_question_id = next_q.id
        session.commit()

        # Отправляем вопрос всем лидерам команд (не ожидаем таймеры тут)
        teams = session.query(Team).all()
        sent_messages = []  # список (chat_id, message_id)
        for team in teams:
            try:
                msg = await send_question(client, next_q.id, team.leader_id)
                if msg:
                    # В Pyrogram поле с id сообщения называется message_id
                    msg_id = getattr(msg, "message_id", None) or getattr(msg, "id", None)
                    chat_id = getattr(msg, "chat", None)
                    # chat_id может быть объектом Chat — взять chat.id, иначе использовать team.leader_id
                    if chat_id and hasattr(chat_id, "id"):
                        chat_id_val = chat_id.id
                    else:
                        chat_id_val = team.leader_id
                    if msg_id:
                        sent_messages.append((chat_id_val, msg_id))
            except Exception as e:
                # Не ломаем цикл, логируем проблему с отправкой конкретной команде
                logger.error(f"Failed to send question {next_q.id} to team {team.id}: {e}", exc_info=True)

        # Сразу уведомляем веб-клиентов о новом вопросе (фронт обновится)
        logger.info(f"Emitting new_question for qid={next_q.id} round={next_q.round_number}")
        try:
            socketio.emit('new_question', {
                'id': next_q.id,
                'text': next_q.text,
                'round': next_q.round_number,
                'options': next_q.options,
                'time_limit': next_q.time_limit,
                'total_questions': len(round_questions)
            }, namespace="/")
            logger.info("new_question emmited")
        except Exception as e:
            logger.error(f"Emit new_question failed: {e}", exc_info=True)

        # Таймер: фоновая async задача, не блокирует handler
        async def timer_coroutine(time_limit, messages_to_edit):
            remaining = time_limit
            try:
                while remaining > 0:
                    try:
                        logger.info(f"Emitting timer_update for qid={next_q.id} round={next_q.round_number}, time: {remaining}")
                        socketio.emit('timer_update', {'time': remaining})
                    except Exception as e:
                        logger.debug(f"timer_emit error: {e}")
                    await asyncio.sleep(1)
                    remaining -= 1
                try:
                    logger.info(f"Emitting timer_end for qid={next_q.id} round={next_q.round_number}")
                    socketio.emit('timer_end', {})
                except Exception as e:
                    logger.debug(f"timer_end emit error: {e}")

                # По окончании таймера пробуем убрать клавиатуры у отправленных сообщений
                for (chat_id_val, msg_id) in messages_to_edit:
                    try:
                        # Попытка удалить reply_markup; если нет изменений — ловим ошибку
                        await client.edit_message_reply_markup(chat_id_val, msg_id, reply_markup=None)
                    except Exception as e:
                        # Игнорируем MessageNotModified и другие ошибки редактирования
                        logger.debug(f"Could not edit reply_markup for chat {chat_id_val} msg {msg_id}: {e}")
            except Exception as e:
                logger.error(f"Error in timer_coroutine: {e}", exc_info=True)

        # Запускаем таймер как background task
        asyncio.create_task(timer_coroutine(next_q.time_limit, sent_messages))

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
        if not gs or not gs.current_question_id:
            await message.reply("❌ Нет текущего вопроса")
            return

        question = session.query(Question).get(gs.current_question_id)
        teams = session.query(Team).order_by(Team.score.desc()).all()
        teams_data = [{'id': t.id, 'name': t.name, 'score': t.score, 'answers': t.answers} for t in teams]

        try:
            logger.info(f"Emitting show_results for qid={question.id} round={question.round_number}")
            socketio.emit('show_results', {
                'correct_answer': question.correct_answer,
                'teams': teams_data
            })
        except Exception as e:
            logger.error(f"Emit show_results failed: {e}", exc_info=True)

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

@is_admin
async def load_questions(client, message):
    logger.debug(f"Processing /load_questions command from user {message.from_user.id}")
    try:
        # Путь к файлу questions.json в корне проекта
        json_path = os.path.join(os.path.dirname(__file__), '..', 'questions.json')
        if not os.path.exists(json_path):
            await message.reply("❌ Файл questions.json не найден в корне проекта!")
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)

        if not isinstance(questions_data, list):
            await message.reply("❌ Неверный формат questions.json: ожидается список вопросов.")
            return

        session = Session()
        try:
            added = 0
            for q in questions_data:
                # Валидация полей
                if not all(key in q for key in ['round_number', 'text', 'correct_answer']):
                    await message.reply(f"❌ Неверный формат вопроса: {q}. Требуются round_number, text, correct_answer.")
                    continue

                round_num = q['round_number']
                if round_num not in [1, 2, 3]:
                    await message.reply(f"❌ Неверный номер раунда в вопросе: {round_num}. Должен быть 1, 2 или 3.")
                    continue

                options = None
                if 'options' in q and round_num == 2:
                    opts = q['options']
                    if not (isinstance(opts, list) and len(opts) == 4):
                        await message.reply(f"❌ Для раунда 2 нужно ровно 4 варианта ответа в вопросе: {q['text']}.")
                        continue
                    options = json.dumps({
                        'A': opts[0],
                        'B': opts[1],
                        'C': opts[2],
                        'D': opts[3]
                    })

                time_limit = q.get('time_limit', 30)
                if not isinstance(time_limit, int) or time_limit <= 0:
                    await message.reply(f"❌ Неверное время для вопроса: {q['text']}. Установлено 30 сек.")
                    time_limit = 30

                # Проверка на существование вопроса
                existing = session.query(Question).filter_by(
                    round_number=round_num,
                    text=q['text']
                ).first()
                if existing:
                    logger.info(f"Вопрос уже существует: {q['text']}")
                    continue

                new_question = Question(
                    round_number=round_num,
                    text=q['text'],
                    correct_answer=q['correct_answer'],
                    options=options,
                    time_limit=time_limit
                )
                session.add(new_question)
                added += 1

            session.commit()
            await message.reply(f"✅ Успешно добавлено {added} вопросов из questions.json!")
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error in load_questions: {str(e)}", exc_info=True)
        await message.reply(f"❌ Ошибка при загрузке вопросов: {str(e)}")