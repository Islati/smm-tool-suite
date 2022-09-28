"""empty message

Revision ID: 3680754c1180
Revises: b9d2c98e48e9
Create Date: 2022-09-17 22:45:49.061461

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3680754c1180'
down_revision = 'b9d2c98e48e9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('published_social_media_posts',
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.Column('updated_at', sa.DateTime(), nullable=False),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('platform', sa.Text(), nullable=False),
                    sa.Column('social_media_post_id', sa.Integer(), nullable=False),
                    sa.Column('post_url', sa.Text(), nullable=True),
                    sa.ForeignKeyConstraint(['social_media_post_id'], ['social_media_posts.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.add_column('social_media_posts', sa.Column('platforms', sa.Text(), nullable=False, server_default=''))
    op.add_column('social_media_posts', sa.Column('title', sa.Text(), nullable=True))
    op.add_column('social_media_posts', sa.Column('description', sa.Text(), nullable=True))
    op.alter_column('social_media_posts', 'api_id',
                    existing_type=sa.TEXT(),
                    nullable=True)
    op.execute('UPDATE social_media_posts SET platforms=platform')
    op.drop_column('social_media_posts', 'platform')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('social_media_posts', sa.Column('platform', sa.TEXT(), autoincrement=False, nullable=False))
    op.alter_column('social_media_posts', 'api_id',
                    existing_type=sa.TEXT(),
                    nullable=False)
    op.drop_column('social_media_posts', 'description')
    op.drop_column('social_media_posts', 'title')
    op.drop_column('social_media_posts', 'platforms')
    op.drop_table('published_social_media_posts')
    # ### end Alembic commands ###
