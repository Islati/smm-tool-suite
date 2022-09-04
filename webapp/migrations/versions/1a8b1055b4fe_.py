"""empty message

Revision ID: 1a8b1055b4fe
Revises: 9b0158f3cfb1
Create Date: 2022-09-04 14:53:11.860265

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a8b1055b4fe'
down_revision = '9b0158f3cfb1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('media_uploads', sa.Column('clip_id', sa.Integer(), nullable=False))
    op.create_foreign_key(None, 'media_uploads', 'video_clips', ['clip_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'media_uploads', type_='foreignkey')
    op.drop_column('media_uploads', 'clip_id')
    # ### end Alembic commands ###
