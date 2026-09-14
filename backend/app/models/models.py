"""
Modèles SQLAlchemy — Afrika Markets Intelligence
"""
from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum
import uuid

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class PlanEnum(str, enum.Enum):
    FREE            = "free"
    STARTER         = "starter"         # 29.99 USD/mois
    PRO             = "pro"             # 74.99 USD/mois
    EXPERT          = "expert"          # 199.99 USD/mois
    EXPERT_PREMIUM  = "expert_premium"  # 299.99 USD/mois


class StatusEnum(str, enum.Enum):
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    SUSPENDED = "suspended"
    TRIAL     = "trial"


class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, default=gen_uuid)
    email           = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name       = Column(String)
    country         = Column(String, default="CA")  # CA, CI, SN...
    phone           = Column(String)
    plan            = Column(Enum(PlanEnum), default=PlanEnum.FREE)
    status          = Column(Enum(StatusEnum), default=StatusEnum.TRIAL)
    is_admin        = Column(Boolean, default=False)
    trial_ends_at   = Column(DateTime)
    # ── Subscription lifecycle ────────────────────────────────
    cancel_at_period_end = Column(Boolean, default=False)   # annulation programmée fin de période
    pending_plan         = Column(Enum(PlanEnum), nullable=True)  # downgrade programmé fin de période
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, onupdate=func.now())


class Licence(Base):
    __tablename__ = "licences"

    id                   = Column(String, primary_key=True, default=gen_uuid)
    user_id              = Column(String, nullable=False, index=True)
    token                = Column(String, unique=True, nullable=False)
    plan                 = Column(Enum(PlanEnum))
    status               = Column(Enum(StatusEnum), default=StatusEnum.ACTIVE)
    billing_period_start = Column(DateTime, nullable=True)  # début de la période facturée
    expires_at           = Column(DateTime, nullable=False)
    created_at           = Column(DateTime, server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"

    id           = Column(String, primary_key=True, default=gen_uuid)
    user_id      = Column(String, nullable=False, index=True)
    amount       = Column(Float, nullable=False)
    currency     = Column(String, default="CAD")
    method       = Column(String)          # stripe, wave, orange_money
    status       = Column(String)          # pending, success, failed
    provider_ref = Column(String)          # Stripe session_id / Wave ref / OM ref
    plan         = Column(Enum(PlanEnum))
    created_at   = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(String, index=True)
    action     = Column(String)
    ip_address = Column(String)
    details    = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ── Trading Bot System ────────────────────────────────────────────────────────

class BotStatusEnum(str, enum.Enum):
    IDLE    = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR   = "error"


class TradingModeEnum(str, enum.Enum):
    PAPER   = "paper"    # simulation locale, pas d'ordre réel
    TESTNET = "testnet"  # exchange sandbox (Binance testnet, Deriv demo)
    LIVE    = "live"     # argent réel — confirmation explicite requise


class UserBrokerCredential(Base):
    """Clés API broker chiffrées Fernet, une ligne par (user, broker)."""
    __tablename__ = "user_broker_credentials"

    id              = Column(String, primary_key=True, default=gen_uuid)
    user_id         = Column(String, nullable=False, index=True)
    broker          = Column(String, nullable=False)   # "binance" | "exness" | "deriv"
    # Champs chiffrés (Fernet token stocké en clair en DB)
    api_key_enc     = Column(Text, nullable=True)      # API key chiffrée
    api_secret_enc  = Column(Text, nullable=True)      # API secret chiffrée
    extra_enc       = Column(Text, nullable=True)      # JSON chiffré (token Deriv, login MT5…)
    label           = Column(String, default="default")  # nom libre ex. "Binance principal"
    is_testnet      = Column(Boolean, default=False)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, onupdate=func.now())

    __table_args__ = (
        # Un seul credential par (user, broker, label)
        __import__("sqlalchemy").UniqueConstraint("user_id", "broker", "label"),
    )


class TradingBot(Base):
    """Configuration + état d'un bot de trading appartenant à un utilisateur."""
    __tablename__ = "trading_bots"

    id               = Column(String, primary_key=True, default=gen_uuid)
    user_id          = Column(String, nullable=False, index=True)
    name             = Column(String, nullable=False)
    broker           = Column(String, nullable=False)   # "binance" | "exness" | "deriv"
    symbol           = Column(String, nullable=False)   # ex. "BTCUSDT", "XAUUSD", "R_75"
    strategy         = Column(String, default="sma_crossover")  # identifiant stratégie

    # Mode d'exécution
    mode             = Column(Enum(TradingModeEnum), default=TradingModeEnum.PAPER)
    confirmed_live   = Column(Boolean, default=False)   # consentement live explicite

    # Paramètres stratégie (JSON texte)
    params_json      = Column(Text, default="{}")       # {"fast":9,"slow":21,"qty":0.01,...}

    # État runtime
    status           = Column(Enum(BotStatusEnum), default=BotStatusEnum.IDLE)
    paper_balance    = Column(Float, default=10000.0)   # solde simulation PAPER
    pnl_total        = Column(Float, default=0.0)       # PnL cumulé (USD)
    trades_count     = Column(Integer, default=0)

    # Lien credentials broker (nullable → paper mode sans credentials)
    credential_id    = Column(String, nullable=True)

    last_error       = Column(Text, nullable=True)
    started_at       = Column(DateTime, nullable=True)
    stopped_at       = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, server_default=func.now())
    updated_at       = Column(DateTime, onupdate=func.now())


class BotTrade(Base):
    """Historique des trades exécutés par un bot (open + close en une ligne)."""
    __tablename__ = "bot_trades"

    id           = Column(String, primary_key=True, default=gen_uuid)
    bot_id       = Column(String, nullable=False, index=True)
    user_id      = Column(String, nullable=False, index=True)
    symbol       = Column(String, nullable=False)
    side         = Column(String, nullable=False)   # "buy" | "sell"
    qty          = Column(Float, nullable=False)
    entry_price  = Column(Float, nullable=True)
    exit_price   = Column(Float, nullable=True)
    pnl          = Column(Float, default=0.0)       # PnL net en USD
    reason       = Column(String, nullable=True)    # "signal" | "stop_loss" | "take_profit"
    created_at   = Column(DateTime, server_default=func.now())
