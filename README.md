# RebalanceCryptofolioBot 📊

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/PostgreSQL-15%2B-blue" alt="PostgreSQL 15+">
  <img src="https://img.shields.io/badge/aiogram-3.19.0-green" alt="aiogram 3.19.0">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0.39-orange" alt="SQLAlchemy 2.0.39">
</div>

Telegram-бот для ребалансировки криптовалютного портфеля с автоматическим отслеживанием цен токенов на бирже Bybit.

## ✨ Функциональность

- 📈 **Умное распределение и структурирование портфеля**: Распределение депозита между ликвидностью и рабочим капиталом, с последующим распределением рабочего капитала между секторами и токенами внутри секторов. Распределение происходит автоматически по заданным вами процентным соотношениям.
- 🛡️ **Минимизация рисков**: Вход в токен происходит в 10 ордеров для снижения влияния волатильности и защиты капитала.
- 💰 **Управление депозитами**: Отслеживание распределения инвестированного баланса.
- 🔄 **Актуальные цены**: Автоматическое обновление через API Bybit.
- 🔔 **Уведомления**: Оповещения о достижении цены фиксации тела инвестиций (х2), о просадках токена для своевременного докупа.
- 📋 **Учет позиций**: Ведение учета открытых позиций.
- 🌟 **Предустановленные токены**: Автоматическое добавление популярных токенов с Bybit (с рыночной капитализацией от $100M на момент релиза) и консервативное распределение процентов при первом запуске. Функцию можно отключить в файле connection.py.


## 🚀 Установка и настройка

### Требования

- Python 3.10+
- PostgreSQL 15+

### Шаги установки

1. **Установка PostgreSQL**
   - Скачайте установщик с [официального сайта](https://www.postgresql.org/download/)
   - Запустите установщик и следуйте инструкциям
   - Запомните пароль для пользователя postgres

2. **Клонирование репозитория**
   ```bash
   git clone https://github.com/Athermal/RebalanceCryptofolioBot/releases/latest
   cd RebalanceCryptofolioBot
   ```

3. **Настройка окружения**
   ```bash
   # Создание виртуального окружения
   python -m venv venv
   
   # Активация виртуального окружения
   # Для Windows:
   venv\Scripts\activate
   # Для Linux/Mac:
   source venv/bin/activate
   
   # Установка зависимостей
   pip install -r requirements.txt
   ```

4. **Настройка переменных окружения**
   ```bash
   cp .env.example .env
   ```
   
   Отредактируйте файл `.env`, указав:
   - Токен бота (получите у @BotFather в Telegram)
   - Ваш Telegram ID (можно узнать у @userinfobot)
   - Данные для подключения к PostgreSQL
   - Процент просадки токена для уведомлений по просадкам

