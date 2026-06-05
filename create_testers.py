"""
Script de création des comptes testeurs — All Access
Afrika Markets Intelligence
Usage : python create_testers.py
"""
import asyncio
import uuid
import bcrypt
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.app.models.models import User, AuditLog, PlanEnum, StatusEnum

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./brvm_analyzer.db")
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── Modifier ici les comptes testeurs ────────────────────────
# Format : (email, mot_de_passe, nom_complet, pays)
TESTERS = [
    ("testeur1@afrikamarkets.com",  "Test@Afrika1",  "Testeur Alpha",    "CI"),
    ("testeur2@afrikamarkets.com",  "Test@Afrika2",  "Testeur Beta",     "SN"),
    ("testeur3@afrikamarkets.com",  "Test@Afrika3",  "Testeur Gamma",    "CA"),
    ("testeur4@afrikamarkets.com",  "Test@Afrika4",  "Testeur Delta",    "FR"),
    ("testeur5@afrikamarkets.com",  "Test@Afrika5",  "Testeur Epsilon",  "BF"),
    # Ajouter d'autres ici :
    # ("email@example.com", "MotDePasse123!", "Prénom Nom", "CI"),
]

def hash_pwd(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def create_tables():
    from backend.app.models.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_tester(session, email, password, full_name, country):
    result = await session.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()

    if existing:
        # Mise à jour si existe déjà
        existing.plan = PlanEnum.EXPERT
        existing.status = StatusEnum.ACTIVE
        existing.hashed_password = hash_pwd(password)
        existing.trial_ends_at = datetime.utcnow() + timedelta(days=365)
        print(f"  🔄 Mis à jour  : {email}")
        return "updated"

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_pwd(password),
        full_name=full_name,
        country=country,
        plan=PlanEnum.EXPERT,
        status=StatusEnum.ACTIVE,
        is_admin=False,
        trial_ends_at=datetime.utcnow() + timedelta(days=365),
    )
    session.add(user)
    session.add(AuditLog(
        user_id=user.id,
        action="TESTER_CREATED",
        ip_address="127.0.0.1",
        details=f"Compte testeur all-access créé : {email}",
    ))
    print(f"  ✅ Créé        : {email} ({full_name}) — {country}")
    return "created"


async def show_all_users(session):
    result = await session.execute(select(User))
    users = result.scalars().all()
    print(f"\n{'─'*65}")
    print(f"  {'EMAIL':<35} {'PLAN':<10} {'STATUT':<10} {'ADMIN'}")
    print(f"{'─'*65}")
    for u in users:
        admin_tag = "🛡️ oui" if u.is_admin else "non"
        print(f"  {u.email:<35} {u.plan.value:<10} {u.status.value:<10} {admin_tag}")
    print(f"{'─'*65}")
    print(f"  Total : {len(users)} compte(s)\n")


async def main():
    print("\n" + "═"*65)
    print("  Afrika Markets Intelligence — Création Comptes Testeurs")
    print("═"*65)

    await create_tables()

    created = updated = 0
    async with AsyncSessionLocal() as session:
        print(f"\n📋 Traitement de {len(TESTERS)} testeur(s)...\n")
        for email, password, full_name, country in TESTERS:
            result = await create_tester(session, email, password, full_name, country)
            if result == "created":
                created += 1
            else:
                updated += 1
        await session.commit()

        print(f"\n  ✅ {created} créé(s)  |  🔄 {updated} mis à jour")

        print(f"\n{'═'*65}")
        print("  📊 État complet de la base")
        await show_all_users(session)

        print("  🔑 Identifiants testeurs :")
        print(f"{'─'*65}")
        for email, password, full_name, _ in TESTERS:
            print(f"  📧 {email}")
            print(f"  🔑 {password}")
            print()

    print("  💡 Pour modifier les comptes, éditez la liste TESTERS")
    print("     en haut de ce fichier et relancez le script.\n")


if __name__ == "__main__":
    asyncio.run(main())
