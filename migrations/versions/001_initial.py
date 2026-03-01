"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # work_orders
    op.create_table(
        "work_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_type", sa.String(100), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=True, default=1),
        sa.Column(
            "status",
            sa.Enum("PENDING", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "CANCELLED",
                    name="workorderstatus"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_orders_id", "work_orders", ["id"])
    op.create_index("ix_work_orders_status", "work_orders", ["status"])
    op.create_index("ix_work_orders_status_created", "work_orders", ["status", "created_at"])

    # stations
    op.create_table(
        "stations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "type",
            sa.Enum("CUTTING", "ASSEMBLY", "QA", "PACKAGING", name="stationtype"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("RUNNING", "IDLE", "DOWN", "HOLD", name="stationstatus"),
            nullable=True,
        ),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_stations_id", "stations", ["id"])
    op.create_index("ix_stations_type", "stations", ["type"])
    op.create_index("ix_stations_status", "stations", ["status"])

    # events
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "type",
            sa.Enum(
                "WORK_ORDER_STARTED", "WORK_ORDER_COMPLETED", "STEP_COMPLETED",
                "DEFECT_FOUND", "MACHINE_DOWN", "MACHINE_UP", "MACHINE_IDLE", "QA_HOLD",
                name="eventtype",
            ),
            nullable=False,
        ),
        sa.Column("station_id", sa.Integer(), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column("work_order_id", sa.Integer(), sa.ForeignKey("work_orders.id"), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_id", "events", ["id"])
    op.create_index("ix_events_type", "events", ["type"])
    op.create_index("ix_events_timestamp", "events", ["timestamp"])
    op.create_index("ix_events_station_id", "events", ["station_id"])
    op.create_index("ix_events_work_order_id", "events", ["work_order_id"])
    op.create_index("ix_events_type_timestamp", "events", ["type", "timestamp"])
    op.create_index("ix_events_station_timestamp", "events", ["station_id", "timestamp"])

    # kpi_history
    op.create_table(
        "kpi_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("throughput", sa.Float(), nullable=True, default=0.0),
        sa.Column("defect_rate", sa.Float(), nullable=True, default=0.0),
        sa.Column("downtime_minutes", sa.Float(), nullable=True, default=0.0),
        sa.Column("avg_cycle_time", sa.Float(), nullable=True, default=0.0),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kpi_history_id", "kpi_history", ["id"])
    op.create_index("ix_kpi_history_timestamp", "kpi_history", ["timestamp"])

    # automation_rules
    op.create_table(
        "automation_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("condition_json", sa.JSON(), nullable=False),
        sa.Column("action_json", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True, default=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_automation_rules_id", "automation_rules", ["id"])


def downgrade() -> None:
    op.drop_table("automation_rules")
    op.drop_table("kpi_history")
    op.drop_table("events")
    op.drop_table("stations")
    op.drop_table("work_orders")
    # Drop custom enums
    for enum_name in ["workorderstatus", "stationtype", "stationstatus", "eventtype"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
