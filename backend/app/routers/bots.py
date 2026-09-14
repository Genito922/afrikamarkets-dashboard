"""
CRUD + lifecycle des trading bots — /bots
Gating par plan :
  - FREE         : aucun bot
  - STARTER      : 1 bot PAPER uniquement
  - PRO          : 2 bots (PAPER + TESTNET)
  - EXPERT       : 5 bots (tous modes dont LIVE)
  - EXPERT_PREMIUM: 5 bots (identique EXPERT)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import require_plan, get_current_user
from backend.app.models.models import (
    PlanEnum, TradingBot, TradingModeEnum, BotStatusEnum,
    UserBrokerCredential, User, BotTrade,
)
from backend.app.services import bot_runner

router = APIRouter(
    prefix="/bots",
    tags=["bots"],
    # Au moins FREE+auth pour voir la section — le gating fin est dans chaque endpoint
    dependencies=[Depends(get_current_user)],
)

# ── Plan limits ───────────────────────────────────────────────────────────────
PLAN_BOT_LIMIT: dict[PlanEnum, int] = {
    PlanEnum.FREE:           0,
    PlanEnum.STARTER:        1,
    PlanEnum.PRO:            2,
    PlanEnum.EXPERT:         5,
    PlanEnum.EXPERT_PREMIUM: 5,
}

PLAN_ALLOWED_MODES: dict[PlanEnum, set[TradingModeEnum]] = {
    PlanEnum.FREE:           set(),
    PlanEnum.STARTER:        {TradingModeEnum.PAPER},
    PlanEnum.PRO:            {TradingModeEnum.PAPER, TradingModeEnum.TESTNET},
    PlanEnum.EXPERT:         {TradingModeEnum.PAPER, TradingModeEnum.TESTNET, TradingModeEnum.LIVE},
    PlanEnum.EXPERT_PREMIUM: {TradingModeEnum.PAPER, TradingModeEnum.TESTNET, TradingModeEnum.LIVE},
}

SUPPORTED_STRATEGIES = {"sma_crossover"}
SUPPORTED_BROKERS    = {"binance", "exness", "deriv"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class BotCreate(BaseModel):
    name: str
    broker: str
    symbol: str
    strategy: str = "sma_crossover"
    mode: TradingModeEnum = TradingModeEnum.PAPER
    params: dict = {}
    credential_id: str | None = None
    paper_balance: float = 10_000.0


class BotOut(BaseModel):
    id: str
    name: str
    broker: str
    symbol: str
    strategy: str
    mode: TradingModeEnum
    status: BotStatusEnum
    paper_balance: float
    pnl_total: float
    trades_count: int
    confirmed_live: bool
    last_error: str | None
    started_at: datetime | None
    stopped_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class BotUpdate(BaseModel):
    name: str | None = None
    params: dict | None = None
    paper_balance: float | None = None
    credential_id: str | None = None


class LiveConfirm(BaseModel):
    confirmed: bool  # doit être True explicitement


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_bot_or_404(bot_id: str, user_id: str, db: AsyncSession) -> TradingBot:
    result = await db.execute(
        select(TradingBot).where(TradingBot.id == bot_id, TradingBot.user_id == user_id)
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(404, "Bot introuvable")
    return bot


async def _count_user_bots(user_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(TradingBot).where(TradingBot.user_id == user_id)
    )
    return len(result.scalars().all())


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=BotOut, status_code=201)
async def create_bot(
    body: BotCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limit = PLAN_BOT_LIMIT.get(user.plan, 0)
    if limit == 0:
        raise HTTPException(403, "Votre plan ne permet pas de créer de bots. Passez au plan Starter.")

    count = await _count_user_bots(user.id, db)
    if count >= limit:
        raise HTTPException(
            403,
            f"Limite atteinte ({limit} bot(s) pour le plan {user.plan.value}). "
            "Passez à un plan supérieur pour en créer davantage."
        )

    allowed_modes = PLAN_ALLOWED_MODES.get(user.plan, set())
    if body.mode not in allowed_modes:
        raise HTTPException(
            403,
            f"Le mode '{body.mode.value}' n'est pas disponible pour le plan {user.plan.value}."
        )

    if body.broker not in SUPPORTED_BROKERS:
        raise HTTPException(400, f"Broker non supporté. Valeurs : {SUPPORTED_BROKERS}")

    if body.strategy not in SUPPORTED_STRATEGIES:
        raise HTTPException(400, f"Stratégie inconnue. Valeurs : {SUPPORTED_STRATEGIES}")

    # Valider credential si fourni
    if body.credential_id:
        cred_res = await db.execute(
            select(UserBrokerCredential).where(
                UserBrokerCredential.id == body.credential_id,
                UserBrokerCredential.user_id == user.id,
            )
        )
        if not cred_res.scalar_one_or_none():
            raise HTTPException(404, "Credential introuvable")

    bot = TradingBot(
        user_id=user.id,
        name=body.name,
        broker=body.broker,
        symbol=body.symbol,
        strategy=body.strategy,
        mode=body.mode,
        params_json=json.dumps(body.params),
        paper_balance=body.paper_balance,
        credential_id=body.credential_id,
        confirmed_live=False,
    )
    db.add(bot)
    await db.commit()
    await db.refresh(bot)
    return bot


@router.get("", response_model=list[BotOut])
async def list_bots(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TradingBot).where(TradingBot.user_id == user.id)
    )
    return result.scalars().all()


@router.get("/{bot_id}", response_model=BotOut)
async def get_bot(
    bot_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_bot_or_404(bot_id, user.id, db)


@router.patch("/{bot_id}", response_model=BotOut)
async def update_bot(
    bot_id: str,
    body: BotUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bot = await _get_bot_or_404(bot_id, user.id, db)

    if bot.status == BotStatusEnum.RUNNING:
        raise HTTPException(409, "Arrêtez le bot avant de le modifier.")

    if body.name is not None:
        bot.name = body.name
    if body.params is not None:
        bot.params_json = json.dumps(body.params)
    if body.paper_balance is not None and bot.mode == TradingModeEnum.PAPER:
        bot.paper_balance = body.paper_balance
    if body.credential_id is not None:
        cred_res = await db.execute(
            select(UserBrokerCredential).where(
                UserBrokerCredential.id == body.credential_id,
                UserBrokerCredential.user_id == user.id,
            )
        )
        if not cred_res.scalar_one_or_none():
            raise HTTPException(404, "Credential introuvable")
        bot.credential_id = body.credential_id

    await db.commit()
    await db.refresh(bot)
    return bot


@router.delete("/{bot_id}", status_code=204)
async def delete_bot(
    bot_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bot = await _get_bot_or_404(bot_id, user.id, db)
    if bot.status == BotStatusEnum.RUNNING:
        await bot_runner.stop_bot(bot_id)
    await db.delete(bot)
    await db.commit()


@router.post("/{bot_id}/confirm-live", response_model=BotOut)
async def confirm_live(
    bot_id: str,
    body: LiveConfirm,
    user: User = Depends(require_plan(PlanEnum.EXPERT)),
    db: AsyncSession = Depends(get_db),
):
    """
    Étape obligatoire avant de démarrer un bot en mode LIVE.
    L'utilisateur doit envoyer {"confirmed": true} explicitement.
    """
    bot = await _get_bot_or_404(bot_id, user.id, db)
    if bot.mode != TradingModeEnum.LIVE:
        raise HTTPException(400, "Ce bot n'est pas en mode LIVE.")
    if not body.confirmed:
        raise HTTPException(400, "Vous devez confirmer explicitement en envoyant confirmed=true.")
    bot.confirmed_live = True
    await db.commit()
    await db.refresh(bot)
    return bot


@router.post("/{bot_id}/start", response_model=BotOut)
async def start_bot(
    bot_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bot = await _get_bot_or_404(bot_id, user.id, db)

    if bot.status == BotStatusEnum.RUNNING:
        raise HTTPException(409, "Le bot est déjà en cours d'exécution.")

    if bot.mode == TradingModeEnum.LIVE and not bot.confirmed_live:
        raise HTTPException(
            403,
            "Confirmez d'abord le mode live via POST /bots/{id}/confirm-live."
        )

    if bot.mode != TradingModeEnum.PAPER and not bot.credential_id:
        raise HTTPException(
            400,
            "Un credential broker est requis pour les modes TESTNET et LIVE."
        )

    # Charger le credential si nécessaire
    cred = None
    if bot.credential_id:
        cred_res = await db.execute(
            select(UserBrokerCredential).where(UserBrokerCredential.id == bot.credential_id)
        )
        cred = cred_res.scalar_one_or_none()

    bot.status = BotStatusEnum.RUNNING
    bot.started_at = datetime.now(timezone.utc)
    bot.last_error = None
    await db.commit()

    # Lancer la tâche asyncio
    await bot_runner.start_bot(bot, cred)

    await db.refresh(bot)
    return bot


@router.post("/{bot_id}/stop", response_model=BotOut)
async def stop_bot(
    bot_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bot = await _get_bot_or_404(bot_id, user.id, db)

    if bot.status != BotStatusEnum.RUNNING:
        raise HTTPException(409, "Le bot n'est pas en cours d'exécution.")

    await bot_runner.stop_bot(bot_id)

    bot.status = BotStatusEnum.STOPPED
    bot.stopped_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(bot)
    return bot


# ── Trade history ─────────────────────────────────────────────────────────────

class TradeOut(BaseModel):
    id: str
    bot_id: str
    symbol: str
    side: str
    qty: float
    entry_price: float | None
    exit_price: float | None
    pnl: float
    reason: str | None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/{bot_id}/trades", response_model=list[TradeOut])
async def get_bot_trades(
    bot_id: str,
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_bot_or_404(bot_id, user.id, db)
    result = await db.execute(
        select(BotTrade)
        .where(BotTrade.bot_id == bot_id, BotTrade.user_id == user.id)
        .order_by(desc(BotTrade.created_at))
        .limit(limit)
    )
    return result.scalars().all()


# ── Fleet dashboard summary ───────────────────────────────────────────────────

@router.get("/dashboard/summary")
async def fleet_dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Agrégats fleet-level pour le dashboard bots :
    total_pnl, running_count, total_trades, win_rate,
    per_bot stats, equity_curve (cumul PnL par jour).
    """
    # Tous les bots de l'user
    bots_res = await db.execute(
        select(TradingBot).where(TradingBot.user_id == user.id)
    )
    bots = bots_res.scalars().all()

    if not bots:
        return {
            "total_pnl": 0.0,
            "running_count": 0,
            "total_trades": 0,
            "win_rate": None,
            "per_bot": [],
            "equity_curve": [],
            "recent_trades": [],
        }

    bot_ids = [b.id for b in bots]

    # Tous les trades
    trades_res = await db.execute(
        select(BotTrade)
        .where(BotTrade.user_id == user.id)
        .order_by(BotTrade.created_at)
    )
    all_trades = trades_res.scalars().all()

    total_trades = len(all_trades)
    winning      = sum(1 for t in all_trades if t.pnl > 0)
    win_rate     = round(winning / total_trades * 100, 1) if total_trades else None
    total_pnl    = round(sum(t.pnl for t in all_trades), 4)
    running_count = sum(1 for b in bots if b.status == BotStatusEnum.RUNNING)

    # Equity curve : cumul PnL chronologique (tous bots confondus)
    cumul = 0.0
    equity_curve = []
    for t in all_trades:
        cumul = round(cumul + t.pnl, 4)
        equity_curve.append({
            "date":  t.created_at.strftime("%Y-%m-%d %H:%M"),
            "pnl":   round(t.pnl, 4),
            "cumul": cumul,
        })

    # Per-bot summary
    per_bot = []
    for b in bots:
        bot_trades = [t for t in all_trades if t.bot_id == b.id]
        bt_total   = len(bot_trades)
        bt_win     = sum(1 for t in bot_trades if t.pnl > 0)
        per_bot.append({
            "id":           b.id,
            "name":         b.name,
            "broker":       b.broker,
            "symbol":       b.symbol,
            "mode":         b.mode.value,
            "status":       b.status.value,
            "pnl_total":    round(b.pnl_total or 0.0, 4),
            "trades_count": b.trades_count or 0,
            "win_rate":     round(bt_win / bt_total * 100, 1) if bt_total else None,
            "paper_balance": b.paper_balance,
            "started_at":   b.started_at.isoformat() if b.started_at else None,
        })

    # 20 derniers trades (toutes stratégies)
    recent_trades = [
        {
            "id":          t.id,
            "bot_id":      t.bot_id,
            "symbol":      t.symbol,
            "side":        t.side,
            "qty":         t.qty,
            "entry_price": t.entry_price,
            "exit_price":  t.exit_price,
            "pnl":         round(t.pnl, 4),
            "reason":      t.reason,
            "created_at":  t.created_at.isoformat(),
        }
        for t in list(reversed(all_trades))[:20]
    ]

    return {
        "total_pnl":    total_pnl,
        "running_count": running_count,
        "total_trades": total_trades,
        "win_rate":     win_rate,
        "per_bot":      per_bot,
        "equity_curve": equity_curve,
        "recent_trades": recent_trades,
    }
