from alembic import op
from app.settings import ROOT
revision='0002_audit'
down_revision='0001_core'
def upgrade():
    op.get_bind().connection.driver_connection.execute((ROOT/'db/audit.sql').read_text())
def downgrade():
    raise RuntimeError('Audit history is immutable.')
