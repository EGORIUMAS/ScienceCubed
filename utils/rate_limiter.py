import time

user_timestamps = {}

def RateLimiter(seconds=5):
    def decorator(func):
        async def wrapper(client, message, *args, **kwargs):
            user_id = message.from_user.id
            now = time.time()
            last = user_timestamps.get(user_id, 0)
            if now - last < seconds:
                await message.reply("Пожалуйста, подождите...")
                return
            user_timestamps[user_id] = now
            return await func(client, message, *args, **kwargs)
        return wrapper
    return decorator