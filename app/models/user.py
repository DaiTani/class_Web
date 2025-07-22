from app.models.db import db  # 从独立模块导入db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime  # 正确导入datetime类

# 添加帖子模型
class Post(db.Model):
    __tablename__ = 'post'
    __table_args__ = {'extend_existing': True}  # 必须添加此行
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

# 添加评论模型
class Comment(db.Model):
    __tablename__ = 'comment'
    __table_args__ = {'extend_existing': True}  # 必须添加此行
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post = db.relationship('Post', backref=db.backref('comments', lazy=True))
    author = db.relationship('User', backref=db.backref('comments', lazy=True))
    like_count = db.Column(db.Integer, default=0)  # 确保已添加点赞数字段

# 添加点赞模型
class Like(db.Model):  # 新增的Like模型也需要添加
    __tablename__ = 'like'
    __table_args__ = {'extend_existing': True}  # Must add this line
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure unique constraints are added
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
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 现在可以正确调用utcnow()
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        # 显式指定算法
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.name}>'