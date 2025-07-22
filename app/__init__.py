from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_compress import Compress  # 导入压缩扩展
from app.config import Config

# 从独立模块导入db
from app.models.db import db

# 全局扩展实例
migrate = Migrate()
login_manager = LoginManager()
# 添加CSRF实例
csrf = CSRFProtect()
login_manager.login_view = 'auth.login'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化压缩扩展
    Compress(app)
    
    # 绑定扩展到应用
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    # 恢复CSRF初始化
    csrf.init_app(app)

    # 注册蓝图
    from app.routes.auth import auth
    from app.routes.main import main
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(main)

    # 用户加载回调（必须有）
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    # 延迟导入模型以避免循环依赖
    with app.app_context():
        from app.models.user import User, Announcement  # 确保导入Announcement
        db.create_all()

    return app  # 确保返回应用实例
