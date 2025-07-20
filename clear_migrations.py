from app import create_app
from app.models.db import db
from alembic import op
import sqlalchemy as sa

app = create_app()
with app.app_context():
    # 清除alembic_version表中的所有记录
    conn = db.engine.connect()
    conn.execute(sa.text("DELETE FROM alembic_version"))
    conn.commit()
    print("迁移历史已成功清除")