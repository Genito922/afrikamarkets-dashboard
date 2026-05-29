"""Création des tables marché BRVM

Revision ID: 001
Revises:
Create Date: 2026-05-28

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brvm_actions",
        sa.Column("id",           sa.Integer(),     nullable=False, autoincrement=True),
        sa.Column("symbole",      sa.String(10),    nullable=False),
        sa.Column("nom",          sa.String(100),   nullable=True),
        sa.Column("secteur",      sa.String(50),    nullable=True),
        sa.Column("cours_ouv",    sa.Float(),       nullable=True),
        sa.Column("cours",        sa.Float(),       nullable=True),
        sa.Column("cours_veille", sa.Float(),       nullable=True),
        sa.Column("variation",    sa.Float(),       nullable=True),
        sa.Column("volume",       sa.BigInteger(),  nullable=True),
        sa.Column("date",         sa.Date(),        nullable=False),
        sa.Column("scraped_at",   sa.DateTime(),    server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbole", "date", name="uq_action_date"),
    )
    op.create_index("ix_brvm_actions_symbole", "brvm_actions", ["symbole"])
    op.create_index("ix_brvm_actions_date",    "brvm_actions", ["date"])

    op.create_table(
        "brvm_indices",
        sa.Column("id",           sa.Integer(),    nullable=False, autoincrement=True),
        sa.Column("nom",          sa.String(80),   nullable=False),
        sa.Column("type",         sa.String(20),   nullable=True),
        sa.Column("cloture_prec", sa.Float(),      nullable=True),
        sa.Column("cloture",      sa.Float(),      nullable=True),
        sa.Column("variation",    sa.Float(),      nullable=True),
        sa.Column("var_ytd",      sa.Float(),      nullable=True),
        sa.Column("date",         sa.Date(),       nullable=False),
        sa.Column("scraped_at",   sa.DateTime(),   server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nom", "date", name="uq_index_date"),
    )
    op.create_index("ix_brvm_indices_nom",  "brvm_indices", ["nom"])
    op.create_index("ix_brvm_indices_date", "brvm_indices", ["date"])

    op.create_table(
        "brvm_market_summary",
        sa.Column("id",                  sa.Integer(),    nullable=False, autoincrement=True),
        sa.Column("cap_actions_raw",     sa.String(100),  nullable=True),
        sa.Column("cap_obligations_raw", sa.String(100),  nullable=True),
        sa.Column("transactions_raw",    sa.String(100),  nullable=True),
        sa.Column("date",                sa.Date(),       nullable=False),
        sa.Column("scraped_at",          sa.DateTime(),   server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", name="uq_summary_date"),
    )
    op.create_index("ix_brvm_market_summary_date", "brvm_market_summary", ["date"])


def downgrade() -> None:
    op.drop_table("brvm_market_summary")
    op.drop_table("brvm_indices")
    op.drop_table("brvm_actions")
