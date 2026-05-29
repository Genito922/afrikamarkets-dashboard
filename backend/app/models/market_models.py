"""
Market Data Models — Afrika Markets Intelligence
Tables : brvm_actions, brvm_indices, brvm_market_summary
"""
from sqlalchemy import (
    Column, String, Float, BigInteger, Date, DateTime,
    Integer, UniqueConstraint,
)
from sqlalchemy.sql import func
from backend.app.models.models import Base


class BrvmAction(Base):
    __tablename__ = "brvm_actions"
    __table_args__ = (
        UniqueConstraint("symbole", "date", name="uq_action_date"),
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    symbole      = Column(String(10), nullable=False, index=True)
    nom          = Column(String(100))
    secteur      = Column(String(50))
    cours_ouv    = Column(Float)
    cours        = Column(Float)        # close
    cours_veille = Column(Float)        # previous close
    variation    = Column(Float)        # % daily change
    volume       = Column(BigInteger)
    date         = Column(Date, nullable=False, index=True)
    scraped_at   = Column(DateTime, server_default=func.now())


class BrvmIndex(Base):
    __tablename__ = "brvm_indices"
    __table_args__ = (
        UniqueConstraint("nom", "date", name="uq_index_date"),
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    nom          = Column(String(80), nullable=False, index=True)
    type         = Column(String(20))   # "marche" | "sectoriel"
    cloture_prec = Column(Float)
    cloture      = Column(Float)
    variation    = Column(Float)
    var_ytd      = Column(Float)
    date         = Column(Date, nullable=False, index=True)
    scraped_at   = Column(DateTime, server_default=func.now())


class BrvmMarketSummary(Base):
    __tablename__ = "brvm_market_summary"
    __table_args__ = (
        UniqueConstraint("date", name="uq_summary_date"),
    )

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    cap_actions_raw     = Column(String(100))
    cap_obligations_raw = Column(String(100))
    transactions_raw    = Column(String(100))
    date                = Column(Date, nullable=False, index=True)
    scraped_at          = Column(DateTime, server_default=func.now())
