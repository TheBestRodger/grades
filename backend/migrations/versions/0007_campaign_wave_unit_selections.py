"""Add planned organizational scope for campaign waves.

Revision ID: 0007_campaign_wave_unit_selections
Revises: 0006_campaign_waves
Create Date: 2026-05-26
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007_campaign_wave_unit_selections"
down_revision: str | None = "0006_campaign_waves"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if "campaign_wave_unit_selections" in set(sa.inspect(bind).get_table_names()):
        return
    op.create_table(
        "campaign_wave_unit_selections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_wave_id", sa.Integer(), sa.ForeignKey("campaign_waves.id"), nullable=False),
        sa.Column("org_unit_id", sa.Integer(), sa.ForeignKey("org_units.id"), nullable=False),
        sa.Column("inclusion_status", sa.String(length=32), nullable=False),
        sa.Column("selected_by_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("campaign_wave_id", "org_unit_id", name="uq_campaign_wave_org_unit"),
    )


def downgrade() -> None:
    op.drop_table("campaign_wave_unit_selections")
