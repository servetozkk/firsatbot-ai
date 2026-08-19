"""Existing FırsatAI schema baseline.

Revision ID: 20260801_0001
Revises: None
Create Date: 2026-08-01
"""
from typing import Sequence, Union

revision: str = "20260801_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing installations are created and normalized by create_db(), then stamped.
    pass


def downgrade() -> None:
    # Baseline intentionally does not delete existing application data.
    pass
