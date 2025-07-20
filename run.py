import os
from app import create_app, db
from app.config import config  # 导入配置字典

# 获取环境变量并从配置字典中获取对应配置类
config_name = os.getenv('FLASK_ENV', 'default')
app = create_app(config[config_name])  # 使用配置类而非字符串

@app.shell_context_processor
def make_shell_context():
    return {'db': db}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)