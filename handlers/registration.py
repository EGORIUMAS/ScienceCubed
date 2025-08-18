from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from database.db import Team
from config import DATABASE_URL, TG_ADMIN_USERNAME
from database.db import init_db
Session = init_db(DATABASE_URL)
from utils.rate_limiter import RateLimiter
import json

user_states = {}

#@RateLimiter(seconds=5)  # 1 запрос каждые 5 секунд
async def start_registration(client, message):
    if message.from_user.username == TG_ADMIN_USERNAME:
        await message.reply("Добро пожаловать, администратор! Но, увы, эта команда не для вас")
        return
    # Проверка, является ли пользователь уже участником команды
    session = Session()
    player = session.query(Team).filter_by(leader_id=message.from_user.id).first()

    if player:
        await message.reply("Вы уже зарегистрировали (или начали) команду!")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Создать команду", callback_data="create_team")]
    ])

    await message.reply(
        "Добро пожаловать в викторину!\n\n"
        'Домашнее задание от Леонида Модестовича: посмотреть 17 серию 3 сезона "Пингвинёнка Пороро" и послушать песнь "Совы нежные"',
        reply_markup=keyboard
    )


#@RateLimiter(seconds=5)
async def create_team_handler(client, callback_query: CallbackQuery):
    # Создание новой команды
    await client.send_message(
        callback_query.from_user.id,
        "Введите название команды:"
    )
    # Установка состояния ожидания названия команды
    user_states[callback_query.from_user.id] = "waiting_team_name"


#@RateLimiter(seconds=5)
async def handle_team_creation(client: Client, message: Message):
    user_state = user_states.get(message.from_user.id)

    if user_state == "waiting_team_name":
        session = Session()

        # Проверка существования команды с таким названием
        existing_team = session.query(Team).filter_by(name=message.text).first()
        if existing_team:
            await message.reply("Команда с таким названием уже существует!")
            return

        # Создание новой команды
        new_team = Team(
            name=message.text,
            leader_id=message.from_user.id
        )
        session.add(new_team)

        session.commit()

        await message.reply(
            f"Команда '{message.text}' успешно создана!\n\n"
            "Теперь добавьте остальных участников (до 3 человек).\n"
            "Отправьте их имена, фамилии и команды по одному человеку в сообщении.\n"
            "Если людей в команде меньше 4, в конце отправьте 0.\n\n"
            "Не забудьте добавить себя!"
        )

        user_states[message.from_user.id] = "adding_players"

        session.close()
    elif user_state == "adding_players":
        session = Session()

        team = session.query(Team).filter_by(leader_id=message.from_user.id).first()
        players = json.loads(team.players)

        if message.text == "0":
            if len(players) == 0:
                await message.reply("В команде не может быть 0 человек!")
                session.close()
                return
            user_states[message.from_user.id] = "done"
            await client.send_message(message.from_user.id, "Все участники команды успешно добавлены! Ожидайте.")
            session.close()
        else:
            players.append(message.text)
            team.players = json.dumps(players)
            session.commit()
            session.close()

            await client.send_message(message.from_user.id, f"Участник {message.text} успешно добавлен!")

            if len(players) == 4:
                user_states[message.from_user.id] = "done"
                await client.send_message(message.from_user.id, "Все участники команды успешно добавлены! Ожидайте.")