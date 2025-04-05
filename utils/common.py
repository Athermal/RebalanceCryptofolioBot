from decimal import Decimal


symbols_list = []

bodyfix_notified_tokens: set[str] = set()

# Словарь для отслеживания последних цен уведомлений о просадке {symbol: last_notification_price}
drawdown_last_prices: dict[str, Decimal] = {}
