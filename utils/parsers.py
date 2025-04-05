import asyncio
import logging
import os
from typing import Optional

import aiohttp
import certifi
import ssl
from dotenv import load_dotenv
from decimal import Decimal

from database.requests import get_all_positions, update_tokens_prices
from utils.common import symbols_list

load_dotenv()
ADMIN_ID = int(os.getenv("ADMIN_ID"))

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

    async def fetch_tickers_bybit(
        self, session: aiohttp.ClientSession, symbol: str
    ) -> tuple[str, Decimal] | None:
        """Получение цены для заданного токена."""
        url = f"{self.bybit_url}/v5/market/tickers?category={self.category}&symbol={symbol}USDT"
        async with self.semaphore:
            try:
                async with session.get(url) as response:
                    data = await response.json()
                    if data["retCode"] == 0:
                        price = Decimal(data["result"]["list"][0]["lastPrice"])
                        logger.info(f"Цена для {symbol}: {price}")
                        return symbol, price
                    else:
                        logger.error(f"Ошибка API для {symbol}: {data['retMsg']}")
                        # Если токен не найден, удаляем его из списка и отправляем уведомление
                        if data.get("retMsg") == "invalid symbol" or data.get("retCode") == 10001:
                            if symbol in symbols_list:
                                symbols_list.remove(symbol)
                                if self.bot:
                                    await self.bot.send_message(
                                        chat_id=ADMIN_ID,
                                        text=(f"❗️ Токен <b>{symbol}</b> отсутствует на Bybit, "
                                              f"уведомлений по его цене <b>не будет</b>."),
                                        parse_mode="HTML",
                                    )
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
                    results = await asyncio.gather(*self.tasks)
                    prices = {}
                    for result in results:
                        if result:
                            symbol, price = result
                            prices[symbol] = price
                    if prices:
                        await update_tokens_prices(prices)
                        # Проверяем, достигла ли цена токена цены фиксации тела инвестиций
                        for symbol, price in prices.items():
                            token = await get_token_or_info(symbol=symbol)
                            if token and token.position and token.position.bodyfix_price_usd:
                                if price >= token.position.bodyfix_price_usd:
                                    if self.bot:
                                        await self.bot.send_message(
                                            chat_id=ADMIN_ID,
                                            text=(f"🎯 Цена токена <b>{symbol}</b> достигла цены фиксации тела: "
                                                  f"<b>{price}$</b>"),
                                            parse_mode="HTML",
                                        )
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
