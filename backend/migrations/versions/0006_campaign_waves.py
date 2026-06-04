"""Add waves inside profiling campaigns.

Revision ID: 0006_campaign_waves
Revises: 0005_documents
Create Date: 2026-05-26
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_campaign_waves"
down_revision: str | None = "0005_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


campaign_waves = sa.table(
    "campaign_waves",
    sa.column("id", sa.Integer),
    sa.column("campaign_id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("status", sa.String),
    sa.column("due_at", sa.Date),
    sa.column("created_by_id", sa.Integer),
    sa.column("is_demo", sa.Boolean),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "campaign_waves" not in table_names:
        op.create_table(
            "campaign_waves",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("due_at", sa.Date()),
            sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
            sa.Column("is_demo", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    participant_columns = {
        column["name"] for column in sa.inspect(bind).get_columns("campaign_participants")
    }
    if "campaign_wave_id" not in participant_columns:
        op.add_column("campaign_participants", sa.Column("campaign_wave_id", sa.Integer()))

    campaigns = bind.execute(
        sa.text(
            "SELECT id, due_at, created_by_id, is_demo FROM campaigns "
            "WHERE NOT EXISTS ("
            "SELECT 1 FROM campaign_waves WHERE campaign_waves.campaign_id = campaigns.id"
            ")"
        )
    ).mappings()
    for campaign in campaigns:
        bind.execute(
            sa.text(
                "INSERT INTO campaign_waves "
                "(campaign_id, name, status, due_at, created_by_id, is_demo) "
                "VALUES (:campaign_id, :name, :status, :due_at, :created_by_id, :is_demo)"
            )
            ,
            {
                "campaign_id": campaign["id"],
                "name": "Волна 1",
                "status": "active",
                "due_at": campaign["due_at"],
                "created_by_id": campaign["created_by_id"],
                "is_demo": campaign["is_demo"],
            },
        )

    waves = bind.execute(sa.text("SELECT id, campaign_id FROM campaign_waves")).mappings()
    for wave in waves:
        bind.execute(
            sa.text(
                "UPDATE campaign_participants "
                "SET campaign_wave_id = :wave_id "
                "WHERE campaign_id = :campaign_id AND campaign_wave_id IS NULL"
            ),
            {"wave_id": wave["id"], "campaign_id": wave["campaign_id"]},
        )


def downgrade() -> None:
    with op.batch_alter_table("campaign_participants") as batch_op:
        batch_op.drop_column("campaign_wave_id")
    op.drop_table("campaign_waves")
