"""
Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from alembic import op
import sqlalchemy as sa

${imports if imports else ""}


def upgrade():
% for stmt in upgrade_ops:
    ${stmt}
% endfor


def downgrade():
% for stmt in downgrade_ops:
    ${stmt}
% endfor
