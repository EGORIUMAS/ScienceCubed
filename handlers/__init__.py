from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
import logging as logger

# Импорт всех необходимых обработчиков
from .registration import *
from .quiz import *
from .admin import *
from .common import *

# Настройка логирования
logger.basicConfig(level=logger.INFO)

def register_handlers(bot):
    logger.info("Handlers registration started")
    """Регистрация всех обработчиков команд бота"""
    try:
        # Регистрация общих команд
        bot.add_handler(MessageHandler(help_command, filters.command("help")))
        bot.add_handler(MessageHandler(rules_command, filters.command("rules")))
        bot.add_handler(MessageHandler(status_command, filters.command("status")))
        bot.add_handler(MessageHandler(leaderboard_command, filters.command("leaderboard")))
        logger.info("Common command handlers registered")

        # Регистрация команд для регистрации команд
        bot.add_handler(MessageHandler(start_registration, filters.command("Start")))
        bot.add_handler(CallbackQueryHandler(create_team_handler, filters.regex("create_team")))
        bot.add_handler(MessageHandler(handle_team_creation, filters.text))
        logger.info("Registration handlers registered")

        # Регистрация команд администратора
        bot.add_handler(MessageHandler(add_question, filters.command("add_question")))
        bot.add_handler(MessageHandler(reset_scores, filters.command("reset_scores")))
        bot.add_handler(MessageHandler(start_round, filters.command("start_round")))
        logger.info("Admin command handlers registered")

        # Регистрация обработчиков ответов на вопросы
        bot.add_handler(CallbackQueryHandler(
            handle_answer,
            filters.regex("^answer_")
        ))
        bot.add_handler(MessageHandler(handle_text_answer, filters.text))
        logger.info("Quiz handlers registered")

        logger.info("All handlers registered successfully")
    except Exception as e:
        logger.error(f"Error registering handlers: {e}", exc_info=True)
        raise

def remove_handlers(bot):
    """Удаление всех обработчиков команд бота"""
    try:
        bot.remove_handler(*bot.handlers)
        logger.info("All handlers removed successfully")
    except Exception as e:
        logger.error(f"Error removing handlers: {e}", exc_info=True)

# Словарь для хранения состояний пользователей
user_states = {}

# Константы состояний
class States:
    IDLE = "idle"
    WAITING_TEAM_NAME = "waiting_team_name"
    WAITING_TEAM_JOIN = "waiting_team_join"
    WAITING_ANSWER = "waiting_answer"

# Функции для работы с состояниями
def get_user_state(user_id):
    """Получить текущее состояние пользователя"""
    return user_states.get(user_id, States.IDLE)

def set_user_state(user_id, state):
    """Установить состояние пользователя"""
    user_states[user_id] = state
    logger.debug(f"User {user_id} state set to {state}")

def clear_user_state(user_id):
    """Очистить состояние пользователя"""
    if user_id in user_states:
        del user_states[user_id]
        logger.debug(f"User {user_id} state cleared")