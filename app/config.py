import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 确保此文件只包含以下内容
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    # 合并数据库连接配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'connect_args': {
            'timeout': 10,
        }
    }
    # 修正数据库连接字符串为MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://username:password@localhost:3306/class_web?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 移除不支持的timeout参数
    # 添加数据库连接池配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_recycle': 1800,
        # 'timeout': 10,  # 注释掉或删除这一行
    }
    # 添加 S3 区域配置
    S3_REGION = os.getenv('S3_REGION', 'eu-north-1')  # 提供默认区域值
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY', '')
    AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY', '')
    S3_BUCKET = os.getenv('S3_BUCKET', '')

# 以下为可选配置（根据需要保留）
class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # 生产环境密钥应从环境变量获取
    # import os
    # SECRET_KEY = os.environ.get('SECRET_KEY')

# 配置字典，便于切换环境
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}