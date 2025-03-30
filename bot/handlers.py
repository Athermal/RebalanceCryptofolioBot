from decimal import ROUND_DOWN, Decimal, InvalidOperation
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
import bot.keyboards as kb
import database.requests as rq
import bot.states as st

router = Router()

def format_number(value: Decimal) -> Decimal:
    value_str = format(value, 'f')
    if '.' in value_str:
        int_part, frac_part = value_str.split('.', 1)
        frac_part = frac_part.rstrip('0')
        if frac_part:
            formatted_str = f'{int_part}.{frac_part}'
        else:
            formatted_str = int_part
    else:
        formatted_str = value_str
    return Decimal(formatted_str)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    text = (f'Привет, <b>{message.from_user.first_name}</b> ! 👋\n\n'
            f'Канал с обновлениями бота: @Athermal \n\n'
            f'🐥 <b>Выберите пункт меню:</b>')
    await message.answer(text, reply_markup=kb.main)


@router.callback_query(F.data == 'start')
async def step_back_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (f'Привет, <b>{callback.from_user.first_name}</b> ! 👋\n\n'
            f'Канал с обновлениями бота: @Athermal \n\n'
            f'🐥 <b>Выберите пункт меню:</b>')
    await callback.message.edit_text(text, reply_markup=kb.main)


@router.callback_query(F.data == 'portfolio')
async def portfolio(callback: CallbackQuery):
    all_sum_usd = await rq.get_all_usd_info()
    usd_in_positions = await rq.get_positions_usd_info()
    usd_in_liquidity = await rq.get_direction_or_info(
        direction_name='Ликвидность',
        field='balance_usd')
    usd_in_tokens = await rq.get_tokens_usd()
    text = (f'<b>Текущая статистика вашего портфеля</b>\n\n'
            f'💰 <b>Общая сумма инвестиций:</b> {all_sum_usd}$\n\n'
            f'📊 <b>Из них:</b>\n'
            f'  • 💵 <b>В ликвидности:</b> {usd_in_liquidity}$\n'
            f'  • 📈 <b>В позициях:</b> {usd_in_positions}$\n'
            f'  • 🪙 <b>На покупку токенов есть:</b> {usd_in_tokens}$\n')
    await callback.message.edit_text(text, reply_markup=kb.portfolio)


@router.callback_query(F.data == 'deposit')
async def deposit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(st.Deposit.amount_usd)
    text = '💵 Введите <b>сумму в $</b>, на которую нужно пополнить <b>портфель</b>:'
    await callback.message.edit_text(text)

@router.message(st.Deposit.amount_usd)
async def deposit_first(message: Message, state: FSMContext):
    try:
        raw_input = Decimal(message.text.replace('$', '').strip())
        if raw_input <= 0:
            text = '❌ <b>Ошибка!</b>\n\nСумма должна быть больше нуля!'
            await message.answer(text)
        else:
            formatted_raw = format_number(raw_input).quantize(
                Decimal('0.01'), rounding=ROUND_DOWN
            )
            await state.update_data(amount_usd=formatted_raw)
        data = await state.get_data()
        await rq.add_deposit(amount_usd=data['amount_usd'
        ''])
        text = f'✅ Депозит на <b>{data['amount_usd']}$</b> добавлен в <b>портфель</b>!'
        await message.answer(text,
                             reply_markup=kb.deposit)
        await state.clear()
    except InvalidOperation:
        text = '❌ <b>Ошибка!</b>\n\nВведите <b>корректное число</b> в долларах!'
        await message.answer(text)
    except ValueError as e:
        await state.clear()
        await message.answer(f'{e}', reply_markup=kb.deposit)

@router.callback_query(F.data == 'strategy')
async def strategy(callback: CallbackQuery):
    text = '📊 <b>Выберите пункт для распределения капитала по %:</b>'
    await callback.message.edit_text(text,
                                     reply_markup=kb.strategy)


@router.callback_query(F.data == 'strategy_portfolio')
async def strategy_portfolio(callback: CallbackQuery):
    liquidity_percentage = await rq.get_direction_or_info(
        direction_name=st.StrategyLiquidity.direction_name,
        field='percentage') or 0
    wcapital_percentage = await rq.get_direction_or_info(
        direction_name=st.StrategyWorkingCapital.direction_name,
        field='percentage') or 0
    text = (f'<b>📊 Портфель</b>\n\n'
            f'<b>Текущее распределение:</b>\n'
            f'🔹{st.StrategyLiquidity.direction_name} - {liquidity_percentage}%\n'
            f'🔹{st.StrategyWorkingCapital.direction_name} - {wcapital_percentage}%\n\n'
            f'<b>Выберите пункт для изменения распределения портфеля в %:</b>')
    await callback.message.edit_text(text, reply_markup=kb.strategy_portfolio)


@router.callback_query(F.data == 'strategy_liquidity')
async def strategy_liquidity(callback: CallbackQuery, state: FSMContext):
    await state.set_state(st.StrategyLiquidity.percentage)
    text = ('📊 Введите <b>%</b>, который хотите выделить на <b>Ликвидность</b>.\n\n'
            '<i>Используется для откупа существующих позиций на просадках.</i>')
    await callback.message.edit_text(text)


@router.message(st.StrategyLiquidity.percentage)
async def strategy_liquidity_first(message: Message, state: FSMContext):
    try:
        raw_input = Decimal(message.text.replace('%', '').strip())
        if raw_input == 100:
            text = ('❌ <b>Ошибка!</b>\n\n'
                    'Ликвидность <u>не может быть равна 100%</u>, тебе еще позиции набирать! 😉')
            await message.answer(text)
            return
        elif raw_input > 100:
            text = '⚠️ <b>Ошибка!</b>\n\nЛиквидность <u>не может быть более 100%</u>.'
            await message.answer(text)
            return
        else:
                await state.update_data(percentage=format_number(raw_input))

        data = await state.get_data()
        await rq.change_percentage_portfolio_direction(
            direction_name=st.StrategyLiquidity.direction_name,
            percentage=data['percentage'])
        text = (f'✅ <b>Готово!</b>\n\n'
                f'<b>Ликвидность</b> теперь составляет <b>{data['percentage']}% от портфеля.</b>')
        await message.answer(text, reply_markup=kb.strategy_portfolio_back)
        await state.clear()
    except ValueError as e:
        await state.clear()
        await message.answer(f'{e}', reply_markup=kb.strategy_portfolio_back)
    except InvalidOperation:
        text = ('❌ <b>Ошибка!</b>\n\nВведите корректное число.\n\n'
                '<b>Пример:</b> <code>30%</code> или <code>30.53%</code>')
        await message.answer(text)


@router.callback_query(F.data == 'strategy_wcapital')
async def strategy_wcapital(callback: CallbackQuery, state: FSMContext):
    await state.set_state(st.StrategyWorkingCapital.percentage)
    text = ('📊 <b>Введите %</b>, который хотите выделить на <b>Рабочий Капитал</b>.\n\n'
            '<i>Используется для набора и закупа позиций.</i>')
    await callback.message.edit_text(text)


@router.message(st.StrategyWorkingCapital.percentage)
async def strategy_wcapital_first(message: Message, state: FSMContext):
    try:
        raw_input = Decimal(message.text.replace('%', '').strip())
        if raw_input == 100:
            text = ('❌ <b>Ошибка!</b>\n\nРабочий Капитал <u>не может быть равен 100%</u>, '
                    'тебе еще просадки откупать! 😉')
            await message.answer(text)
            return
        elif raw_input > 100:
            text = '⚠️ <b>Ошибка!</b>\n\nРабочий Капитал <u>не может быть более 100%</u>.'
            await message.answer(text)
            return
        else:
            await state.update_data(percentage=format_number(raw_input))

        data = await state.get_data()
        await rq.change_percentage_portfolio_direction(
            direction_name=st.StrategyWorkingCapital.direction_name,
            percentage=data['percentage'])
        text = (f'✅ <b>Готово!</b>\n\n'
                f'<b>Рабочий Капитал</b> теперь составляет '
                f'<b>{data['percentage']}% от портфеля.</b>')
        await message.answer(text, reply_markup=kb.strategy_portfolio_back)
        await state.clear()
    except ValueError as e:
        await state.clear()
        await message.answer(f'{e}', reply_markup=kb.strategy_portfolio_back)
    except InvalidOperation:
        await message.answer('❌ <b>Ошибка!</b>\n\nВведите корректное число.\n\n'
                             '<b>Пример:</b> <code>70%</code> или <code>70.53%</code>')


@router.callback_query(F.data == 'strategy_sectors')
async def strategy_sectors(callback: CallbackQuery):
    sectors = await rq.get_all_sectors()
    sector_text=''
    if sectors:
        for sector in sectors:
            sector_text += f'🔹 {sector.name} - {sector.percentage}%\n'
    text = (f'<b>📊 Секторы</b>\n\n'
            f'<b>Текущее распределение по секторам:</b>\n'
            f'{sector_text}\n'
            f'<b>Выберите сектор для изменения распределения в %:</b>')
    await callback.message.edit_text(text, reply_markup=await kb.strategy_sectors())


@router.callback_query(F.data == 'add_sector')
async def add_sector(callback: CallbackQuery, state: FSMContext):
    await state.set_state(st.Sector.name)
    await callback.message.edit_text('🗳 <b>Укажите название для нового сектора</b>')


@router.message(st.Sector.name)
async def add_sector_first(message: Message, state: FSMContext):
    await state.update_data(sector=message.text)
    data = await state.get_data()
    await state.set_state(st.Sector.percentage)
    text = f'📊 <b>Введите %</b>, который хотите выделить на сектор <b>{data['sector']}</b>.'
    await message.answer(text)


@router.message(st.Sector.percentage)
async def add_sector_second(message: Message, state: FSMContext):
    try:
        raw_input = Decimal(message.text.replace('%', '').strip())
        if raw_input > 100:
            await message.answer('⚠️ <b>Ошибка!</b>\n\nСектор <u>не может быть более 100%</u>.')
            return
        else:
            await state.update_data(percentage=format_number(raw_input))

        data = await state.get_data()
        await rq.add_sector(sector_name=data['sector'], percentage=data['percentage'])
        text = (f'✅ <b>Готово!</b>\n\n'
                f'Сектор <b>{data['sector']}</b> теперь составляет <b>{data['percentage']}%'
                f' от Рабочего Капитала.</b>')
        await message.answer(text, reply_markup=kb.strategy_sectors_back)
        await state.clear()
    except ValueError as e:
        await state.clear()
        await message.answer(f'{e}', reply_markup=kb.strategy_sectors_back)
    except InvalidOperation:
        await message.answer('❌ <b>Ошибка!</b>\n\nВведите корректное число.\n\n'
                             '<b>Пример:</b> <code>70%</code> или <code>70.53%</code>')


@router.callback_query(F.data.startswith('sector_page_'))
async def sector_page(callback: CallbackQuery):
    page = int(callback.data.split('_')[2])
    sectors = await rq.get_all_sectors()
    sector_text = ''
    if sectors:
        for sector in sectors:
            sector_text += f'🔹 {sector.name} - {sector.percentage}%\n'
    text = (f'<b>📊 Секторы</b>\n\n'
            f'<b>Текущее распределение по секторам:</b>\n'
            f'{sector_text}\n'
            f'<b>Выберите сектор для изменения распределения в %:</b>')
    await callback.message.edit_text(
        text,
        reply_markup=await kb.strategy_sectors(page=page))


@router.callback_query(F.data.startswith('sector_button_'))
async def sector_button(callback: CallbackQuery):
    sector_id = int(callback.data.split('_')[2])
    sector = await rq.get_sector_info(sector_id=sector_id)
    tokens = await rq.get_all_sector_tokens(sector_id=sector_id)
    token_text = ''
    if tokens:
        for token in tokens:
            token_text += f'🔹 {token.symbol} - {token.percentage}%\n'
    text = (f'<b>📊 Сектор "{sector.name}"</b>\n\n'
            f'<b>Текущее распределение по токенам:</b>\n'
            f'{token_text}'
            f'\n\nВыделено от Рабочего Капитала: <b>{sector.percentage}%</b>')
    await callback.message.edit_text(
        text,
        reply_markup=await kb.in_sector(sector_id))


@router.callback_query(F.data.startswith('sector_delete_button_'))
async def sector_delete_first(callback: CallbackQuery):
    sector_id = int(callback.data.split('_')[3])
    sector = await rq.get_sector_info(sector_id=sector_id)
    text = f'<b>Уверены, что хотите удалить сектор {sector.name}?</b>'
    await callback.message.edit_text(text, reply_markup=await kb.sector_delete_confirm(sector_id))


@router.callback_query(F.data.startswith('sector_delete_confirm_'))
async def sector_delete_second(callback: CallbackQuery):
    sector_id = int(callback.data.split('_')[3])
    sector = await rq.get_sector_info(sector_id=sector_id)
    sector_name = sector.name
    await rq.delete_sector(sector=sector)
    await callback.message.edit_text(f'✅ <b>Готово!</b>\n\n'
                                     f'Сектор <b>{sector_name}</b> был успешно удален.',
                                     reply_markup=kb.strategy_sectors_back)


@router.callback_query(F.data.startswith('sector_change_percentage_'))
async def sector_change_percentage(callback: CallbackQuery, state: FSMContext):
    sector_id = int(callback.data.split('_')[3])
    await state.set_state(st.Sector.new_percentage)
    sector = await rq.get_sector_info(sector_id=sector_id)
    await state.update_data(sector_id=sector_id, name=sector.name)
    text = (f'📊 <b>Введите новый %</b>, который хотите выделить на сектор '
            f'<b>{sector.name}</b>.')
    await callback.message.edit_text(text)


@router.message(st.Sector.new_percentage)
async def sector_change_percentage_second(message: Message, state: FSMContext):
    try:
        raw_input = Decimal(message.text.replace('%', '').strip())
        if raw_input > 100:
            await message.answer('⚠️ <b>Ошибка!</b>\n\nСектор <u>не может быть более 100%</u>.')
            return
        else:
            await state.update_data(percentage=format_number(raw_input))

        data = await state.get_data()
        await rq.change_sector_percentage(sector_name=data['name'], percentage=data['percentage'])
        await message.answer(f'✅ <b>Готово!</b>\n\n'
                             f'Сектор <b>{data['name']}</b> теперь составляет '
                             f'<b>{data['percentage']}% от Рабочего Капитала.</b>',
                             reply_markup=await kb.sector_change(data['sector_id']))
        await state.clear()

    except ValueError as e:
        await state.clear()
        await message.answer(f'{e}', reply_markup=kb.strategy_sectors_back)
    except InvalidOperation:
        await message.answer('❌ <b>Ошибка!</b>\n\nВведите корректное число.\n\n'
                             '<b>Пример:</b> <code>70%</code> или <code>70.53%</code>')


@router.callback_query(F.data.startswith('strategy_tokens_'))
async def strategy_tokens(callback: CallbackQuery):
    sector_id = int(callback.data.split('_')[2])
    sector = await rq.get_sector_info(sector_id=sector_id)
    tokens = await rq.get_all_sector_tokens(sector_id=sector_id)
    token_text = ''
    if tokens:
        for token in tokens:
            token_text += f'🔹 {token.symbol} - {token.percentage}%\n'

    text = (f'<b>📊 Токены сектора "{sector.name}"</b>\n\n'
            f'<b>Текущее распределение по токенам:</b>\n'
            f'{token_text}\n'
            f'<b>Выберите токен для изменения распределения в %:</b>')
    await callback.message.edit_text(
        text,
        reply_markup=await kb.strategy_tokens(sector_id=sector_id, page=0))


@router.callback_query(F.data.startswith('add_token_'))
async def add_token(callback: CallbackQuery, state: FSMContext):
    sector_id = int(callback.data.split('_')[2])
    await state.set_state(st.Token.sector_id)
    await state.update_data(sector_id=sector_id)
    await callback.message.edit_text(f'🗳 <b>Укажите название для нового токена</b>')


@router.message(st.Token.sector_id)
async def add_token_first(message: Message, state: FSMContext):
    await state.update_data(symbol=str(message.text))
    data = await state.get_data()
    sector = await rq.get_sector_info(sector_id=data['sector_id'])
    await state.set_state(st.Token.percentage)
    text = (f'📊 <b>Введите %</b>, который хотите выделить на токен '
            f'<b>{data['symbol']}</b> из сектора <b>{sector.name}</b>.')
    await message.answer(text)


@router.message(st.Token.percentage)
async def add_token_second(message: Message, state: FSMContext):
    try:
        raw_input = Decimal(message.text.replace('%', '').strip())
        if raw_input > 100:
            await message.answer('⚠️ <b>Ошибка!</b>\n\nТокен <u>не может быть более 100%</u>.')
            return
        else:
            await state.update_data(percentage=format_number(raw_input))

        data = await state.get_data()
        await rq.add_token(
            sector_id=data['sector_id'],
            symbol=data['symbol'],
            percentage=data['percentage']
            )
        sector = await rq.get_sector_info(sector_id=data['sector_id'])

        await message.answer(f'✅ <b>Готово!</b>\n\n'
                             f'Токен <b>{data['symbol']}</b> теперь составляет '
                             f'<b>{data['percentage']}%</b> от сектора <b>{sector.name}</b>',
                             reply_markup=await kb.strategy_tokens_back(data['sector_id']))
        await state.clear()
    except ValueError as e:
        data = await state.get_data()
        await state.clear()
        await message.answer(
            f'{e}', reply_markup=await kb.strategy_tokens_back(data['sector_id'])
        )
    except InvalidOperation:
        await message.answer('❌ <b>Ошибка!</b>\n\nВведите корректное число.\n\n'
                             '<b>Пример:</b> <code>70%</code> или <code>70.53%</code>')

@router.callback_query(F.data.startswith('token_page_'))
async def token_page(callback: CallbackQuery):
    sector_id = int(callback.data.split('_')[2])
    page = int(callback.data.split('_')[3])
    sector = await rq.get_sector_info(sector_id=sector_id)
    tokens = await rq.get_all_sector_tokens(sector_id=sector_id)
    token_text = ''
    if tokens:
        for token in tokens:
            token_text += f'🔹 {token.symbol} - {token.percentage}%\n'
    text = (f'<b>📊 Токены сектора "{sector.name}"</b>\n\n'
            f'<b>Текущее распределение по токенам:</b>\n'
            f'{token_text}\n'
            f'<b>Выберите токен для изменения распределения в %:</b>')
    await callback.message.edit_text(
        text,
        reply_markup=await kb.strategy_tokens(sector_id=sector_id, page=page))


@router.callback_query(F.data.startswith('token_button_'))
async def token_button(callback: CallbackQuery):
    token_id = int(callback.data.split('_')[2])
    token = await rq.get_token_or_info(token_id=token_id)
    if token:
        text = (
            f'<b>📊 Токен "{token.symbol}" из сектора "{token.sector.name}"</b>\n\n'
            f'<b>Выделено % от сектора:</b> {token.percentage}%\n\n'
            f'<b>Выделено на токен:</b> {token.balance_usd}$\n'
            f'<b>Выделено на новый ордер:</b> {token.balance_entry_usd}$\n\n'
            f'<b>Выберите действие с токеном:</b>'
        )
        await callback.message.edit_text(text,
                                         reply_markup=await kb.in_token(token_id))


@router.callback_query(F.data.startswith('token_change_percentage_'))
async def token_change_percentage_first(callback: CallbackQuery, state: FSMContext):
    token_id = int(callback.data.split('_')[3])
    await state.set_state(st.Token.new_percentage)
    token = await rq.get_token_or_info(token_id=token_id)
    if token:
        await state.update_data(symbol=token.symbol)
        await state.update_data(token_id=token_id, sector_id=token.sector_id)
        text = (f'📊 <b>Введите %</b>, который хотите выделить на токен '
                f'<b>{token.symbol}</b> из сектора <b>{token.sector.name}</b>')
        await callback.message.edit_text(text)


@router.message(st.Token.new_percentage)
async def token_change_percentage_second(message: Message, state: FSMContext):
    try:
        raw_input = Decimal(message.text.replace('%', '').strip())
        if raw_input > 100:
            await message.answer('⚠️ <b>Ошибка!</b>\n\nТокен <u>не может быть более 100%</u>.')
            return
        else:
            await state.update_data(new_percentage=format_number(raw_input))
        data = await state.get_data()
        sector = await rq.get_sector_info(sector_id=data['sector_id'])
        await rq.change_token_percentage(token_id=data['token_id'], sector_id=data['sector_id'],
                                         percentage=data['new_percentage'])
        await message.answer(f'✅ <b>Готово!</b>\n\n'
                             f'Токен <b>{data['symbol']}</b> теперь составляет '
                             f'<b>{data['new_percentage']}%</b> от сектора <b>{sector.name}</b>',
                             reply_markup=await kb.strategy_tokens_back(data['sector_id']))
        await state.clear()
    except ValueError as e:
        data = await state.get_data()
        await state.clear()
        await message.answer(
            f'{e}',
            reply_markup=await kb.strategy_tokens_back(data['sector_id']))
    except InvalidOperation:
        text = ('❌ <b>Ошибка!</b>\n\nВведите корректное число приобретенных монет.\n\n'
                '<b>Пример:</b> <code>70%</code> или <code>70.53%</code>')
        await message.answer(text)


@router.callback_query(F.data.startswith('token_delete_button_'))
async def token_delete_first(callback: CallbackQuery):
    token_id = int(callback.data.split('_')[3])
    token = await rq.get_token_or_info(token_id=token_id)
    text = f'<b>Уверены, что хотите удалить сектор {token.symbol}?</b>'
    await callback.message.edit_text(text, reply_markup=await kb.token_delete_confirm(token_id))


@router.callback_query(F.data.startswith('token_delete_confirm_'))
async def token_delete_second(callback: CallbackQuery):
    token_id = int(callback.data.split('_')[3])
    token = await rq.get_token_or_info(token_id=token_id)
    if token:
        token_symbol = token.symbol
        await rq.delete_token(token=token)
        text = (f'✅ <b>Готово!</b>\n\n'
                f'Токен <b>{token_symbol}</b> был успешно удален.')
        await callback.message.edit_text(
            text,
            reply_markup=await kb.strategy_tokens_back(token.sector_id)
            )


@router.callback_query(F.data == 'positions')
async def positions(callback: CallbackQuery):
    await callback.message.edit_text(f'Выберите пункт меню:',
                                     reply_markup=await kb.positions(page=0))

@router.callback_query(F.data == 'back_positions')
async def back_positions(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await positions(callback)


@router.callback_query(F.data == 'add_order')
async def add_order(callback: CallbackQuery):
    await callback.message.edit_text('<b>Выберите тип ордера:</b>',
                                     reply_markup=kb.add_order)


@router.callback_query(F.data == 'buy_order')
async def buy_order(callback: CallbackQuery, state: FSMContext):
    await state.set_state(st.Order.buy_token_symbol)
    await callback.message.edit_text('✏️ <b>Введите название токена:</b>')


@router.message(st.Order.buy_token_symbol)
async def buy_order_first(message: Message, state: FSMContext):
    token_symbol = str(message.text)
    token = await rq.get_token_or_info(symbol=token_symbol)
    if token:
        await state.update_data(buy_token_symbol=token_symbol, buy_token_id=token.id)
        token_balance_entry_usd = token.balance_entry_usd
        liquidity_balance = await rq.get_direction_or_info(
            direction_name="Ликвидность", field="balance_usd"
        ) * Decimal("0.02")

        if token.position and token_balance_entry_usd < Decimal("5"):
            total_usd = token_balance_entry_usd + liquidity_balance
            text = (
                f'⚖️ <b>Для покупки токена "{token_symbol}" доступно:\n\n'
                f"Из баланса токена:</b> {format_number(token_balance_entry_usd)}$\n"
                f"<b>Из ликвидности:</b> {format_number(liquidity_balance)}$\n\n"
                f"📊 <b>Суммарно доступен вход до:</b> {format_number(total_usd)}$\n\n"
                f"❓<i>Приобретите токены в пределах <b>этой суммы</b> и выведите их на кошелек."
                f"</i>\n\n"
                f"<b>Введите итоговое кол-во токенов на кошельке:</b>"
            )
        else:
            text = (
                f'⚖️ <b>Для покупки токена "{token_symbol}" доступно:</b>\n\n'
                f"Из баланса токена:<b> {format_number(token_balance_entry_usd)}$</b>\n\n"
                f"❓ <i>Приобретите токены <b>на эту сумму</b> и выведите их на кошелек.</i>\n\n"
                f"<b>Введите итоговое кол-во токенов на кошельке:</b>"
            )

        await message.answer(text)
        await state.set_state(st.Order.buy_amount)
    else:
        text = ('❌ <b>Ошибка! Токен не найден.</b>\n\n'
                'Убедитесь, что токен существует и добавлен в сектор.')
        await message.answer(text,
                             reply_markup=kb.order_error_with_token)
        await state.clear()
        return


@router.message(st.Order.buy_amount)
async def buy_order_second(message: Message, state: FSMContext):
    try:
        buy_amount = Decimal(message.text)
        await state.update_data(buy_amount=buy_amount)
        await state.set_state(st.Order.buy_entry_price)
        text = '💰<b>Введите стоимость одного купленного токена:</b>'
        await message.answer(text)
    except InvalidOperation:
        text = ('❌ <b>Ошибка!</b>\n\nВведите корректное число или отмените создание ордера.\n\n'
                '<b>Пример ввода:</b> <code>70112</code> или <code>70112.151423424</code>\n\n')
        await message.answer(text,
                             reply_markup=kb.order_cancel)


@router.message(st.Order.buy_entry_price)
async def buy_order_third(message: Message, state: FSMContext):
    try:
        buy_entry_price = Decimal(message.text)
        await state.update_data(buy_entry_price=buy_entry_price)
        data = await state.get_data()
        await rq.buy_order(token_id=data['buy_token_id'], amount=data['buy_amount'],
                           entry_price=data['buy_entry_price'])
        await state.clear()
        text = '✅ <b>Готово!</b>\n\nОрдер был успешно сохранен.'
        await message.answer(text,
                             reply_markup=kb.order_back)
    except InvalidOperation:
        text = ('❌ <b>Ошибка!</b>\n\nВведите корректное число или отмените создание ордера.\n\n'
                '<b>Пример ввода:</b> <code>70112</code> или <code>70112.151423424</code>\n\n')
        await message.answer(text,
                             reply_markup=kb.order_cancel)
    except ValueError as e:
        await state.clear()
        await message.answer(f'{e}', reply_markup=kb.order_back)


@router.callback_query(F.data == 'sell_order')
async def sell_order(callback: CallbackQuery, state: FSMContext):
    await state.set_state(st.Order.sell_token_symbol)
    text = '✏️ <b>Введите название токена:</b>'
    await callback.message.edit_text(text)


@router.message(st.Order.sell_token_symbol)
async def sell_order_first(message: Message, state: FSMContext):
    token_symbol = str(message.text)
    token = await rq.get_token_or_info(symbol=token_symbol)
    if not token:
        text = ('❌ <b>Ошибка! Токен не найден.</b>\n\n'
                'Убедитесь, что токен существует и добавлен в сектор.')
        await message.answer(text,
            reply_markup=kb.order_error_with_token)
        await state.clear()
        return
    await state.update_data(sell_token_symbol=token_symbol, sell_token_id=token.id)
    if not token.position:
        text = '❌ <b>Ошибка!</b>\n\nУ вас нет позиций по этому токену.'
        await message.answer(
            text,
            reply_markup=kb.order_back)
        await state.clear()
        return
    text = (f'⚖️Для продажи доступно: <b>{token.position.amount} {token_symbol}</b>\n\n'
            f'Введите кол-во токенов, которое будете продавать:')
    await message.answer(text)
    await state.set_state(st.Order.sell_amount)


@router.message(st.Order.sell_amount)
async def sell_order_second(message: Message, state: FSMContext):
    try:
        sell_amount = Decimal(message.text)
        await state.update_data(sell_amount=sell_amount)
        data = await state.get_data()
        await rq.sell_order(token_id=data['sell_token_id'], amount=data['sell_amount'])
        await state.clear()
        text = '✅ <b>Готово!</b>\n\nОрдер был успешно сохранен.'
        await message.answer(text,
                             reply_markup=kb.order_back)
    except InvalidOperation:
        text = ('❌ <b>Ошибка!</b>\n\nВведите корректное число или отмените создание ордера.\n\n'
                '<b>Пример ввода:</b> <code>70112</code> или <code>70112.151423424</code>\n\n')
        await message.answer(text,
                             reply_markup=kb.order_cancel)


@router.callback_query(F.data.startswith('position_button_'))
async def token_button(callback: CallbackQuery):
    position_id = int(callback.data.split('_')[2])
    position = await rq.get_position_info(position_id=position_id)
    if position:
        text = (
            f'<b>📊 Позиция по токену "{position.name}"</b>\n\n'
            f'💰 <b>Общая сумма инвестиций:</b> {format_number(position.invested_usd)}$\n\n'
            f'<b>Количество токенов:</b> {format_number(position.amount)}\n\n'
            f'<b>Текущая цена токена:</b> {position.token.current_coinprice_usd or 0}$\n\n'
            f'<b>Цена входа:</b> {format_number(position.entry_price)}$\n'
            f'<b>Цена фиксации тела (х2):</b> {format_number(position.bodyfix_price_usd)}$\n\n'
            f'📈 <b>Текущая стоимость позиции:</b> {format_number(position.total_usd)}$'
        )
        await callback.message.edit_text(text, reply_markup=await kb.in_position(position_id))


@router.callback_query(F.data.startswith('position_buy_order_'))
async def position_buy_order(callback: CallbackQuery, state: FSMContext):
    position_id = int(callback.data.split('_')[3])
    position = await rq.get_position_info(position_id=position_id)
    token_symbol = position.token.symbol
    token_id = position.token_id
    await state.update_data(buy_token_symbol=token_symbol, buy_token_id=token_id)
    await state.set_state(st.Order.buy_amount)
    token_balance_entry_usd = position.token.balance_entry_usd
    liquidity_balance = await rq.get_direction_or_info(
        direction_name="Ликвидность", field="balance_usd"
    ) * Decimal("0.02")
    
    if token_balance_entry_usd < Decimal("5"):
        total_usd = token_balance_entry_usd + liquidity_balance
        text = (
            f'⚖️ <b>Для покупки токена "{token_symbol}" доступно:\n\n'
            f"Из баланса токена:</b> {format_number(token_balance_entry_usd)}$\n"
            f"<b>Из ликвидности:</b> {format_number(liquidity_balance)}$\n\n"
            f"📊 <b>Суммарно доступен вход до:</b> {format_number(total_usd)}$\n\n"
            f"❓<i>Приобретите токены в пределах <b>этой суммы</b> и выведите их на кошелек."
            f"</i>\n\n"
            f"<b>Введите итоговое кол-во токенов на кошельке:</b>"
        )
    else:
        text = (
            f'⚖️ <b>Для покупки токена "{token_symbol}" доступно:</b>\n\n'
            f"Из баланса токена:<b> {format_number(token_balance_entry_usd)}$</b>\n\n"
            f"❓ <i>Приобретите токены <b>на эту сумму</b> и выведите их на кошелек.</i>\n\n"
            f"<b>Введите итоговое кол-во токенов на кошельке:</b>"
        )
    await callback.message.edit_text(text)


@router.callback_query(F.data.startswith('position_sell_order_'))
async def position_sell_order(callback: CallbackQuery, state: FSMContext):
    position_id = int(callback.data.split('_')[3])
    position = await rq.get_position_info(position_id=position_id)
    token_symbol = position.token.symbol
    token_id = position.token_id
    await state.set_state(st.Order.sell_amount)
    await state.update_data(sell_token_symbol=token_symbol, sell_token_id=token_id)
    text = (
        f"⚖️Для продажи доступно: <b>{position.amount} {token_symbol}\n\n"
        f"Введите кол-во токенов, которое будете продавать:</b>"
    )
    await callback.message.edit_text(text)
