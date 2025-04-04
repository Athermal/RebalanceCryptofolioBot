import asyncio
import logging
from typing import Optional

import aiohttp
import certifi
import ssl

from database.requests import get_all_positions
from utils.common import symbols_list

logger = logging.getLogger(__name__)


class BybitTickersParser:
    """Класс парсера цен токенов из symbols_list с Bybit"""

    def __init__(self, bot: Optional[object] = None):
        self.semaphore = asyncio.Semaphore(15)
        self.bybit_url = "https://api.bybit.com/"
        self.category = "spot"
        self.bot = bot
        self.is_running = False
        self.session: Optional[aiohttp.ClientSession] = None
        self.tasks: list[asyncio.Task] = []
        self.sleep_task: Optional[asyncio.Task] = None

    async def init_tokens(self) -> None:
        """Инициализация токенов в уже созданных позициях"""
        positions = await get_all_positions()
        symbols_list.extend(
            position.token.symbol 
            for position in positions 
            if position.token and position.token.symbol not in symbols_list
        )

    async def check_api_health(self, session: aiohttp.ClientSession) -> bool:
        """Проверка доступности API Bybit."""
        url = f"{self.bybit_url}/v5/market/time"
        try:
            async with session.get(url) as response:
                data = await response.json()
                return data["retCode"] == 0
        except Exception:
            return False

    async def fetch_tickers_bybit(self, session: aiohttp.ClientSession, symbol: str) -> None:
        """Получение цены для заданного токена."""
        url = f"{self.bybit_url}/v5/market/tickers?category={self.category}&symbol={symbol}USDT"
        async with self.semaphore:
            try:
                async with session.get(url) as response:
                    data = await response.json()
                    if data["retCode"] == 0:
                        price = data["result"]["list"][0]["lastPrice"]
                        logger.info(f"Цена для {symbol}: {price}")
                    else:
                        logger.error(f"Ошибка API для {symbol}: {data['retMsg']}")
            except Exception as e:
                logger.error(f"Ошибка при парсинге {symbol}: {e}")

    async def run(self) -> None:
        """Запуск парсера"""
        self.is_running = True
        await self.init_tokens()

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context),
            timeout=aiohttp.ClientTimeout(total=60),
        )
        try:
            while self.is_running:
                if await self.check_api_health(session=self.session) and symbols_list:
                    self.tasks = [
                        asyncio.create_task(
                            self.fetch_tickers_bybit(self.session, symbol)
                        )
                        for symbol in symbols_list
                    ]
                    await asyncio.gather(*self.tasks)
                    self.tasks = []
                elif not symbols_list:
                    logger.warning("Список символов пуст.")
                else:
                    logger.error("API Bybit недоступен.")

                self.sleep_task = asyncio.create_task(asyncio.sleep(60))
                try:
                    await self.sleep_task
                except asyncio.CancelledError:
                    break
        except Exception as e:
            logger.error(f"Ошибка в парсере: {e}")
        finally:
            if self.session:
                await self.session.close()
                self.session = None
            logger.info("Парсер Bybit был остановлен.")

    async def stop(self) -> None:
        """Остановка парсера"""
        self.is_running = False
        for task in self.tasks:
            task.cancel()
        if self.sleep_task:
            self.sleep_task.cancel()
