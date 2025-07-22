import os
import boto3
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化S3客户端
try:
    s3 = boto3.client(
        's3',
        region_name=os.getenv('S3_REGION'),
        aws_access_key_id=os.getenv('S3_KEY'),
        aws_secret_access_key=os.getenv('S3_SECRET')
    )
    print("S3客户端初始化成功！")
    # 测试上传文件
    test_file = 'test_upload.jpg'
    with open(test_file, 'wb') as f:
        f.write(b'Hello S3 Test')  # 创建临时测试文件
        
    s3.upload_file(
        test_file,
        os.getenv('S3_BUCKET'),
        f'test/{test_file}',
        ExtraArgs={'ContentType': 'image/jpeg'}
    )
    print(f"测试文件上传成功: https://{os.getenv('S3_BUCKET')}.s3.{os.getenv('S3_REGION')}.amazonaws.com/test/{test_file}")
except Exception as e:
    print(f"测试失败: {str(e)}")