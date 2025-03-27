from aiogram.fsm.state import StatesGroup, State

class DepositState(StatesGroup):
    amount_usd = State()

class StrategyLiquidity(StatesGroup):
    direction_name = 'Ликвидность'
    percentage = State()

class StrategyWorkingCapital(StatesGroup):
    direction_name = 'Рабочий капитал'
    percentage = State()

class Sector(StatesGroup):
    sector_id = State()
    name = State()
    percentage = State()
    new_percentage = State()

class Token(StatesGroup):
    token_id = State()
    sector_id = State()
    symbol = State()
    percentage = State()
    new_percentage = State()
    balance_usd = State()

class Order(StatesGroup):
    buy_token_symbol = State()
    buy_token_id = State()
    buy_amount = State()
    buy_entry_price = State()

    sell_token_symbol = State()
    sell_token_id = State()
    sell_amount = State()

