import os
from dotenv import load_dotenv
from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

from database.models import Base
import database.requests as rq

load_dotenv()
engine_pg = create_async_engine(url=os.getenv('POSTGRESQL_URL'))

engine = create_async_engine(url=os.getenv('DB_URL'))
async_session = async_sessionmaker(engine)

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def create_default_columns():
    await rq.add_portfolio_directions()
    sectors_data = [
        ('Layer 1', Decimal(32)),
        ('Layer 2', Decimal(20)),
        ('DeFi', Decimal(15)),
        ('AI', Decimal(10)),
        ('Oracle', Decimal(10)),
        ('GameFi', Decimal(5)),
        ('Memes', Decimal(5)),
        ('NFT', Decimal(3))
    ]
    for sector_name, percentage in sectors_data:
        await rq.add_sector(sector_name=sector_name, percentage=percentage)

    tokens_data = [
        (1, "BTC", Decimal(30)),
        (1, "ETH", Decimal(17)),
        (1, "BNB", Decimal(8)),
        (1, "SOL", Decimal(5)),
        (1, "XRP", Decimal(4)),
        (1, "TON", Decimal(3)),
        (1, "ADA", Decimal(3)),
        (1, "TRX", Decimal(2)),
        (1, "AVAX", Decimal(2)),
        (1, "DOT", Decimal(2)),
        (1, "XLM", Decimal(1)),
        (1, "HBAR", Decimal(1)),
        (1, "LTC", Decimal(1)),
        (1, "SUI", Decimal(1)),
        (1, "NEAR", Decimal(1)),
        (1, "ATOM", Decimal(1)),
        (1, "ICP", Decimal(1)),
        (1, "ETC", Decimal(1)),
        (1, "BCH", Decimal(1)),
        (1, "ALGO", Decimal(1)),
        (1, "SEI", Decimal(1)),
        (1, "XTZ", Decimal(1)),
        (1, "EGLD", Decimal(1)),
        (1, "APT", Decimal(1)),
        (1, "FIL", Decimal(1)),
        (1, "CSPR", Decimal(1)),
        (1, "KDA", Decimal(1)),
        (1, "TIA", Decimal(1)),
        (1, "KAVA", Decimal(1)),
        (1, "ZETA", Decimal(1)),
        (1, "KAS", Decimal(1)),
        (1, "XEC", Decimal(1)),
        (1, "BERA", Decimal(1)),
        (1, "IP", Decimal(1)),
        (2, "ARB", Decimal(17)),
        (2, "OP", Decimal(16)),
        (2, "STRK", Decimal(13)),
        (2, "IMX", Decimal(13)),
        (2, "MNT", Decimal(8)),
        (2, "STX", Decimal(8)),
        (2, "POL", Decimal(5)),
        (2, "ZK", Decimal(5)),
        (2, "AEVO", Decimal(4)),
        (2, "MOVE", Decimal(4)),
        (2, "LRC", Decimal(3)),
        (2, "INJ", Decimal(3)),
        (2, "ALT", Decimal(1)),
        (3, "AAVE", Decimal(10)),
        (3, "UNI", Decimal(8)),
        (3, "LDO", Decimal(7)),
        (3, "DYDX", Decimal(6)),
        (3, "MKR", Decimal(5)),
        (3, "GMX", Decimal(5)),
        (3, "RPL", Decimal(5)),
        (3, "COMP", Decimal(5)),
        (3, "CRV", Decimal(4)),
        (3, "SUSHI", Decimal(4)),
        (3, "FXS", Decimal(4)),
        (3, "SNX", Decimal(3)),
        (3, "1INCH", Decimal(3)),
        (3, "YFI", Decimal(3)),
        (3, "UMA", Decimal(3)),
        (3, "AERO", Decimal(2)),
        (3, "JUP", Decimal(2)),
        (3, "ONDO", Decimal(2)),
        (3, "PENDLE", Decimal(2)),
        (3, "ENA", Decimal(2)),
        (3, "LAYER", Decimal(2)),
        (3, "STG", Decimal(2)),
        (3, "WOO", Decimal(2)),
        (3, "ZRX", Decimal(1)),
        (3, "DRIFT", Decimal(1)),
        (3, "FIDA", Decimal(1)),
        (3, "CPOOL", Decimal(1)),
        (3, "SPELL", Decimal(1)),
        (3, "OM", Decimal(1)),
        (3, "MORPHO", Decimal(1)),
        (3, "RUNE", Decimal(1)),
        (3, "ETHFI", Decimal(1)),
        (4, "FET", Decimal(25)),
        (4, "RENDER", Decimal(25)),
        (4, "GRT", Decimal(32)),
        (4, "GRASS", Decimal(9)),
        (4, "VIRTUAL", Decimal(9)),
        (5, "LINK", Decimal(43)),
        (5, "PYTH", Decimal(27)),
        (5, "FLR", Decimal(11)),
        (5, "RED", Decimal(11)),
        (5, "SUPRA", Decimal(8)),
        (6, "AXS", Decimal(17)),
        (6, "SAND", Decimal(17)),
        (6, "MANA", Decimal(14)),
        (6, "FLOW", Decimal(11)),
        (6, "ENJ", Decimal(11)),
        (6, "GALA", Decimal(9)),
        (6, "NOT", Decimal(7)),
        (6, "PRIME", Decimal(7)),
        (6, "G", Decimal(7)),
        (7, "DOGE", Decimal(34)),
        (7, "SHIB", Decimal(27)),
        (7, "FLOKI", Decimal(16)),
        (7, "PEPE", Decimal(11)),
        (7, "BONK", Decimal(5)),
        (7, "POPCAT", Decimal(2)),
        (7, "WIF", Decimal(2)),
        (7, "TRUMP", Decimal(1)),
        (7, "DOGS", Decimal(1)),
        (7, "MOG", Decimal(1)),
        (8, "APE", Decimal(35)),
        (8, "BLUR", Decimal(29)),
        (8, "LOOKS", Decimal(18)),
        (8, "GODS", Decimal(12)),
        (8, "PENGU", Decimal(6))
    ]
    for sector_id, symbol, percentage in tokens_data:
        await rq.add_token(sector_id=sector_id, symbol=symbol, percentage=percentage)


async def create_database():
    async with engine_pg.connect() as conn:
        # Проверяем, существует ли уже база данных
        query = "SELECT 1 FROM pg_database WHERE datname = 'cryptofolio_db'"
        result = await conn.execute(text(query))
        exists = result.scalar()

        if exists is None:
            await conn.execute(text('COMMIT')) #тк нельзя в рамках транзакции создать бд
            await conn.execute(text('CREATE DATABASE cryptofolio_db'))
            await async_main()
            await create_default_columns()
            print('База данных cryptofolio_db создана.')
