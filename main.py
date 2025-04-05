import os
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from bot.handlers import router
from database.connection import create_database
from bot.middlewares import CheckAdminMiddleware
from utils.parsers import BybitTickersParser

async def main():
    load_dotenv()
    await create_database()
    bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    CheckAdminMiddleware(dp)
    dp.include_router(router)
    bybit_parser = BybitTickersParser(bot=bot)
    parser_task = asyncio.create_task(bybit_parser.run())
    try:
        await dp.start_polling(bot)
    finally:
        await bybit_parser.stop() 
        await parser_task


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(main())
