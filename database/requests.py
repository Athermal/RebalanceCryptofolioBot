from decimal import Decimal
from typing import Optional, Union, Any
from sqlalchemy.orm import selectinload
from database.connection import async_session
from database.models import Deposit, Direction, Sector, Token, Position, Order
from sqlalchemy import select, func, desc
from bot.states import StrategyLiquidity, StrategyWorkingCapital


async def add_deposit(amount_usd: Decimal) -> None:
    amount_usd = amount_usd.quantize(Decimal('0.01'))
    async with async_session() as session:
        async with session.begin(): # argument readonly doesn't work in asyncpg
            session.add(Deposit(amount_usd=amount_usd))
            query = select(Direction)
            result = await session.execute(query)
            portfolio_directions = result.scalars().all()

            if portfolio_directions:
                query = select(func.sum(Direction.percentage))
                result = await session.execute(query)
                total_percentage_directions = result.scalar_one_or_none() or Decimal(0)
                if total_percentage_directions != Decimal(100):
                    text = (f'❌ <b>Ошибка!</b>\n\nСуммарный % всех направлений в портфеле = '
                            f'<b>{total_percentage_directions}%</b>'
                            f', а для добавления депозита должен быть <b>ровно 100%!</b>')
                    raise ValueError(text)

            query = select(Sector).options(selectinload(Sector.tokens))
            result = await session.execute(query)
            sectors = result.scalars().all()

            if sectors:
                query = select(func.sum(Sector.percentage))
                result = await session.execute(query)
                total_percentage_sectors = result.scalar_one_or_none() or Decimal(0)
                if total_percentage_sectors != Decimal(100):
                    text = (f'❌ <b>Ошибка!</b>\n\nСуммарный % всех секторов = '
                            f'<b>{total_percentage_sectors}%</b>'
                            f', а для добавления депозита должен быть <b>ровно 100%!</b>')
                    raise ValueError(text)

            for sector in sectors:
                total_percentage_tokens = sum(token.percentage for token in sector.tokens)
                if total_percentage_tokens != Decimal(100):
                    text=(f'❌ <b>Ошибка!</b>\n\nСуммарный % токенов '
                          f'в секторе <b>{sector.name}</b> = '
                          f'<b>{total_percentage_tokens}%</b>, '
                          f'а должен быть <b>ровно 100%!</b>')
                    raise ValueError(text)
            for direction in portfolio_directions:
                direction_balance = amount_usd * (direction.percentage / Decimal(100))
                direction_balance = direction_balance.quantize(Decimal('0.01'))
                direction.balance_usd += direction_balance
                if direction.name == "Рабочий капитал":
                    total_sector_balance = Decimal('0')
                    for i, sector in enumerate(sectors[:-1]):
                        raw_sector_balance = direction_balance * (sector.percentage / Decimal(100))
                        sector_balance = raw_sector_balance.quantize(Decimal('0.01'))
                        sector.balance_usd += sector_balance
                        total_sector_balance += sector_balance
                        total_token_balance = Decimal('0')
                        for j, token in enumerate(sector.tokens[:-1]):
                            raw_token_balance = sector_balance * (token.percentage / Decimal(100))
                            token_balance = raw_token_balance.quantize(Decimal('0.01'))
                            token.balance_usd += token_balance
                            total_token_balance += token_balance
                        if sector.tokens:
                            last_token_balance = sector_balance - total_token_balance
                            sector.tokens[-1].balance_usd += last_token_balance
                        else:
                            raise ValueError('В секторе нет токенов')
                    if sectors:
                        last_sector_balance = direction_balance - total_sector_balance
                        sectors[-1].balance_usd += last_sector_balance
                        last_sector = sectors[-1]
                        total_last_token_balance = Decimal('0')
                        for j, token in enumerate(last_sector.tokens[:-1]):
                            raw_token_balance = last_sector_balance * (token.percentage / Decimal(100))
                            token_balance = raw_token_balance.quantize(Decimal('0.01'))
                            token.balance_usd += token_balance
                            total_last_token_balance += token_balance
                        if last_sector.tokens:
                            last_token_balance = last_sector_balance - total_last_token_balance
                            last_sector.tokens[-1].balance_usd += last_token_balance
                        else:
                            raise ValueError('В секторе нет токенов')
                    direction.balance_usd -= direction_balance

async def add_portfolio_directions() -> None:
    async with async_session() as session:
        async with session.begin():
            liquidity = Direction(name=StrategyLiquidity.direction_name,
                                  percentage=Decimal(60.00))
            working_capital = Direction(name=StrategyWorkingCapital.direction_name,
                                        percentage=Decimal(40.00))
            session.add_all([liquidity, working_capital])


async def change_percentage_portfolio_direction(direction_name: str, percentage: Decimal) -> None:
    percentage = percentage.quantize(Decimal('0.01'))
    async with async_session() as session:
        async with session.begin():
            query = select(func.sum(Direction.percentage)).where(Direction.name != direction_name)
            result = await session.execute(query)
            not_inclusive_percentage = result.scalar_one_or_none() or Decimal(0)
            if not_inclusive_percentage + percentage > Decimal(100):
                text = (f'❌ <b>Ошибка!</b>\n\n'
                        f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                        f'❗️ <b>Обнулите % другого направления и попробуйте снова</b>')
                raise ValueError(text)

            query = select(Direction).where(Direction.name == direction_name)
            result = await session.execute(query)
            existing_record = result.scalar_one_or_none()
            existing_record.percentage = percentage


async def get_portfolio_direction_info(direction_name: str, field: str) -> Optional[Direction]:
    async with async_session() as session:
        query = select(getattr(Direction, field)).where(Direction.name == direction_name)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def add_sector(sector_name: str, percentage: Decimal) -> None:
    percentage = percentage.quantize(Decimal('0.01'))
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
    async with async_session() as session:
        query = select(Sector).order_by(Sector.id)
        result = await session.execute(query)
        sectors = result.scalars().all()
        return sectors


async def get_sector_info(sector_id: int = None, sector_name: str = None,
                          field: str = None) -> Optional[Union[Sector, Any]]:
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
    if not (sector_id or sector_name):
        return None
    percentage = percentage.quantize(Decimal('0.01'))
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
                            f'Для установки новому сектору доступно: {residue}%\n\n'
                            f'❗️ <b>Удалите некоторые секторы, или измените их %</b>')
                    raise ValueError(text)
                else:
                    text = (f'❌ <b>Ошибка!</b>\n\n'
                            f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                            f'Для установки новому сектору доступно: {residue}%')
                    raise ValueError(text)
            sector.percentage = percentage


async def add_token(sector_id: int, symbol: str, percentage: Decimal) -> None:
    percentage = percentage.quantize(Decimal('0.01'))
    async with async_session() as session:
        async with session.begin():
            query = select(func.sum(Token.percentage)).where(Token.symbol != symbol,
                                                             Token.sector_id == sector_id)
            result = await session.execute(query)
            total_percentage = result.scalar_one_or_none() or Decimal(0)
            if total_percentage + percentage > Decimal(100):
                all_percentage = await session.execute(select(func.sum(Token.percentage)).where(
                    Token.sector_id == sector_id))
                all_percentage = all_percentage.result.scalar_one_or_none() or Decimal(0)
                residue = Decimal(100) - all_percentage
                if residue == Decimal(0):
                    text = (f'❌ <b>Ошибка!</b>\n\n'
                            f'Общая сумма процентов <u>не может превышать 100%</u>\n\n'
                            f'Для установки новому токену доступно: 0%\n\n'
                            f'❗️ <b>Удалите некоторые токены, или измените их %</b>')
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
    percentage = percentage.quantize(Decimal('0.01'))
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


async def get_token_info(token_id: int = None, symbol: str = None,
                         field: str = None) -> Optional[Union[Token, Any]]:
    if not (token_id or symbol):
        return None
    async with async_session() as session:
        if field:
            query = select(getattr(Token, field))
        else:
            query = select(Token).options(
                selectinload(Token.sector),
                selectinload(Token.position)
            )
        if symbol:
            query = query.where(Token.symbol == symbol)
        elif token_id:
            query = query.where(Token.id == token_id)
        token = await session.execute(query)
        return token.scalar_one_or_none()


async def delete_token(token_id: int = None, symbol: str = None, token: Token = None) -> None:
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
    amount = amount.quantize(Decimal('0.0000000001'))
    entry_price = entry_price.quantize(Decimal('0.0000000001'))
    async with async_session() as session:
        async with session.begin():
            query = select(Token).where(Token.id == token_id)
            result = await session.execute(query)
            token = result.scalar_one_or_none()

            invested_usd = amount * entry_price
            token_symbol = token.symbol
            token_balance_usd = token.balance_usd
            if invested_usd > token_balance_usd:
                text = (f'❌ <b>Ошибка! Ордер не был добавлен.</b>\n\n'
                        f'Вы превысили максимально возможную сумму для покупки!\n\n'
                        f'⚖️<b>Для покупки токена "{token_symbol}" '
                        f'доступно: {token.balance_usd}$</b>')
                raise ValueError(text)
            token.balance_usd -= invested_usd
            order = Order(token_id=token_id, amount=amount, entry_price=entry_price)
            session.add(order)
            await session.flush()
            order.name = f'{order.type} #{order.id} — {token.symbol}'

            query = select(Position).where(Position.token_id == token_id)
            position = await session.execute(query)
            position = position.scalar_one_or_none()
            if position:
                position.amount += amount
                position.invested_usd += amount * entry_price
                position.entry_price = position.invested_usd / position.amount
                position.bodyfix_price_usd = position.entry_price * Decimal(2)
            else:
                await add_position(token_id=token_id, amount=amount, entry_price=entry_price)


async def add_position(token_id: int, amount: Decimal, entry_price: Decimal) -> None:
    amount = amount.quantize(Decimal('0.0000000001'))
    entry_price = entry_price.quantize(Decimal('0.0000000001'))
    async with async_session() as session:
        async with session.begin():
            invested_usd = Decimal(amount * entry_price).quantize(Decimal('0.01'))
            bodyfix_price_usd = Decimal(entry_price * 2).quantize(Decimal('0.0000000001'))
            token = await get_token_info(token_id=token_id)
            position = Position(name=token.symbol, token_id=token_id,
                                amount=amount, entry_price=entry_price,
                                invested_usd=invested_usd, bodyfix_price_usd=bodyfix_price_usd)
            session.add(position)


async def sell_order(token_id: int, amount: Decimal) -> None:
    amount = amount.quantize(Decimal('0.0000000001'))
    async with async_session() as session:
        async with session.begin():
            query = select(Token).where(Token.id == token_id)
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


async def get_all_positions() -> Optional[list[Position]]:
    async with async_session() as session:
        query = select(Position).order_by(desc(Position.id))
        positions = await session.execute(query)
        positions = positions.scalars().all()
        return positions or None


async def get_all_usd_info() -> Optional[Decimal]:
    async with async_session() as session:
        query = select(Direction.balance_usd).where(Direction.name == 'Ликвидность')
        result = await session.execute(query)
        usd_in_liquidity = result.scalar_one_or_none()

        query = select(func.sum(Position.invested_usd))
        result = await session.execute(query)
        usd_in_positions = result.scalar_one_or_none()

        query = select(func.sum(Token.balance_usd))
        result = await session.execute(query)
        usd_in_tokens = result.scalar_one_or_none()

        all_usd_sum = ((usd_in_positions or Decimal(0)) + (usd_in_tokens or Decimal(0))
                       + (usd_in_liquidity or Decimal(0)))
        return all_usd_sum


async def get_positions_usd_info() -> Optional[Decimal]:
    async with async_session() as session:
        query = select(func.sum(Position.invested_usd))
        result = await session.execute(query)
        usd_in_positions = result.scalar_one_or_none()
        return usd_in_positions or Decimal(0)