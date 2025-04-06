import asyncio
import logging
import os
from typing import Optional

import aiohttp
import certifi
import ssl
from dotenv import load_dotenv
from decimal import Decimal

from database.requests import get_all_positions, update_tokens_prices, get_token_or_info
from utils.common import symbols_list, bodyfix_notified_tokens, drawdown_last_prices
import bot.keyboards as kb

load_dotenv()
ADMIN_ID = int(os.getenv("ADMIN_ID"))
DRAWDOWN_PERCENTAGE = int(os.getenv("DRAWDOWN_PERCENTAGE"))

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
        if positions:
            symbols_list.extend(
                position.token.symbol 
                for position in positions 
                if position.token and position.token.symbol not in symbols_list
            )
            logger.info(f"Инициализировано {len(symbols_list)} токенов")

    async def check_api_health(self, session: aiohttp.ClientSession) -> bool:
        """Проверка доступности API Bybit."""
        url = f"{self.bybit_url}/v5/market/time"
        try:
            async with session.get(url) as response:
                data = await response.json()
                return data["retCode"] == 0
        except Exception as e:
            logger.error(f"Ошибка при проверке доступности API Bybit: {e}")
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
                                              f"уведомлений по его цене <b>не будет</b>.")
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
                api_healthy = await self.check_api_health(session=self.session)

                if api_healthy and symbols_list:
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
                        symbols = list(prices.keys())
                        tokens = await get_token_or_info(symbols=symbols)

                        # Фильтруем список для отправки уведомлений о фиксации тела
                        bodyfix_tokens = [
                            (token, prices.get(token.symbol))
                            for token in tokens
                            if (token.position and 
                                prices.get(token.symbol, 0) >= token.position.bodyfix_price_usd and
                                token.symbol not in bodyfix_notified_tokens)  
                        ]

                        # Фильтруем список для отправки уведомлений о просадке
                        drawdown_tokens = []
                        for token in tokens:
                            if not token.position:
                                continue
                                
                            symbol = token.symbol
                            price = prices.get(symbol, 0)
                            entry_price = token.position.entry_price
                            if price >= entry_price:
                                continue
                            drawdown_percent = ((entry_price - price) / entry_price) * 100
                            if drawdown_percent < DRAWDOWN_PERCENTAGE:
                                continue
                            
                            # Получаем последнюю цену, по которой было отправлено уведомление
                            last_notified_price = drawdown_last_prices.get(symbol)
                            
                            # Первое уведомление о просадке (ранее не отправлялось)
                            if last_notified_price is None:
                                drawdown_tokens.append((token, price))
                                continue
                                
                            # Рассчитываем просадку от последней цены уведомления
                            additional_drawdown = ((last_notified_price - price) / last_notified_price) * 100
                            
                            # Отправляем повторное уведомление только при значительной дополнительной просадке
                            if additional_drawdown >= DRAWDOWN_PERCENTAGE:
                                drawdown_tokens.append((token, price))
                                
                        # Отправляем уведомления о фиксации тела
                        for token, price in bodyfix_tokens:
                            if self.bot:
                                await self.bot.send_message(
                                    chat_id=ADMIN_ID,
                                    text=(
                                        f"🎯 Цена токена <b>{token.symbol}</b> "
                                        f"достигла <b>цены фиксации тела!</b>"
                                    ),
                                    reply_markup=await kb.to_position_button(
                                        token.position.id
                                    ),
                                )
                                # Добавляем токен в множество уведомленных
                                bodyfix_notified_tokens.add(token.symbol)
                                logger.info(f"Отправлено уведомление по токену {token.symbol}")

                        # Отправляем уведомления о просадке
                        for token, price in drawdown_tokens:
                            if self.bot:
                                drawdown_percent = ((token.position.entry_price - price) / token.position.entry_price) * 100
                                await self.bot.send_message(
                                    chat_id=ADMIN_ID,
                                    text=(
                                        f"📉 <b>Просадка по {token.symbol}!</b>\n\n"
                                        f"Текущая цена: <b>${price}</b>\n"
                                        f"Просадка: <b><i>-{drawdown_percent:.2f}%</i></b>"
                                    ),
                                    reply_markup=await kb.to_position_button(
                                        token.position.id
                                    ),
                                )
                                # Обновляем последнюю цену в словаре отслеживания просадки
                                drawdown_last_prices[token.symbol] = price
                                logger.info(
                                    f"Отправлено уведомление о просадке {drawdown_percent}% "
                                    f"по токену {token.symbol}"
                                )
                    else:
                        logger.warning("Не удалось получить цены ни для одного токена")
                    self.tasks = []
                elif not symbols_list:
                    logger.warning("Список символов пуст.")
                else:
                    logger.error("API Bybit недоступен.")

                logger.info("Парсер уходит в сон на 60 секунд")
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
