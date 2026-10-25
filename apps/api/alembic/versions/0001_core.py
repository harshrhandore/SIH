from alembic import op
from app.settings import ROOT
revision='0001_core'
down_revision=None
def upgrade():
    op.get_bind().connection.driver_connection.execute((ROOT/'db/core.sql').read_text())
def downgrade():
    raise RuntimeError('Use the guarded owner-only synthetic reset; no destructive automatic downgrade.')
