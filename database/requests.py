from decimal import Decimal
from turtle import pensize
from typing import Optional, Union, Any

from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from database.models import Deposit, Direction, Sector, Token, Position, Order
from database.connection import async_session
from utils.helpers import round_to_2
from utils.common import symbols_list, bodyfix_notified_tokens, drawdown_last_prices

async def add_deposit(amount_usd: Decimal) -> None:
    """
    Добавляет депозит и распределяет средства по направлениям, секторам и токенам.

    Args:
        amount_usd (Decimal): Сумма депозита в USD

    Raises:
        ValueError: Если сумма процентов направлений, секторов или токенов не равна 100%
    """
    async with async_session() as session:
        async with session.begin():
            session.add(Deposit(amount_usd=amount_usd))

            # Проверка, что направления в сумме дают 100%
            query = select(Direction)
            result = await session.execute(query)
            portfolio_directions = result.scalars().all()

            if portfolio_directions:
                query = select(func.sum(Direction.percentage))
                result = await session.execute(query)
                total_percentage_directions = result.scalar_one_or_none() or Decimal(0)
                if total_percentage_directions != Decimal(100):
                    raise ValueError(
                        f"❌ <b>Ошибка!</b>\n\nСуммарный % всех направлений в портфеле = "
                        f"<b>{total_percentage_directions}%</b>"
                        f", а для добавления депозита должен быть <b>ровно 100%!</b>"
                    )

            # Проверка, что секторы в сумме дают 100%
            query = select(Sector).options(selectinload(Sector.tokens))
            result = await session.execute(query)
            sectors = result.scalars().all()

            if sectors:
                query = select(func.sum(Sector.percentage))
                result = await session.execute(query)
                total_percentage_sectors = result.scalar_one_or_none() or Decimal(0)
                if total_percentage_sectors != Decimal(100):
                    raise ValueError(
                        f"❌ <b>Ошибка!</b>\n\nСуммарный % всех секторов = "
                        f"<b>{total_percentage_sectors}%</b>"
                        f", а для добавления депозита должен быть <b>ровно 100%!</b>"
                    )

            # Проверка, что токены в каждом секторе в сумме дают 100%
            for sector in sectors:
                total_percentage_tokens = sum(
                    token.percentage for token in sector.tokens
                )
                if total_percentage_tokens != Decimal(100):
                    raise ValueError(
                        f"❌ <b>Ошибка!</b>\n\nСуммарный % токенов "
                        f"в секторе <b>{sector.name}</b> = "
                        f"<b>{total_percentage_tokens}%</b>, "
                        f"а должен быть <b>ровно 100%!</b>"
                    )

            # Распределение средств по направлениям
            total_direction_balance = Decimal("0")
            for idx, direction in enumerate(portfolio_directions):
                # Последнее направление получает остаток для избежания ошибок округления
                if idx == len(portfolio_directions) - 1:
                    direction_balance = amount_usd - total_direction_balance
                else:
                    direction_balance = round_to_2(
                        amount_usd * (direction.percentage / Decimal(100))
                    )
                direction.balance_usd += direction_balance
                total_direction_balance += direction_balance

                # Распределение внутри рабочего капитала
                if direction.name == "Рабочий капитал":
                    # Распределение по секторам
                    total_sector_balance = Decimal("0")
                    for i, sector in enumerate(sectors[:-1]):
                        sector_balance = round_to_2(
                            direction_balance * (sector.percentage / Decimal(100))
                        )
                        sector.balance_usd += sector_balance
                        total_sector_balance += sector_balance

                        # Распределение по всем токенам кроме последнего
                        total_token_balance = Decimal("0")
                        for j, token in enumerate(sector.tokens[:-1]):
                            token_balance = round_to_2(
                                sector_balance * (token.percentage / Decimal(100))
                            )
                            token.balance_usd += token_balance
                            token.balance_entry_usd = round_to_2(
                                token.balance_usd * Decimal("0.10")
                            )
                            total_token_balance += token_balance

                        # Последний токен получает остаток для избежания ошибок округления
                        last_token_balance = sector_balance - total_token_balance
                        sector.tokens[-1].balance_usd += last_token_balance
                        sector.tokens[-1].balance_entry_usd = round_to_2(
                            sector.tokens[-1].balance_usd * Decimal("0.10")
                        )
                        # Вычитаем распределённую сумму из сектора
                        sector.balance_usd -= (total_token_balance + last_token_balance)

                    # Обработка последнего сектора для избежания ошибок округления
                    if sectors:
                        last_sector = sectors[-1]
                        last_sector_balance = direction_balance - total_sector_balance
                        last_sector.balance_usd += last_sector_balance

                        # Распределение по всем токенам кроме последнего
                        total_last_token_balance = Decimal("0")
                        for j, token in enumerate(last_sector.tokens[:-1]):
                            token_balance = round_to_2(
                                last_sector_balance * (token.percentage / Decimal(100))
                            )
                            token.balance_usd += token_balance
                            token.balance_entry_usd = round_to_2(
                                token.balance_usd * Decimal("0.10")
                            )
                            total_last_token_balance += token_balance

                        # Последний токен получает остаток для избежания ошибок округления
                        last_token_balance = (
                            last_sector_balance - total_last_token_balance
                        )
                        last_sector.tokens[-1].balance_usd += last_token_balance
                        last_sector.tokens[-1].balance_entry_usd = round_to_2(
                            last_sector.tokens[-1].balance_usd * Decimal("0.10")
                        )
                        last_sector.balance_usd -= (
                            total_last_token_balance + last_token_balance
                        )
                    # Вычитание израсходованный рабочий капитал
                    direction.balance_usd -= direction_balance


async def add_portfolio_directions() -> None:
    """
    Создает и добавляет в базу данных два основных направления портфеля:
    - Ликвидность (60%)
    - Рабочий капитал (40%)
    """
    async with async_session() as session:
        async with session.begin():
            liquidity = Direction(name="Ликвидность", percentage=Decimal("60.00"))
            working_capital = Direction(name="Рабочий капитал", percentage=Decimal("40.00"))
            session.add_all([liquidity, working_capital])


async def change_percentage_portfolio_direction(direction_name: str, percentage: Decimal) -> None:
    """
    Изменяет процентное соотношение направления портфеля.

    Args:
        direction_name: Название направления
        percentage: Новое процентное значение

    Raises:
        ValueError: Если общая сумма процентов превышает 100%
    """
    async with async_session() as session:
        async with session.begin():
            query = select(func.sum(Direction.percentage)).where(Direction.name != direction_name)
            result = await session.execute(query)
            not_inclusive_percentage = result.scalar_one_or_none() or Decimal(0)
            if not_inclusive_percentage + percentage > Decimal(100):
                text = (f'❌ <b>Ошибка!</b>\n\n'
                        f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                        f'❗️ <b>Обнулите % любого направления и попробуйте снова</b>')
                raise ValueError(text)
            query = select(Direction).where(Direction.name == direction_name)
            result = await session.execute(query)
            existing_record = result.scalar_one_or_none()
            existing_record.percentage = percentage


async def get_direction_or_info(
        direction_name: str,
        field: str = None,
        current_session: AsyncSession = None,
        ) -> Optional[Union[Direction, Any]]:
    """
    Получает направление портфеля или конкретное поле из него.

    Args:
        direction_name (str): Название направления
        field (str, optional): Название поля для получения. По умолчанию None
        current_session (AsyncSession, optional): Текущая сессия БД. По умолчанию None

    Returns:
        Optional[Union[Direction, Any]]: Направление целиком или значение конкретного поля
    """
    if field:
        query = select(getattr(Direction, field)).where(
            Direction.name == direction_name
        )
    else:
        query = select(Direction).where(Direction.name == direction_name)

    if current_session:
        result = await current_session.execute(query)
    else:
        async with async_session() as session:
            result = await session.execute(query)
    return result.scalar_one_or_none()


async def add_sector(sector_name: str, percentage: Decimal) -> None:
    """
    Добавляет новый сектор в портфель с указанным процентом.

    Args:
        sector_name (str): Название сектора
        percentage (Decimal): Процент сектора в портфеле

    Raises:
        ValueError: Если общая сумма процентов превышает 100% или сектор уже существует
    """
    async with async_session() as session:
        async with session.begin():
            query = select(func.sum(Sector.percentage)).where(Sector.name != sector_name)
            result = await session.execute(query)
            not_inclusive_percentage = result.scalar_one_or_none() or Decimal(0)

            if not_inclusive_percentage + percentage > Decimal(100):
                query = select(func.sum(Sector.percentage))
                all_percentage = await session.execute(query)
                all_percentage = all_percentage.scalar_one_or_none() or Decimal(0)
                residue = Decimal(100) - all_percentage
                if residue == Decimal(0):
                    text = (f'❌ <b>Ошибка!</b>\n\n'
                            f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                            f'Для установки новому сектору доступно: {residue}%\n\n'
                            f'❗️ <b>Удалите некоторые секторы, или измените их %</b>')
                    raise ValueError(text)
                else:
                    text = (f'❌ <b>Ошибка!</b>\n\n'
                            f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                            f'Для установки новому сектору доступно: {residue}%')
                    raise ValueError(text)
            query = select(Sector).where(Sector.name == sector_name)
            result = await session.execute(query)
            existing_record = result.scalar_one_or_none()
            if existing_record:
                text = (f'❌ <b>Ошибка!</b>\n\nСектор <b>{sector_name}</b> уже существует.\n\n'
                        f'<b>❓ Чтобы изменить процент, перейдите в сектор по кнопке из '
                        f'распределения по секторам.</b>')
                raise ValueError(text)
            else:
                session.add(Sector(name=sector_name, percentage=percentage))


async def get_all_sectors() -> Optional[list[Sector]]:
    """
    Получает список всех секторов из базы данных.

    Returns:
        Optional[list[Sector]]: Список объектов Sector, отсортированный по id.
        None если секторов нет.
    """
    async with async_session() as session:
        query = select(Sector).order_by(Sector.id)
        result = await session.execute(query)
        sectors = result.scalars().all()
        return sectors


async def get_sector_info(
    sector_id: int = None,
    sector_name: str = None,
    field: str = None
) -> Optional[Union[Sector, Any]]:
    """
    Получает информацию о секторе по его id или имени.

    Args:
        sector_id (int, optional): ID сектора. По умолчанию None.
        sector_name (str, optional): Название сектора. По умолчанию None.
        field (str, optional): Название поля для выборки конкретного атрибута. По умолчанию None.

    Returns:
        Optional[Union[Sector, Any]]: Объект сектора или значение конкретного поля.
        None если сектор не найден или не указаны параметры поиска.
    """
    if not (sector_id or sector_name):
        return None
    async with async_session() as session:
        if field:
            query = select(getattr(Sector, field))
        else:
            query = select(Sector).options(selectinload(Sector.tokens))
        if sector_name:
            query = query.where(Sector.name == sector_name)
        elif sector_id:
            query = query.where(Sector.id == sector_id)
        sector = await session.execute(query)
        return sector.scalar_one_or_none()


async def delete_sector(sector_id: int = None,
                        sector_name: str = None, sector: Sector = None) -> None:
    """
    Удаляет сектор из базы данных.

    Args:
        sector_id (int, optional): ID сектора. По умолчанию None.
        sector_name (str, optional): Название сектора. По умолчанию None.
        sector (Sector, optional): Объект сектора. По умолчанию None.

    Raises:
        ValueError: Если сектор не найден.
    """
    if not (sector_id or sector_name or sector):
        return None
    async with async_session() as session:
        async with session.begin():
            query = select(Sector)
            if sector_id:
                query = query.where(Sector.id == sector_id)
            elif sector_name:
                query = query.where(Sector.name == sector_name)
            elif sector:
                await session.delete(sector)
                return
            result = await session.execute(query)
            sector = result.scalar_one_or_none()
            if not sector:
                raise ValueError(f'❌ <b>Ошибка!</b>\n\nСектор не найден.')
            await session.delete(sector)


async def change_sector_percentage(percentage: Decimal, 
                                   sector_id: int = None, sector_name: str = None) -> None:
    """
    Изменяет процентное соотношение сектора в портфеле.

    Args:
        percentage (Decimal): Новое процентное значение
        sector_id (int, optional): ID сектора. По умолчанию None
        sector_name (str, optional): Название сектора. По умолчанию None

    Raises:
        ValueError: Если сектор не найден или общая сумма процентов превышает 100%

    Returns:
        None
    """
    if not (sector_id or sector_name):
        return None
    async with async_session() as session:
        async with session.begin():
            query = select(Sector)
            if sector_id:
                query = query.where(Sector.id == sector_id)
            elif sector_name:
                query = query.where(Sector.name == sector_name)
            sector = await session.execute(query)
            sector = sector.scalar_one_or_none()
            if not sector:
                raise ValueError('Сектор не найден')

            query = select(func.sum(Sector.percentage)).where(Sector.id != sector.id)
            result = await session.execute(query)
            not_inclusive_percentage = result.scalar_one_or_none() or Decimal(0)
            if not_inclusive_percentage + percentage > Decimal(100):
                query = select(func.sum(Sector.percentage))
                all_percentage = await session.execute(query)
                residue = Decimal(100) - (all_percentage.scalar_one_or_none() or Decimal(0))
                if residue == Decimal(0):
                    text = (f'❌ <b>Ошибка!</b>\n\n'
                            f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                            f'Для установки новому сектору доступно: 0%\n\n'
                            f'❗️ <b>Удалите некоторые секторы, или обнулите их %</b>')
                    raise ValueError(text)
                else:
                    text = (f'❌ <b>Ошибка!</b>\n\n'
                            f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                            f'Для установки новому сектору доступно: {residue}%')
                    raise ValueError(text)
            sector.percentage = percentage


async def add_token(sector_id: int, symbol: str, percentage: Decimal) -> None:
    """
    Добавляет новый токен в указанный сектор с заданным процентом.

    Args:
        sector_id (int): ID сектора
        symbol (str): Символ токена
        percentage (Decimal): Процент токена в секторе

    Raises:
        ValueError: Если общая сумма процентов превышает 100% или токен уже существует
    """
    async with async_session() as session:
        async with session.begin():
            query = select(func.sum(Token.percentage)).where(Token.symbol != symbol,
                                                             Token.sector_id == sector_id)
            result = await session.execute(query)
            total_percentage = result.scalar_one_or_none() or Decimal(0)
            if total_percentage + percentage > Decimal(100):
                all_percentage = await session.execute(select(func.sum(Token.percentage)).where(
                    Token.sector_id == sector_id))
                all_percentage = all_percentage.scalar_one_or_none() or Decimal(0)
                residue = Decimal(100) - all_percentage
                if residue == Decimal(0):
                    text = (f'❌ <b>Ошибка!</b>\n\n'
                            f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                            f'Для установки новому токену доступно: 0%\n\n'
                            f'❗️ <b>Удалите некоторые токены, или обнулите их %</b>')
                    raise ValueError(text)
                else:
                    text = (f'❌ <b>Ошибка!</b>\n\n'
                            f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                            f'Для установки новому токену доступно: {residue}%')
                    raise ValueError(text)

            query = select(Token).where(Token.symbol == symbol).options(selectinload(Token.sector))
            result = await session.execute(query)
            token = result.scalar_one_or_none()
            if token:
                sector_name = token.sector.name
                text = (f'❌ <b>Ошибка!</b>\n\nТокен <b>{symbol}</b> уже добавлен в сектор '
                        f'<b>{sector_name}</b>.\n\n'
                        f'<b>❓ Чтобы изменить процент, '
                        f'перейдите в токен по кнопке из его сектора.</b>')
                raise ValueError(text)
            else:
                session.add(Token(sector_id=sector_id, symbol=symbol, percentage=percentage))


async def change_token_percentage(percentage: Decimal, sector_id: int, token_id: int = None,
                                  symbol: str = None) -> None:
    """Изменяет процент токена в секторе.
    
    Args:
        percentage: Новый процент токена
        sector_id: ID сектора
        token_id: ID токена (опционально)
        symbol: Символ токена (опционально)
        
    Raises:
        ValueError: Если токен не найден или сумма процентов превышает 100%
    """
    if not (token_id or symbol):
        return None
    async with async_session() as session:
        async with session.begin():
            query = select(Token)
            if token_id:
                query = query.where(Token.id == token_id)
            elif symbol:
                query = query.where(Token.symbol == symbol)
            result = await session.execute(query)
            token = result.scalar_one_or_none()
            if not token:
                raise ValueError('Токен не найден')
            query = select(func.sum(Token.percentage)).where(Token.symbol != symbol,
                                                             Token.sector_id == sector_id)
            result = await session.execute(query)
            total_percentage = result.scalar() or Decimal(0)
            if total_percentage + percentage > Decimal(100):
                all_percentage = await session.execute(select(func.sum(Token.percentage)).where(
                    Token.sector_id == sector_id))
                residue = Decimal(100) - all_percentage.scalar()
                if residue == Decimal(0):
                    text = (f'❌ <b>Ошибка!</b>\n\n'
                            f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                            f'Для установки новому токену доступно: {residue}%\n\n'
                            f'❗️ <b>Удалите некоторые токены, или измените их %</b>')
                    raise ValueError(text)
                else:
                    text = (f'❌ <b>Ошибка!</b>\n\n'
                            f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                            f'Для установки новому токену доступно: {residue}%')
                    raise ValueError(text)
            token.percentage = percentage


async def get_token_or_info(
    token_id: int = None,
    symbol: str = None,
    field: str = None,
    current_session: AsyncSession = None,
    symbols: list[str] = None,
) -> Optional[Union[Token, Any, list[Token]]]:
    """Получение токена или его поля по ID или символу.
    
    Args:
        token_id: ID токена
        symbol: Символ токена
        field: Поле токена для получения
        current_session: Текущая сессия
        symbols: Список символов для пакетной загрузки
    
    Returns:
        Token, поле токена или список токенов
    """
    if not (token_id or symbol or symbols):
        return None
        
    if field:
        query = select(getattr(Token, field))
    else:
        query = select(Token).options(
            selectinload(Token.sector), selectinload(Token.position)
        )
        
    if symbols:
        query = query.where(Token.symbol.in_(symbols))
    elif token_id:
        query = query.where(Token.id == token_id)
    elif symbol:
        query = query.where(Token.symbol == symbol)
        
    if current_session:
        result = await current_session.execute(query)
    else:
        async with async_session() as session:
            result = await session.execute(query)
    if symbols:
        return result.scalars().all()
    else:
        return result.scalar_one_or_none()


async def delete_token(token_id: int = None, symbol: str = None, token: Token = None) -> None:
    """Удаляет токен из базы данных.
    
    Args:
        token_id: ID токена для удаления
        symbol: Символ токена для удаления
        token: Объект токена для удаления
        
    Raises:
        ValueError: Если токен не найден
    """
    if not (token_id or symbol or token):
        return None
    async with async_session() as session:
        async with session.begin():
            query = select(Token)
            if token_id:
                query = query.where(Token.id == token_id)
            elif symbol:
                query = query.where(Token.symbol == symbol)
            elif token:
                await session.delete(token)
                return
            result = await session.execute(query)
            token = result.scalar_one_or_none()
            if not token:
                raise ValueError(f'❌ <b>Ошибка!</b>\n\nТокен не найден.')
            await session.delete(token)


async def get_all_sector_tokens(sector_id: int = None,
                                sector: Sector = None) -> Optional[list[Token]]:
    """Получает все токены сектора.
    
    Args:
        sector_id: ID сектора
        sector: Объект сектора
        
    Returns:
        Список токенов сектора или None
    """
    if not (sector_id or sector):
        return None
    async with async_session() as session:
        query = select(Token)
        if sector_id:
            query = query.where(Token.sector_id == sector_id).order_by(Token.id)
        if sector:
            query = query.where(Token.sector_id == sector.id).order_by(Token.id)
        result = await session.execute(query)
        tokens = result.scalars().all()
        return tokens or None


async def buy_order(token_id: int, amount: Decimal, entry_price: Decimal) -> None:
    """Создает ордер на покупку токена.
    
    Args:
        token_id: ID токена
        amount: Количество токенов
        entry_price: Цена входа
        
    Raises:
        ValueError: Если превышен доступный баланс
    """
    async with async_session() as session:
        async with session.begin():
            token = await get_token_or_info(
                token_id=token_id, current_session=session
                )
            position = token.position if token.position else None
            token_symbol = token.symbol

            liquidity = await get_direction_or_info(
                direction_name="Ликвидность", current_session=session
                )

            invested_usd = amount * entry_price
            token_balance_entry_usd = token.balance_entry_usd
            allowed_liquidity_balance = liquidity.balance_usd * Decimal("0.02")

            if position or token_balance_entry_usd < Decimal("5"):
                allowed_balance = token_balance_entry_usd + allowed_liquidity_balance
            else:
                allowed_balance = token_balance_entry_usd

            if invested_usd > allowed_balance:
                text = (
                    "❌ <b>Ошибка! Ордер не был добавлен.</b>\n\n"
                    "Вы превысили максимально возможную сумму $ для покупки!\n\n"
                )
                raise ValueError(text)

            token_used = min(token_balance_entry_usd, invested_usd)
            liquidity_used = max(Decimal(0), invested_usd - token_balance_entry_usd)
            if liquidity_used > 0:
                liquidity.balance_usd -= liquidity_used
            token.balance_usd -= token_used

            order = Order(token_id=token_id, amount=amount, entry_price=entry_price)
            session.add(order)
            await session.flush()
            order.name = f"{order.type} #{order.id} — {token_symbol}"

            if position:
                position.amount += amount
                position.invested_usd += invested_usd
                position.entry_price = position.invested_usd / position.amount
                position.bodyfix_price_usd = position.entry_price * Decimal(2)
                if token_symbol in bodyfix_notified_tokens:
                    bodyfix_notified_tokens.remove(token_symbol)
                # Обновляем цену входа в словаре отслеживания просадки
                if token_symbol in drawdown_last_prices:
                    drawdown_last_prices[token_symbol] = position.entry_price
            else:
                await add_position(token_id=token_id, amount=amount, entry_price=entry_price)
                # Добавляем цену входа в словарь отслеживания просадки
                drawdown_last_prices[token_symbol] = entry_price


async def add_position(token_id: int, amount: Decimal, entry_price: Decimal) -> None:
    """Создает новую позицию по токену.
    
    Args:
        token_id: ID токена
        amount: Количество токенов
        entry_price: Цена входа
    """
    async with async_session() as session:
        async with session.begin():
            invested_usd = Decimal(amount * entry_price)
            bodyfix_price_usd = Decimal(entry_price * 2)
            token = await get_token_or_info(token_id=token_id)
            token_symbol = token.symbol
            position = Position(
                name=token_symbol,
                token_id=token_id,
                amount=amount,
                entry_price=entry_price,
                invested_usd=invested_usd,
                bodyfix_price_usd=bodyfix_price_usd,
            )
            if token_symbol not in symbols_list:
                symbols_list.append(token_symbol)
            # Добавляем цену входа в словарь отслеживания просадки
            drawdown_last_prices[token_symbol] = entry_price
            session.add(position)


async def sell_order(token_id: int, amount: Decimal) -> None:
    """Создает ордер на продажу токена.
    
    Args:
        token_id: ID токена
        amount: Количество токенов для продажи
        
    Raises:
        ValueError: Если позиция не найдена или недостаточно токенов
    """
    async with async_session() as session:
        async with session.begin():
            query = select(Token).options(joinedload(Token.position)).where(Token.id == token_id)
            result = await session.execute(query)
            token = result.scalar_one_or_none()
            if not token.position:
                text = f'❌ <b>Ошибка!</b> Позиция для токена {token.symbol} не найдена.'
                raise ValueError(text)
            token_symbol = token.symbol
            position = token.position
            if amount > position.amount:
                text = (f'❌ <b>Ошибка! Ордер не был добавлен.</b>\n\n'
                        f'Вы превысили максимально возможную сумму для продажи!\n\n'
                        f'⚖️<b>Для продажи токена "{token_symbol}" доступно: '
                        f'{position.amount} токенов</b>')
                raise ValueError(text)
            order = Order(token_id=token_id, amount=amount, entry_price=Decimal(0), type='sell')
            session.add(order)
            new_amount = position.amount - amount
            if new_amount == Decimal(0):
                await session.delete(position)
                if token_symbol in symbols_list:
                    symbols_list.remove(token_symbol)
            else:
                position.amount = new_amount
                position.invested_usd -= amount * position.entry_price


async def get_all_positions() -> Optional[list[Position]]:
    """Получает список всех позиций.
    
    Returns:
        Список позиций или None
    """
    async with async_session() as session:
        query = select(Position).options(joinedload(Position.token)).order_by(desc(Position.id))
        positions = await session.execute(query)
        positions = positions.scalars().all()
        return positions or None


async def get_all_usd_info() -> Optional[Decimal]:
    """Получает общую сумму USD во всех направлениях.
    
    Returns:
        Общая сумма USD или 0
    """
    async with async_session() as session:
        # Объединим все запросы в один
        query = select(
            select(Direction.balance_usd).where(Direction.name == 'Ликвидность').scalar_subquery(),
            select(func.sum(Position.invested_usd)).scalar_subquery(),
            select(func.sum(Token.balance_usd)).scalar_subquery()
        )
        result = await session.execute(query)
        usd_in_liquidity, usd_in_positions, usd_in_tokens = result.one_or_none()
        
        all_usd_sum = ((usd_in_positions or Decimal(0)) + (usd_in_tokens or Decimal(0))
                      + (usd_in_liquidity or Decimal(0)))
        return all_usd_sum or Decimal(0.00)


async def get_positions_usd_info() -> Decimal:
    """Получает сумму USD во всех позициях.
    
    Returns:
        Сумма USD в позициях или 0
    """
    async with async_session() as session:
        query = select(func.sum(Position.invested_usd))
        result = await session.execute(query)
        usd_in_positions = result.scalar_one_or_none()
        return usd_in_positions or Decimal(0.00)


async def get_tokens_usd() -> Decimal:
    """Получает сумму USD во всех токенах.
    
    Returns:
        Сумма USD в токенах или 0
    """
    async with async_session() as session:
        query = select(func.sum(Token.balance_usd))
        result = await session.execute(query)
        usd_in_tokens = result.scalar_one_or_none()
        return usd_in_tokens or Decimal(0.00)


async def get_position_info(position_id: int = None, name: str = None,
                         field: str = None) -> Optional[Union[Token, Any]]:
    """Получает информацию о позиции.
    
    Args:
        position_id: ID позиции
        name: Название позиции
        field: Поле позиции для получения
        
    Returns:
        Позиция, поле позиции или None
    """
    if not (position_id or name):
        return None
    async with async_session() as session:
        if field:
            query = select(getattr(Position, field))
        else:
            query = select(Position).options(selectinload(Position.token))
        if name:
            query = query.where(Position.name == name)
        elif position_id:
            query = query.where(Position.id == position_id)
        position = await session.execute(query)
        return position.scalar_one_or_none()


async def update_tokens_prices(prices: dict[str, Decimal]) -> None:
    """Обновление цен токенов в БД и пересчет суммы позиции.
    
    Args:
        prices: Словарь с ценами токенов {symbol: price}
    """
    if not prices:
        return
        
    async with async_session() as session:
        async with session.begin():
            # Получаем все токены за один запрос
            symbols = list(prices.keys())
            query = (select(Token)
                    .options(selectinload(Token.position))
                    .where(Token.symbol.in_(symbols)))
            result = await session.execute(query)
            tokens = result.scalars().all()
            
            # Обновляем цены токенов
            for token in tokens:
                price = prices.get(token.symbol)
                if price:
                    token.current_coinprice_usd = price
                    if token.position:
                        token.position.total_usd = token.position.amount * price
