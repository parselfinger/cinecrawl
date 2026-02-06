"""add_cascade_delete_for_showtimes

Revision ID: eefd26f41b80
Revises: 13b1c9cdb618
Create Date: 2026-01-19 20:30:11.699983

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eefd26f41b80"
down_revision: str | Sequence[str] | None = "13b1c9cdb618"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the existing foreign key constraint
    op.drop_constraint("showtimes_movie_id_fkey", "showtimes", type_="foreignkey")

    # Recreate the foreign key constraint with CASCADE DELETE
    op.create_foreign_key(
        "showtimes_movie_id_fkey",
        "showtimes",
        "movies",
        ["movie_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the CASCADE foreign key constraint
    op.drop_constraint("showtimes_movie_id_fkey", "showtimes", type_="foreignkey")

    # Recreate the foreign key constraint without CASCADE
    op.create_foreign_key(
        "showtimes_movie_id_fkey", "showtimes", "movies", ["movie_id"], ["id"]
    )
