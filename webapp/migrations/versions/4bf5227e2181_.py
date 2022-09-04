"""empty message

Revision ID: 4bf5227e2181
Revises: 15963450ce1a
Create Date: 2022-09-04 19:09:39.389766

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4bf5227e2181'
down_revision = '15963450ce1a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('social_media_posts', sa.Column('post_time', sa.Text(), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('social_media_posts', 'post_time')
    # ### end Alembic commands ###
