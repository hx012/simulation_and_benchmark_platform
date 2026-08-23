"""Add administrator sessions and database-managed access policy.

Revision ID: 20260822_0003
Revises: 20260822_0002
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260822_0003"
down_revision: Union[str, Sequence[str], None] = "20260822_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "permission_sets",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requestable", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("system_managed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "protected_resources",
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("access_mode", sa.String(length=32), nullable=False),
        sa.Column("system_managed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "resource_permission_sets",
        sa.Column("resource_code", sa.String(length=128), nullable=False),
        sa.Column("permission_code", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["permission_code"], ["permission_sets.code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_code"], ["protected_resources.code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("resource_code", "permission_code"),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("auth_mode", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_user_sessions_expires", "user_sessions", ["expires_at"])
    op.create_index("ix_user_sessions_user_active", "user_sessions", ["user_id", "revoked_at"])

    permission_sets = sa.table(
        "permission_sets",
        sa.column("code", sa.String), sa.column("name", sa.String),
        sa.column("description", sa.Text), sa.column("requestable", sa.Boolean),
        sa.column("active", sa.Boolean), sa.column("system_managed", sa.Boolean),
    )
    op.bulk_insert(permission_sets, [
        {"code": "normal", "name": "平台基础权限", "description": "登录平台后默认具备的基础访问权限。", "requestable": False, "active": True, "system_managed": True},
        {"code": "benchmark_access", "name": "Benchmark 访问权限", "description": "浏览芯片、Benchmark 定义和测试结果。", "requestable": True, "active": True, "system_managed": False},
        {"code": "simulation_log", "name": "Simulator 日志访问权限", "description": "查看本人仿真任务的运行日志。", "requestable": True, "active": True, "system_managed": False},
    ])
    resources = sa.table(
        "protected_resources",
        sa.column("code", sa.String), sa.column("name", sa.String),
        sa.column("description", sa.Text), sa.column("access_mode", sa.String),
        sa.column("system_managed", sa.Boolean),
    )
    op.bulk_insert(resources, [
        {"code": "simulation.task", "name": "Simulator 任务", "description": "创建和查看本人仿真任务。", "access_mode": "normal", "system_managed": True},
        {"code": "simulation.log", "name": "Simulator 日志", "description": "查看本人仿真任务日志。", "access_mode": "permission", "system_managed": True},
        {"code": "benchmark.view", "name": "Benchmark", "description": "浏览芯片与 Benchmark 资产。", "access_mode": "permission", "system_managed": True},
        {"code": "permission.manage", "name": "权限管理", "description": "审批权限申请并配置资源访问策略。", "access_mode": "admin", "system_managed": True},
        {"code": "admin.manage", "name": "管理员管理", "description": "配置管理员账号和管理员密码。", "access_mode": "admin", "system_managed": True},
    ])
    mappings = sa.table(
        "resource_permission_sets",
        sa.column("resource_code", sa.String), sa.column("permission_code", sa.String),
    )
    op.bulk_insert(mappings, [
        {"resource_code": "benchmark.view", "permission_code": "benchmark_access"},
        {"resource_code": "simulation.log", "permission_code": "simulation_log"},
    ])

    connection = op.get_bind()
    users = sa.table(
        "users", sa.column("employee_id", sa.String), sa.column("display_name", sa.String),
        sa.column("role", sa.String)
    )
    admin_exists = connection.scalar(
        sa.select(sa.func.count()).select_from(users).where(users.c.employee_id == "admin")
    )
    test_user_exists = connection.scalar(
        sa.select(sa.func.count()).select_from(users).where(users.c.employee_id == "test-user")
    )
    connection.execute(users.update().values(role="normal"))
    if test_user_exists and not admin_exists:
        connection.execute(
            users.update().where(users.c.employee_id == "test-user").values(employee_id="admin", role="admin", display_name="admin")
        )
        connection.execute(sa.text("UPDATE simulation_tasks SET owner_id = 'admin' WHERE owner_id = 'test-user'"))
        connection.execute(sa.text("UPDATE upload_sessions SET owner_id = 'admin' WHERE owner_id = 'test-user'"))
    elif admin_exists:
        connection.execute(users.update().where(users.c.employee_id == "admin").values(role="admin"))


def downgrade() -> None:
    op.drop_index("ix_user_sessions_user_active", table_name="user_sessions")
    op.drop_index("ix_user_sessions_expires", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("resource_permission_sets")
    op.drop_table("protected_resources")
    op.drop_table("permission_sets")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "password_hash")
