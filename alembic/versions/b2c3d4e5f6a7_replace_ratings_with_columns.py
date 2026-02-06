"""replace ratings jsonb with rating columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("movies", "ratings")
    op.add_column(
        "movies", sa.Column("rotten_tomatoes_rating", sa.Integer(), nullable=True)
    )
    op.add_column("movies", sa.Column("metacritic_rating", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("movies", "metacritic_rating")
    op.drop_column("movies", "rotten_tomatoes_rating")
    op.add_column("movies", sa.Column("ratings", JSONB, nullable=True))
