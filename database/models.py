from decimal import Decimal

from sqlalchemy import Numeric, String, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs

PERCENTAGE_CONSTRAINT = CheckConstraint('percentage BETWEEN 0.00 AND 100.00',
                                        name='percentage_check')


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Deposit(Base):
    __tablename__ = 'deposits'

    id: Mapped[int] = mapped_column(primary_key=True)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)


class Direction(Base):
    __tablename__ = 'directions'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    percentage: Mapped[Decimal] = mapped_column(Numeric(5,2), nullable=False)
    balance_usd: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=True, default=0.0
    )

    __table_args__ = (PERCENTAGE_CONSTRAINT,)


class Sector(Base):
    __tablename__ = 'sectors'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    balance_usd: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=True, default=0.0
    )
    tokens: Mapped[list['Token']] = relationship(
        'Token', back_populates='sector', cascade='all, delete-orphan'
    )

    __table_args__ = (PERCENTAGE_CONSTRAINT,)


class Token(Base):
    __tablename__ = 'tokens'

    id: Mapped[int] = mapped_column(primary_key=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey('sectors.id'), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    balance_usd: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=True, default=0.0
    )
    balance_entry_usd: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=True, default=0.0
    )
    current_coinprice_usd: Mapped[Decimal] = mapped_column(
        Numeric(60,30), nullable=True
    )

    sector: Mapped['Sector'] = relationship('Sector', back_populates='tokens')
    position: Mapped['Position'] = relationship(
        'Position', back_populates='token', cascade='all, delete-orphan'
    )
    orders: Mapped[list['Order']] = relationship(
        'Order', back_populates='token', cascade='all, delete-orphan'
    )

    __table_args__ = (PERCENTAGE_CONSTRAINT,)


class Position(Base):
    __tablename__ = 'positions'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    token_id: Mapped[int] = mapped_column(ForeignKey('tokens.id'), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(60, 30), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(60, 30), nullable=False)
    invested_usd: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    bodyfix_price_usd: Mapped[Decimal] = mapped_column(Numeric(60, 30), nullable=False)
    total_usd: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=True, default=0.0)

    token: Mapped['Token'] = relationship('Token', back_populates='position')


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    token_id: Mapped[int] = mapped_column(ForeignKey('tokens.id'), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(60, 30), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(60, 30), nullable=False)
    type: Mapped[str] = mapped_column(String(4), default='Buy')
    added_at: Mapped[str] = mapped_column(TIMESTAMP, default=func.current_timestamp())

    token: Mapped['Token'] = relationship('Token', back_populates='orders')
