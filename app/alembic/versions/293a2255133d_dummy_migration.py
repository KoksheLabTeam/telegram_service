"""Dummy migration to sync with lost revision

Revision ID: 293a2255133d
Revises: 423455fd3281
Create Date: 2025-03-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '293a2255133d'
down_revision = '423455fd3281'
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass