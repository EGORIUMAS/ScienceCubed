from .registration import start_registration, create_team_handler, handle_team_creation
from .quiz import send_question, handle_answer
from .admin import add_question, reset_scores, start_round
from .common import help_command, rules_command, status_command, leaderboard_command


def register_handlers(bot):
    """Регистрация всех обработчиков команд бота"""
    # Регистрация команд
    bot.add_handler(start_registration)
    bot.add_handler(create_team_handler)
    bot.add_handler(handle_team_creation)

    # Регистрация обработчиков викторины
    bot.add_handler(send_question)
    bot.add_handler(handle_answer)

    # Регистрация админских команд
    bot.add_handler(add_question)
    bot.add_handler(reset_scores)
    bot.add_handler(start_round)

    # Регистрация общих команд
    bot.add_handler(help_command)
    bot.add_handler(rules_command)
    bot.add_handler(status_command)
    bot.add_handler(leaderboard_command)
    print("Хендлеры добавлены")