import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from bot.handlers import router
from database.connection import create_database
from bot.middlewares import CheckAdminMiddleware

async def main():
    load_dotenv()
    await create_database()
    bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher()
    CheckAdminMiddleware(dp)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
