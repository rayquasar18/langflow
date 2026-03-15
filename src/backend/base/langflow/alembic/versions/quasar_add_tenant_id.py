"""Add tenant_id to folder and flow tables for multi-tenant isolation.

Revision ID: quasar_001_tenant
Revises: c187c3b9bb94
Create Date: 2026-03-15

Phase: EXPAND
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "quasar_001_tenant"
down_revision: str | None = "c187c3b9bb94"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # -- 1. Add tenant_id column to folder table (NULLABLE for system/starter content) --
    folder_columns = {col["name"] for col in inspector.get_columns("folder")}
    if "tenant_id" not in folder_columns:
        op.add_column("folder", sa.Column("tenant_id", sa.Uuid(), nullable=True))
    folder_indexes = {idx["name"] for idx in inspector.get_indexes("folder") if idx.get("name")}
    if "ix_folder_tenant_id" not in folder_indexes:
        op.create_index("ix_folder_tenant_id", "folder", ["tenant_id"])

    # -- 2. Add tenant_id column to flow table (NULLABLE for system/starter content) --
    flow_columns = {col["name"] for col in inspector.get_columns("flow")}
    if "tenant_id" not in flow_columns:
        op.add_column("flow", sa.Column("tenant_id", sa.Uuid(), nullable=True))
    flow_indexes = {idx["name"] for idx in inspector.get_indexes("flow") if idx.get("name")}
    if "ix_flow_tenant_id" not in flow_indexes:
        op.create_index("ix_flow_tenant_id", "flow", ["tenant_id"])

    # -- 3. Drop old unique constraints --
    # Use batch mode for SQLite compatibility (Langflow uses SQLite in dev/test)
    with op.batch_alter_table("folder", schema=None) as batch_op:
        batch_op.drop_constraint("unique_folder_name", type_="unique")
        batch_op.create_unique_constraint("unique_folder_name", ["tenant_id", "user_id", "name"])

    with op.batch_alter_table("flow", schema=None) as batch_op:
        batch_op.drop_constraint("unique_flow_name", type_="unique")
        batch_op.drop_constraint("unique_flow_endpoint_name", type_="unique")
        batch_op.create_unique_constraint("unique_flow_name", ["tenant_id", "user_id", "name"])
        batch_op.create_unique_constraint("unique_flow_endpoint_name", ["tenant_id", "user_id", "endpoint_name"])


def downgrade() -> None:
    # -- Reverse: drop new constraints, restore old ones, remove columns --
    with op.batch_alter_table("flow", schema=None) as batch_op:
        batch_op.drop_constraint("unique_flow_endpoint_name", type_="unique")
        batch_op.drop_constraint("unique_flow_name", type_="unique")
        batch_op.create_unique_constraint("unique_flow_name", ["user_id", "name"])
        batch_op.create_unique_constraint("unique_flow_endpoint_name", ["user_id", "endpoint_name"])

    with op.batch_alter_table("folder", schema=None) as batch_op:
        batch_op.drop_constraint("unique_folder_name", type_="unique")
        batch_op.create_unique_constraint("unique_folder_name", ["user_id", "name"])

    op.drop_index("ix_flow_tenant_id", table_name="flow")
    op.drop_column("flow", "tenant_id")

    op.drop_index("ix_folder_tenant_id", table_name="folder")
    op.drop_column("folder", "tenant_id")
