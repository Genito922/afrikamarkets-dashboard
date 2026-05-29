"""
Script de création d'un utilisateur admin
Afrika Markets Intelligence
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from getpass import getpass

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.models.models import User, AuditLog, PlanEnum, StatusEnum
from backend.app.core.security import hash_password

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./brvm_analyzer.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables():
    from backend.app.models.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables vérifiées / créées")


async def list_tables():
    from sqlalchemy import text
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
        tables = result.fetchall()
    print("\n📋 Tables existantes dans la base :")
    for t in tables:
        print(f"   • {t[0]}")
    print()


async def create_admin(email: str, password: str, full_name: str):
    async with AsyncSessionLocal() as session:
        # Vérifier si l'email existe déjà
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.is_admin:
                print(f"⚠️  Un admin existe déjà avec cet email : {email}")
                return
            else:
                # Upgrade en admin
                existing.is_admin = True
                existing.plan = PlanEnum.EXPERT
                existing.status = StatusEnum.ACTIVE
                await session.commit()
                print(f"✅ Utilisateur existant promu ADMIN : {email}")
                return

        # Créer le nouvel admin
        admin = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            country="CI",
            plan=PlanEnum.EXPERT,
            status=StatusEnum.ACTIVE,
            is_admin=True,
            trial_ends_at=datetime.utcnow() + timedelta(days=3650),  # 10 ans
        )
        session.add(admin)
        session.add(AuditLog(
            user_id=admin.id,
            action="ADMIN_CREATED",
            ip_address="127.0.0.1",
            details=f"Compte admin créé via script : {email}",
        ))
        await session.commit()
        print(f"\n✅ Admin créé avec succès !")
        print(f"   📧 Email    : {email}")
        print(f"   👤 Nom      : {full_name}")
        print(f"   🎯 Plan     : EXPERT")
        print(f"   🔑 Statut   : ACTIVE")
        print(f"   🛡️  Admin    : True")
        print(f"   🆔 ID       : {admin.id}")


async def show_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"\n👥 Utilisateurs dans la base ({len(users)}) :")
        for u in users:
            admin_tag = " 🛡️ ADMIN" if u.is_admin else ""
            print(f"   • {u.email} | {u.plan.value} | {u.status.value}{admin_tag}")
    print()


async def main():
    print("=" * 50)
    print("  Afrika Markets — Initialisation Admin")
    print("=" * 50)

    await create_tables()
    await list_tables()

    print("📝 Créer le compte administrateur :")
    email     = input("   Email     : ").strip()
    full_name = input("   Nom complet : ").strip()
    password  = getpass("   Mot de passe : ")
    confirm   = getpass("   Confirmer    : ")

    if password != confirm:
        print("❌ Les mots de passe ne correspondent pas.")
        return

    if len(password) < 8:
        print("❌ Mot de passe trop court (min 8 caractères).")
        return

    await create_admin(email, password, full_name)
    await show_users()


if __name__ == "__main__":
    asyncio.run(main())
