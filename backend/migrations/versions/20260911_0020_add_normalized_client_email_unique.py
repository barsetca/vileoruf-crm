"""add normalized client email uniqueness

Revision ID: 20260911_0020
Revises: 20260910_0019
"""

from alembic import op

revision = "20260911_0020"
down_revision = "20260910_0019"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE UNIQUE INDEX uq_clients_normalized_email "
        "ON clients (lower(btrim(email))) "
        "WHERE email IS NOT NULL AND btrim(email) <> ''"
    )


def downgrade():
    op.execute("DROP INDEX uq_clients_normalized_email")
