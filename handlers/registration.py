from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.db import Team, Player
from config import DATABASE_URL
from database.db import init_db
Session = init_db(DATABASE_URL)
from utils.rate_limiter import RateLimiter

@Client.on_message(filters.command("start") & filters.private)
@RateLimiter(seconds=5)  # 1 запрос каждые 5 секунд
async def start_registration(client, message):
    # Проверка, является ли пользователь уже участником команды
    session = Session()
    player = session.query(Player).filter_by(telegram_id=message.from_user.id).first()

    if player:
        await message.reply("Вы уже зарегистрированы в команде!")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Создать команду", callback_data="create_team")],
        [InlineKeyboardButton("Присоединиться к команде", callback_data="join_team")]
    ])

    await message.reply(
        "Добро пожаловать в викторину!\n"
        "Выберите действие:",
        reply_markup=keyboard
    )


@Client.on_callback_query(filters.regex("create_team"))
async def create_team_handler(client, callback_query: CallbackQuery):
    # Создание новой команды
    await client.send_message(
        callback_query.from_user.id,
        "Введите название команды:"
    )
    # Установка состояния ожидания названия команды
    client.user_state[callback_query.from_user.id] = "waiting_team_name"


@Client.on_message(filters.private & filters.text)
async def handle_team_creation(client, message):
    user_state = client.user_state.get(message.from_user.id)

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

        # Добавление лидера как игрока
        new_player = Player(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            team_id=new_team.id
        )
        session.add(new_player)

        session.commit()

        await message.reply(
            f"Команда '{message.text}' успешно создана!\n"
            "Теперь добавьте остальных участников (до 3 человек).\n"
            "Отправьте их @username по одному в сообщении."
        )

        client.user_state[message.from_user.id] = "adding_players"