import boto3
from botocore.config import Config
from botocore.exceptions import NoCredentialsError, SSLError
from flask import current_app
import uuid
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upload_to_s3(file, album_id):  # 移除acl参数
    """上传文件到AWS S3并返回URL"""
    # 生成唯一文件名
    filename = f"album_{album_id}_{uuid.uuid4()}_{os.path.basename(file.filename)}"
    s3_key = f"memories/{filename}"

    # 验证配置
    required_configs = ['S3_REGION', 'AWS_ACCESS_KEY', 'AWS_SECRET_KEY', 'S3_BUCKET']
    missing_configs = [cfg for cfg in required_configs if not current_app.config.get(cfg)]
    if missing_configs:
        logger.error(f"Missing S3 configurations: {', '.join(missing_configs)}")
        return None

    try:
        # 配置S3客户端
        s3_config = Config(
            region_name=current_app.config['S3_REGION'],
            retries={
                'max_attempts': 10,
                'mode': 'standard'
            },
            connect_timeout=5,
            read_timeout=10,
            signature_version='s3v4'
        )

        # 初始化S3客户端
        s3 = boto3.client(
            's3',
            region_name=current_app.config['S3_REGION'],
            aws_access_key_id=current_app.config['AWS_ACCESS_KEY'],
            aws_secret_access_key=current_app.config['AWS_SECRET_KEY'],
            config=s3_config
        )

        logger.info(f"Uploading to S3: bucket={current_app.config['S3_BUCKET']}, key={s3_key}, region={current_app.config['S3_REGION']}")

        # 上传文件
        s3.upload_fileobj(
            file,
            current_app.config['S3_BUCKET'],
            s3_key,
            ExtraArgs={
                # 'ACL': acl,  # 删除这一行
                'ContentType': file.content_type
            }
        )

        # 生成正确的URL
        url = f"https://{current_app.config['S3_BUCKET']}.s3.{current_app.config['S3_REGION']}.amazonaws.com/{s3_key}"
        logger.info(f"File uploaded successfully: {url}")
        return url

    except SSLError as e:
        logger.error(f"SSL Error: {str(e)}")
        logger.error("Possible causes: incorrect region, network proxy, or SSL certificate issues")
        return None
    except NoCredentialsError:
        logger.error("AWS credentials not found")
        return None
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {str(e)}")
        return None

# 添加S3文件删除功能
def delete_from_s3(s3_url):
    """从S3删除文件"""
    try:
        # 解析S3 URL获取bucket和key
        # URL格式: https://bucket.s3.region.amazonaws.com/key
        parsed_url = urlparse(s3_url)
        bucket = parsed_url.netloc.split('.')[0]
        s3_key = parsed_url.path.lstrip('/')

        # 配置S3客户端
        s3_config = Config(
            region_name=current_app.config['S3_REGION'],
            retries={
                'max_attempts': 10,
                'mode': 'standard'
            },
            connect_timeout=5,
            read_timeout=10,
            signature_version='s3v4'
        )

        # 初始化S3客户端
        s3 = boto3.client(
            's3',
            region_name=current_app.config['S3_REGION'],
            aws_access_key_id=current_app.config['AWS_ACCESS_KEY'],
            aws_secret_access_key=current_app.config['AWS_SECRET_KEY'],
            config=s3_config
        )

        # 删除S3对象
        s3.delete_object(Bucket=bucket, Key=s3_key)
        logger.info(f"File deleted successfully from S3: {s3_url}")
        return True

    except Exception as e:
        logger.error(f"Error deleting file from S3: {str(e)}")
        return False

# 添加导入语句
from urllib.parse import urlparse