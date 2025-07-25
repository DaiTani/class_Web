from app.models.db import db  # 从独立模块导入db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime  # 正确导入datetime类

# 添加帖子模型
class Post(db.Model):
    __tablename__ = 'post'
    __table_args__ = (
        db.Index('idx_post_category', 'category'),
        db.Index('idx_post_created_at', 'created_at'),
        db.Index('idx_post_view_count', 'view_count'),
        db.Index('idx_post_is_sticky', 'is_sticky'),
        {'extend_existing': True}
    )
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('posts', lazy=True))
    like_count = db.Column(db.Integer, default=0)  # 确保已添加点赞数字段
    # 百度贴吧风格扩展字段
    category = db.Column(db.String(50), nullable=False, default='default')  # 帖子分类
    is_sticky = db.Column(db.Boolean, default=False)  # 是否置顶
    view_count = db.Column(db.Integer, default=0)  # 浏览量
    
    @property
    def local_created_at(self):
        """将UTC时间转换为本地时间（根据配置的时区偏移）"""
        from datetime import timezone, timedelta
        from flask import current_app
        tz_offset = current_app.config.get('TIMEZONE_OFFSET', 8)
        # 先将naive的UTC时间转换为aware的UTC时间
        utc_aware = self.created_at.replace(tzinfo=timezone.utc)
        # 再转换到目标时区
        return utc_aware.astimezone(timezone(timedelta(hours=tz_offset)))

# 添加评论模型
class Comment(db.Model):
    __tablename__ = 'comment'
    __table_args__ = (
        db.Index('idx_comment_post_id', 'post_id'),
        db.Index('idx_comment_created_at', 'created_at'),
        {'extend_existing': True}
    )
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post = db.relationship('Post', backref=db.backref('comments', lazy=True))
    author = db.relationship('User', backref=db.backref('comments', lazy=True))
    like_count = db.Column(db.Integer, default=0)  # 确保已添加点赞数字段
    
    @property
    def local_created_at(self):
        """将UTC时间转换为本地时间（根据配置的时区偏移）"""
        from datetime import timezone, timedelta
        from flask import current_app
        tz_offset = current_app.config.get('TIMEZONE_OFFSET', 8)
        # 先将naive的UTC时间转换为aware的UTC时间
        utc_aware = self.created_at.replace(tzinfo=timezone.utc)
        # 再转换到目标时区
        return utc_aware.astimezone(timezone(timedelta(hours=tz_offset)))

# 添加点赞模型
class Like(db.Model):  # 新增的Like模型也需要添加
    __tablename__ = 'like'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # 缺少级联删除配置
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete='CASCADE'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),
        db.UniqueConstraint('user_id', 'comment_id', name='unique_user_comment_like'),
        {'extend_existing': True}
    )

# 添加公告模型
class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', backref=db.backref('announcements', lazy=True))

# 添加相册模型
class Album(db.Model):
    __tablename__ = 'album'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('albums', lazy=True))
    photos = db.relationship('Photo', backref='album', lazy=True, cascade='all, delete-orphan')

# 添加照片模型
class Photo(db.Model):
    __tablename__ = 'photo'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    album_id = db.Column(db.Integer, db.ForeignKey('album.id'), nullable=False)
    s3_url = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    caption = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 移除email字段，添加student_id作为登录凭证
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    nickname = db.Column(db.String(64), nullable=False)  # 将name改为nickname
    # 添加新字段
    id_card = db.Column(db.String(20))  # 身份证号
    is_active = db.Column(db.Integer, default=0)  # 0-未激活, 1-激活
    role = db.Column(db.String(20), default='guest')  # guest/student/admin/super_admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)  # 添加此行跟踪最后活动时间

    def set_password(self, password):
        # 显式指定算法
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.nickname}>'  # 更新__repr__方法