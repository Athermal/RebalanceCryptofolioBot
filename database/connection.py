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
        (1, "BTC", Decimal(40)),
        (1, "ETH", Decimal(24.5)),
        (1, "BNB", Decimal(4)),
        (1, "SOL", Decimal(3.5)),
        (1, "XRP", Decimal(3)),
        (1, "TON", Decimal(2.5)),
        (1, "ADA", Decimal(2)),
        (1, "TRX", Decimal(2)),
        (1, "AVAX", Decimal(1.5)),
        (1, "DOT", Decimal(1.5)),
        (1, "XLM", Decimal(1.5)),
        (1, "HBAR", Decimal(1.5)),
        (1, "LTC", Decimal(1)),
        (1, "SUI", Decimal(1)),
        (1, "NEAR", Decimal(1)),
        (1, "ATOM", Decimal(1)),
        (1, "ICP", Decimal(0.5)),
        (1, "ETC", Decimal(0.5)),
        (1, "BCH", Decimal(0.5)),
        (1, "ALGO", Decimal(0.5)),
        (1, "SEI", Decimal(0.5)),
        (1, "XTZ", Decimal(0.5)),
        (1, "EGLD", Decimal(0.5)),
        (1, "XMR", Decimal(0.5)),
        (1, "PI", Decimal(0.5)),
        (1, "APT", Decimal(0.3)),
        (1, "FIL", Decimal(0.3)),
        (1, "CRO", Decimal(0.3)),
        (1, "ASTR", Decimal(0.3)),
        (1, "CSPR", Decimal(0.3)),
        (1, "KDA", Decimal(0.3)),
        (1, "TIA", Decimal(0.3)),
        (1, "KAVA", Decimal(0.3)),
        (1, "ZETA", Decimal(0.3)),
        (1, "KAS", Decimal(0.2)),
        (1, "XEC", Decimal(0.2)),
        (1, "ONT", Decimal(0.2)),
        (1, "HIVE", Decimal(0.2)),
        (1, "CKB", Decimal(0.2)),
        (1, "BERA", Decimal(0.2)),
        (1, "IP", Decimal(0.1)),
        (2, "ARB", Decimal(14)),
        (2, "MATIC", Decimal(14)),
        (2, "OP", Decimal(13)),
        (2, "STRK", Decimal(10)),
        (2, "IMX", Decimal(10)),
        (2, "MNT", Decimal(6)),
        (2, "STX", Decimal(6)),
        (2, "METIS", Decimal(5)),
        (2, "POL", Decimal(4)),
        (2, "ZK", Decimal(4)),
        (2, "AEVO", Decimal(3)),
        (2, "MOVE", Decimal(3)),
        (2, "LRC", Decimal(2)),
        (2, "INJ", Decimal(2)),
        (2, "ALT", Decimal(1)),
        (2, "LSK", Decimal(1)),
        (2, "RON", Decimal(1)),
        (2, "ELF", Decimal(1)),
        (3, "D4", Decimal(10)),
        (3, "UNI", Decimal(10)),
        (3, "AAVE", Decimal(8)),
        (3, "COMP", Decimal(7)),
        (3, "CRV", Decimal(5)),
        (3, "FRAX", Decimal(5)),
        (3, "SUSHI", Decimal(4)),
        (3, "FXS", Decimal(4)),
        (3, "LDO", Decimal(4)),
        (3, "DYDX", Decimal(4)),
        (3, "CVX", Decimal(3.6)),
        (3, "MKR", Decimal(3)),
        (3, "GMX", Decimal(3)),
        (3, "SNX", Decimal(3)),
        (3, "1INCH", Decimal(2.7)),
        (3, "YFI", Decimal(2)),
        (3, "BAND", Decimal(1.8)),
        (3, "UMA", Decimal(1.8)),
        (3, "API3", Decimal(1.8)),
        (3, "RPL", Decimal(1.8)),
        (3, "OHM", Decimal(0.5)),
        (3, "JUP", Decimal(0.5)),
        (3, "ONDO", Decimal(0.5)),
        (3, "ZEC", Decimal(0.5)),
        (3, "MSOL", Decimal(0.5)),
        (3, "RAY", Decimal(0.5)),
        (3, "RUNE", Decimal(0.5)),
        (3, "AERO", Decimal(0.5)),
        (3, "PENDLE", Decimal(0.5)),
        (3, "TBTC", Decimal(0.5)),
        (3, "AUCTION", Decimal(0.5)),
        (3, "ENA", Decimal(0.5)),
        (3, "GNO", Decimal(0.5)),
        (3, "RSR", Decimal(0.5)),
        (3, "LAYER", Decimal(0.5)),
        (3, "OSMO", Decimal(0.5)),
        (3, "STG", Decimal(0.5)),
        (3, "WOO", Decimal(0.5)),
        (3, "ETHFI", Decimal(0.5)),
        (3, "COW", Decimal(0.5)),
        (3, "MORPHO", Decimal(0.45)),
        (3, "ZRX", Decimal(0.45)),
        (3, "DRIFT", Decimal(0.45)),
        (3, "LCX", Decimal(0.45)),
        (3, "FIDA", Decimal(0.45)),
        (3, "CPOOL", Decimal(0.45)),
        (3, "SPELL", Decimal(0.45)),
        (3, "USUAL", Decimal(0.45)),
        (3, "CUDOS", Decimal(0.45)),
        (3, "OM", Decimal(0.45)),
        (4, "FET", Decimal(20)),
        (4, "RENDER", Decimal(18)),
        (4, "GRT", Decimal(15)),
        (4, "FLUX", Decimal(12)),
        (4, "GRASS", Decimal(7)),
        (4, "K4TO", Decimal(7)),
        (4, "TAO", Decimal(7)),
        (4, "416Z", Decimal(7)),
        (4, "VIRTUAL", Decimal(7)),
        (5, "LINK", Decimal(40)),
        (5, "PYTH", Decimal(25)),
        (5, "FLR", Decimal(10)),
        (5, "RED", Decimal(10)),
        (5, "SUPRA", Decimal(8)),
        (5, "RLC", Decimal(7)),
        (6, "AXS", Decimal(15)),
        (6, "SAND", Decimal(15)),
        (6, "MANA", Decimal(12)),
        (6, "FLOW", Decimal(10)),
        (6, "ENJ", Decimal(10)),
        (6, "GALA", Decimal(8)),
        (6, "NOT", Decimal(6)),
        (6, "PRIME", Decimal(6)),
        (6, "SUPER", Decimal(6)),
        (6, "G", Decimal(6)),
        (6, "CHR", Decimal(6)),
        (7, "DOGE", Decimal(32)),
        (7, "SHIB", Decimal(26)),
        (7, "FLOKI", Decimal(15)),
        (7, "PEPE", Decimal(10)),
        (7, "BONK", Decimal(5)),
        (7, "CHEEMS", Decimal(3)),
        (7, "POPCAT", Decimal(2)),
        (7, "WIF", Decimal(2)),
        (7, "MELANIA", Decimal(1)),
        (7, "TRUMP", Decimal(1)),
        (7, "DOGS", Decimal(1)),
        (7, "MOG", Decimal(1)),
        (7, "FARTCOIN", Decimal(1)),
        (8, "APE", Decimal(30)),
        (8, "BLUR", Decimal(25)),
        (8, "LOOKS", Decimal(15)),
        (8, "RARI", Decimal(10)),
        (8, "GODS", Decimal(10)),
        (8, "PENGU", Decimal(5)),
        (8, "SOUL", Decimal(5))
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
