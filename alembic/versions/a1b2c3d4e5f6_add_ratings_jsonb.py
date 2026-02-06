"""add ratings jsonb

Revision ID: a1b2c3d4e5f6
Revises: 4b20989d22ed
Create Date: 2026-02-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "4b20989d22ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("movies", sa.Column("ratings", JSONB, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("movies", "ratings")
