from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database.requests as rq

main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Портфель', callback_data='portfolio')],
    [InlineKeyboardButton(text='Стратегия', callback_data='strategy')],
    [InlineKeyboardButton(text='Активные позиции', callback_data='positions')]
])

portfolio = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='➕ Добавить депозит', callback_data='deposit')],
    [InlineKeyboardButton(text='Назад', callback_data='start')]
])

deposit = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Назад', callback_data='start')]
])

strategy = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💼  Распределение портфеля',
                          callback_data='strategy_portfolio')],
    [InlineKeyboardButton(text='🗄 Распределение по секторам и токенам',
                          callback_data='strategy_sectors')],
    [InlineKeyboardButton(text='Назад', callback_data='start')]
])

strategy_portfolio = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Ликвидность', callback_data='strategy_liquidity')],
    [InlineKeyboardButton(text='Рабочий Капитал', callback_data='strategy_wcapital')],
    [InlineKeyboardButton(text='Назад', callback_data='strategy')]
])

strategy_portfolio_back = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Назад', callback_data='strategy_portfolio'),
     InlineKeyboardButton(text='В меню', callback_data='start')]
])

add_order = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Покупка', callback_data='buy_order'),
     InlineKeyboardButton(text='Продажа', callback_data='sell_order')],
    [InlineKeyboardButton(text='Назад', callback_data='back_positions')]
])

strategy_sectors_back = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Назад', callback_data='strategy_sectors'),
     InlineKeyboardButton(text='В меню', callback_data='start')]
])

order_error_with_token = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='В секторы', callback_data='strategy_sectors'),
     InlineKeyboardButton(text='В меню', callback_data='start')]
])

order_cancel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Отменить создание ордера', callback_data='back_positions')]
])

order_back = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Назад', callback_data='back_positions'),
     InlineKeyboardButton(text='В меню', callback_data='start')]
])

async def strategy_sectors(page: int = 0) -> InlineKeyboardMarkup:
    all_strategy_sectors = await rq.get_all_sectors()
    if all_strategy_sectors is None:
        all_strategy_sectors = []
    keyboard = InlineKeyboardBuilder()
    buttons_per_page = 4
    nav_buttons = []
    total_pages = (len(all_strategy_sectors) - 1) // buttons_per_page + 1
    start_index = page * buttons_per_page
    end_index = start_index + buttons_per_page
    sectors_on_page = all_strategy_sectors[start_index:end_index]
    if sectors_on_page:
        for sector in sectors_on_page:
            keyboard.row(InlineKeyboardButton(text=sector.name,
                                              callback_data=f'sector_button_{sector.id}'))
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text='⬅️',
                                                    callback_data=f'sector_page_{page - 1}'))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text='➡️',
                                                    callback_data=f'sector_page_{page + 1}'))
        if nav_buttons:
            keyboard.row(*nav_buttons)
    keyboard.row(
        InlineKeyboardButton(text='Добавить сектор', callback_data='add_sector'),
        InlineKeyboardButton(text='Назад', callback_data='strategy')
    )
    return keyboard.as_markup()


async def in_sector(sector_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Изменить % сектора',
                                      callback_data=f'sector_change_percentage_{sector_id}'),
                 InlineKeyboardButton(text='Управлять токенами',
                                      callback_data=f'strategy_tokens_{sector_id}'))
    keyboard.row(InlineKeyboardButton(text='Удалить сектор',
                                      callback_data=f'sector_delete_button_{sector_id}'))
    keyboard.row(InlineKeyboardButton(text='Назад', callback_data='strategy_sectors'))
    return keyboard.as_markup()


async def sector_delete_confirm(sector_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='✅ Уверен, удаляем сектор',
                                      callback_data=f'sector_delete_confirm_{sector_id}'))
    keyboard.add(InlineKeyboardButton(text='❌ Отмена',
                                      callback_data=f'sector_button_{sector_id}'))
    return keyboard.as_markup()


async def sector_change(sector_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data=f'sector_button_{sector_id}'))
    keyboard.add(InlineKeyboardButton(text='В меню', callback_data=f'start'))
    return keyboard.as_markup()


async def positions(page: int = 0) -> InlineKeyboardMarkup:
    all_positions = await rq.get_all_positions()
    if all_positions is None:
        all_positions = []
    keyboard = InlineKeyboardBuilder()
    buttons_per_page = 4
    nav_buttons = []
    total_pages = (len(all_positions) - 1) // buttons_per_page + 1
    start_index = page * buttons_per_page
    end_index = start_index + buttons_per_page
    positions_on_page = all_positions[start_index:end_index]
    if positions_on_page:
        for position in positions_on_page:
            keyboard.row(InlineKeyboardButton(text=position.name,
                                              callback_data=f'position_button_{position.id}'))
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text='⬅️',
                                                    callback_data=f'position_page_{page - 1}'))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text='➡️',
                                                    callback_data=f'position_page_{page + 1}'))
        if nav_buttons:
            keyboard.row(*nav_buttons)
    keyboard.row(InlineKeyboardButton(text='➕ Добавить ордер', callback_data='add_order'),
        InlineKeyboardButton(text='Назад', callback_data='start')
    )
    return keyboard.as_markup()


async def in_position(position_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(
            text="➕ Докупить токен", callback_data=f"position_buy_order_{position_id}"
        ),
        InlineKeyboardButton(
            text="➖ Продать токен", callback_data=f"position_sell_order_{position_id}"
        ),
    )
    keyboard.row(InlineKeyboardButton(text='Назад', callback_data='positions'),
                 InlineKeyboardButton(text='В меню', callback_data='start'))
    return keyboard.as_markup()


async def strategy_tokens(sector_id: int, page: int = 0) -> InlineKeyboardMarkup:
    all_strategy_tokens = await rq.get_all_sector_tokens(sector_id=sector_id)
    if all_strategy_tokens is None:
        all_strategy_tokens = []
    keyboard = InlineKeyboardBuilder()
    buttons_per_page = 4
    nav_buttons = []
    total_pages = (len(all_strategy_tokens) - 1) // buttons_per_page + 1
    start_index = page * buttons_per_page
    end_index = start_index + buttons_per_page
    tokens_on_page = all_strategy_tokens[start_index:end_index]
    for token in tokens_on_page:
        keyboard.row(InlineKeyboardButton(text=token.symbol,
                                          callback_data=f'token_button_{token.id}'))
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text='⬅️',
                                                callback_data=f'token_page_{sector_id}_{page - 1}'))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text='➡️',
                                                callback_data=f'token_page_{sector_id}_{page + 1}'))
    if nav_buttons:
        keyboard.row(*nav_buttons)
    keyboard.row(
        InlineKeyboardButton(text='Добавить токен', callback_data=f'add_token_{sector_id}'),
        InlineKeyboardButton(text='Назад', callback_data=f'sector_button_{sector_id}')
    )
    return keyboard.as_markup()


async def strategy_tokens_back(sector_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data=f'strategy_tokens_{sector_id}'),
     InlineKeyboardButton(text='В меню', callback_data='start'))
    return keyboard.as_markup()


async def in_token(token_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Изменить %',
                                      callback_data=f'token_change_percentage_{token_id}'),
                 InlineKeyboardButton(text='Удалить токен',
                                      callback_data=f'token_delete_button_{token_id}'))
    keyboard.row(InlineKeyboardButton(text='Назад', callback_data='strategy_sectors'))
    return keyboard.as_markup()

async def token_delete_confirm(token_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='✅ Уверен, удаляем  токен',
                                      callback_data=f'token_delete_confirm_{token_id}'))
    keyboard.add(InlineKeyboardButton(text='❌ Отмена', callback_data=f'token_button_{token_id}'))
    return keyboard.as_markup()

async def to_position_button(position_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру с одной кнопкой для перехода к позиции"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text='Открыть позицию', 
                                     callback_data=f'position_button_{position_id}'))
    return keyboard.as_markup()
