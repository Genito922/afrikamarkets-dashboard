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
    FREE    = "free"
    STARTER = "starter"   # 9.99 CAD/mois
    PRO     = "pro"       # 24.99 CAD/mois
    EXPERT  = "expert"    # 49.99 CAD/mois


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
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, onupdate=func.now())


class Licence(Base):
    __tablename__ = "licences"

    id         = Column(String, primary_key=True, default=gen_uuid)
    user_id    = Column(String, nullable=False, index=True)
    token      = Column(String, unique=True, nullable=False)
    plan       = Column(Enum(PlanEnum))
    status     = Column(Enum(StatusEnum), default=StatusEnum.ACTIVE)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


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
