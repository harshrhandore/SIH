from alembic import op
from app.settings import ROOT
revision='0003_views'
down_revision='0002_audit'
def upgrade():
    op.get_bind().connection.driver_connection.execute((ROOT/'db/views.sql').read_text())
def downgrade():
    raise RuntimeError('Use a reviewed offline migration.')
