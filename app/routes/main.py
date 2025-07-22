from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.user import Post, db
from flask_login import login_required, current_user
from flask import current_app
from app.models.user import Post, Comment, User, Like, db  # 添加Like导入
from datetime import datetime, timedelta  # 确保已导入datetime
from app.models.user import User, Announcement  
from app import db
from app.models.user import db, Post, Comment, Like, Announcement, User, Album, Photo  # 添加Album和Photo
from app.utils.s3_upload import upload_to_s3, delete_from_s3  # 导入S3上传函数
import os
from werkzeug.utils import secure_filename
from app import csrf

main = Blueprint('main', __name__)

# 添加用户活动跟踪钩子
@main.before_app_request
def update_last_seen():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

@main.route('/')
def index():
    # 动态计算5分钟内活跃的用户数
    online_count = User.query.filter(
        User.last_seen >= datetime.utcnow() - timedelta(minutes=5)
    ).count()
    announcements = Announcement.query.order_by(Announcement.timestamp.desc()).limit(2).all()
    return render_template('main/index.html', online_count=online_count, announcements=announcements)

@main.route('/forum')
def forum():
    # 获取分页参数，默认为第1页，每页10条
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 获取分类筛选参数
    selected_category = request.args.get('category', 'all')
    # 获取排序参数，默认为按时间排序
    sort_by = request.args.get('sort_by', 'created_at')
    
    # 分离置顶帖子和普通帖子查询
    sticky_posts = Post.query.filter_by(is_sticky=True)
    regular_posts_query = Post.query.filter_by(is_sticky=False)
    
    # 应用分类筛选
    if selected_category != 'all':
        sticky_posts = sticky_posts.filter_by(category=selected_category)
        regular_posts_query = regular_posts_query.filter_by(category=selected_category)
    
    # 排序：置顶帖按更新时间降序
    sticky_posts = sticky_posts.order_by(Post.updated_at.desc()).all()
    
    # 根据参数对普通帖进行排序
    if sort_by == 'view_count':
        regular_posts_query = regular_posts_query.order_by(Post.view_count.desc())
    else:
        regular_posts_query = regular_posts_query.order_by(Post.created_at.desc())
    
    # 应用分页
    regular_posts_paginated = regular_posts_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # 合并结果：置顶帖在前，分页的普通帖在后
    posts = sticky_posts + regular_posts_paginated.items
    
    # 获取所有可用分类（用于筛选下拉框）
    categories = db.session.query(Post.category).distinct().all()
    categories = [c[0] for c in categories]  # 提取分类名称
    
    # 添加默认分类（如果数据库中没有分类）
    if not categories:
        categories = ['学习交流', '资源共享', '活动组织', '问题求助', '创意分享']
    return render_template('main/forum.html', 
                          posts=posts, 
                          selected_category=selected_category, 
                          categories=categories, 
                          sort_by=sort_by, 
                          pagination=regular_posts_paginated)  # 传递分页对象

@main.route('/memories')
def memories():
    # 获取所有相册
    albums = Album.query.order_by(Album.created_at.desc()).all()
    return render_template('main/memories.html', albums=albums)

@main.route('/memories/create_album', methods=['GET', 'POST'])
@login_required
def create_album():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        files = request.files.getlist('photos')

        if not title or not files or all(f.filename == '' for f in files):
            flash('标题和照片不能为空', 'danger')
            return redirect(url_for('main.memories'))

        # 创建相册
        album = Album(
            title=title,
            description=description,
            author_id=current_user.id
        )
        db.session.add(album)
        db.session.flush()  # 获取album.id但不提交事务

        # 上传照片到S3并保存到数据库
        for file in files:
            if file and allowed_file(file.filename):
                s3_url = upload_to_s3(file, album.id)
                if s3_url:
                    photo = Photo(
                        album_id=album.id,
                        s3_url=s3_url,
                        filename=secure_filename(file.filename),
                        caption=request.form.get(f'caption_{file.filename}', '')
                    )
                    db.session.add(photo)
                else:
                    flash('照片上传失败，请检查AWS S3配置', 'danger')
                    db.session.rollback()
                    return redirect(url_for('main.memories'))

        db.session.commit()
        flash('相册创建成功', 'success')
        return redirect(url_for('main.memories'))

    return render_template('main/create_album.html')

# 添加允许的文件类型检查
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/about')
def about():
    # 查询真实数据
    member_count = User.query.count()
    post_count = Post.query.count()
    # 注意：回忆照片和班级活动需要创建对应的模型后才能查询
    photo_count = Photo.query.count()  # 动态获取所有照片总数
    activity_count = 0  # 临时值，需创建Activity模型
    return render_template('main/about.html', 
                          member_count=member_count,
                          post_count=post_count,
                          photo_count=photo_count,
                          activity_count=activity_count)

# 添加帖子详情路由
@main.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    # 增加浏览量计数
    post.view_count += 1
    db.session.commit()
    return render_template('main/post_detail.html', post=post)

@main.route('/create_post', methods=['POST'])
@login_required
def create_post():
    # 1. 验证权限
    if not current_user.is_authenticated:
        flash('请先登录', 'danger')
        return redirect(url_for('auth.login'))
    
    # 2. 获取表单数据
    title = request.form.get('title')
    content = request.form.get('content')
    category = request.form.get('category', 'default')
    
    # 3. 验证数据
    if not title or not content:
        flash('标题和内容不能为空', 'danger')
        return redirect(url_for('main.forum'))
    
    # 4. 业务逻辑处理
    try:
        post = Post(title=title, content=content, 
                   author_id=current_user.id, category=category)
        db.session.add(post)
        db.session.commit()
        flash('帖子发布成功', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'发布帖子失败: {str(e)}')
        flash(f'发布帖子失败: {str(e)}', 'danger')
    
    # 5. 确保返回响应
    return redirect(url_for('main.forum'))

@main.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content')
    if content:
        comment = Comment(content=content, author=current_user, post=post)
        db.session.add(comment)
        db.session.commit()
        flash('评论已发布!', 'success')
    return redirect(url_for('main.post_detail', post_id=post_id))

@main.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # 检查权限
    if post.author_id != current_user.id:
        flash('没有权限删除此帖子', 'danger')
        return redirect(url_for('main.forum'))
    
    try:
        # 先删除帖子的直接点赞
        Like.query.filter_by(post_id=post_id).delete(synchronize_session=False)
        
        # 再删除帖子相关评论的点赞
        Like.query.filter(Like.comment_id.in_(
            db.session.query(Comment.id).filter_by(post_id=post_id)
        )).delete(synchronize_session=False)
        
        # 再删除帖子相关评论
        Comment.query.filter_by(post_id=post_id).delete()
        
        # 最后删除帖子
        db.session.delete(post)
        db.session.commit()
        flash('帖子已成功删除', 'success')
        return redirect(url_for('main.forum'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'删除帖子失败: {str(e)}')
        flash(f'删除失败: {str(e)}', 'danger')
        return redirect(url_for('main.post_detail', post_id=post_id))

@main.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    # 检查权限
    if comment.author_id != current_user.id:
        flash('没有权限删除此评论', 'danger')
        return redirect(url_for('main.post_detail', post_id=comment.post_id))
    
    # 删除评论相关的点赞
    Like.query.filter_by(comment_id=comment_id).delete()
    
    # 删除评论
    db.session.delete(comment)
    db.session.commit()
    
    flash('评论已成功删除', 'success')
    return redirect(url_for('main.post_detail', post_id=comment.post_id))

@main.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    
    if like:
        # 取消点赞
        db.session.delete(like)
        post.like_count -= 1
        action = 'unliked'
    else:
        # 添加点赞
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        post.like_count += 1
        action = 'liked'
    
    db.session.commit()
    # 返回JSON响应而非重定向
    return jsonify({
        'status': 'success',
        'action': action,
        'like_count': post.like_count
    })
    return redirect(url_for('main.post_detail', post_id=post_id))

@main.route('/comment/<int:comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    like = Like.query.filter_by(user_id=current_user.id, comment_id=comment_id).first()
    
    if like:
        # 取消点赞
        db.session.delete(like)
        comment.like_count -= 1
        action = 'unliked'
    else:
        # 添加点赞
        like = Like(user_id=current_user.id, comment_id=comment_id)
        db.session.add(like)
        comment.like_count += 1
        action = 'liked'
    
    db.session.commit()
    # 返回JSON响应而非重定向
    return jsonify({
        'status': 'success',
        'action': action,
        'like_count': comment.like_count
    })
    return redirect(url_for('main.post_detail', post_id=comment.post_id))

@main.route('/post/<int:post_id>/toggle_sticky', methods=['POST'])
@login_required
# 删除此处的导入语句
# from flask_wtf.csrf import validate_csrf, ValidationError
# from flask import current_app
def toggle_sticky(post_id):
    # 将导入移至函数内部
    from flask_wtf.csrf import validate_csrf, ValidationError
    from flask import current_app
    
    csrf_token_header = request.headers.get('X-CSRFToken')
    csrf_token_form = request.form.get('csrf_token')
    current_app.logger.info(f"CSRF调试: 头令牌={csrf_token_header}, 表单令牌={csrf_token_form}")
    
    try:
        # 优先验证请求头令牌，其次验证表单令牌
        validate_csrf(csrf_token_header or csrf_token_form)
    except ValidationError as e:
        current_app.logger.error(f"CSRF验证失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'CSRF令牌验证失败'}), 400
    
    # 检查是否为管理员
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': '只有管理员可以设置置顶帖子'}), 403
    
    post = Post.query.get_or_404(post_id)
    # 切换置顶状态
    post.is_sticky = not post.is_sticky
    # 更新帖子的更新时间
    post.updated_at = datetime.utcnow()
    db.session.commit()
    
    status = '置顶' if post.is_sticky else '取消置顶'
    return jsonify({
        'status': 'success', 
        'message': f'帖子已成功{status}',
        'is_sticky': post.is_sticky
    })
    return redirect(url_for('main.forum'))

# 分类管理路由 - 开始
@main.route('/admin/categories')
@login_required
def manage_categories():
    # 检查管理员权限
    if not current_user.is_admin:
        flash('只有管理员可以管理分类', 'danger')
        return redirect(url_for('main.forum'))
    
    # 获取所有分类及对应帖子数量
    categories = db.session.query(
        Post.category,
        db.func.count(Post.id).label('post_count')
    ).group_by(Post.category).all()
    
    return render_template('main/manage_categories.html', categories=categories)

@main.route('/admin/categories/add', methods=['POST'])
@login_required
def add_category():
    if not current_user.is_admin:
        flash('只有管理员可以添加分类', 'danger')
        return redirect(url_for('main.forum'))
    
    # 获取表单提交的分类名称
    category_name = request.form.get('category_name', '').strip()
    
    # 验证分类名称
    if not category_name:
        flash('分类名称不能为空', 'danger')
        return redirect(url_for('main.manage_categories'))
    
    # 检查分类是否已存在
    existing_category = db.session.query(Post.category).filter_by(category=category_name).first()
    if existing_category:
        flash('该分类已存在', 'danger')
        return redirect(url_for('main.manage_categories'))
    
    # 添加新分类（通过创建一个临时帖子来初始化分类，或直接使用分类表）
    # 注意：这里假设使用Post模型的category字段作为分类存储
    # 如果有专门的Category模型，应该使用该模型添加
    temp_post = Post(
        title=f'初始化分类: {category_name}',
        content='此帖子用于初始化分类，可安全删除',
        author_id=current_user.id,
        category=category_name,
        is_sticky=False
    )
    db.session.add(temp_post)
    db.session.commit()
    
    flash('分类添加成功', 'success')
    return redirect(url_for('main.manage_categories'))

# 公告管理路由
@main.route('/admin/announcements')
@login_required
def manage_announcements():
    if not current_user.is_admin:
        flash('无权限访问管理页面', 'danger')
        return redirect(url_for('main.index'))
    announcements = Announcement.query.order_by(Announcement.timestamp.desc()).all()
    return render_template('main/manage_announcements.html', announcements=announcements)

@main.route('/admin/announcements/add', methods=['GET', 'POST'])
@login_required
def add_announcement():
    if not current_user.is_admin:
        flash('无权限添加公告', 'danger')
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        if not title or not content:
            flash('标题和内容不能为空', 'warning')
            return redirect(url_for('main.add_announcement'))
        announcement = Announcement(
            title=title,
            content=content,
            author_id=current_user.id
        )
        db.session.add(announcement)
        db.session.commit()
        flash('公告添加成功', 'success')
        return redirect(url_for('main.manage_announcements'))
    return render_template('main/add_announcement.html')

@main.route('/admin/announcements/delete/<int:ann_id>')
@login_required
def delete_announcement(ann_id):
    if not current_user.is_admin:
        flash('无权限删除公告', 'danger')
        return redirect(url_for('main.index'))
    announcement = Announcement.query.get_or_404(ann_id)
    db.session.delete(announcement)
    db.session.commit()
    flash('公告已删除', 'success')
    return redirect(url_for('main.manage_announcements'))
@main.route('/admin/categories/edit/<old_category>', methods=['POST'])
@login_required
def edit_category(old_category):
    if not current_user.is_admin:
        flash('只有管理员可以编辑分类', 'danger')
        return redirect(url_for('main.forum'))
    
    new_category = request.form.get('new_category_name', '').strip()
    if not new_category:
        flash('分类名称不能为空', 'danger')
        return redirect(url_for('main.manage_categories'))
    
    # 更新所有使用旧分类的帖子
    posts = Post.query.filter_by(category=old_category).all()
    for post in posts:
        post.category = new_category
    
    db.session.commit()
    flash(f'分类 "{old_category}" 已更新为 "{new_category}"', 'success')
    return redirect(url_for('main.manage_categories'))

@main.route('/admin/categories/delete/<category>', methods=['POST'])
@login_required
def delete_category(category):
    if not current_user.is_admin:
        flash('只有管理员可以删除分类', 'danger')
        return redirect(url_for('main.forum'))
    
    # 获取该分类下的帖子数量
    post_count = Post.query.filter_by(category=category).count()
    if post_count > 0:
        # 提供分类迁移选项
        new_category = request.form.get('migrate_category')
        if not new_category or new_category == category:
            flash('请选择迁移目标分类', 'danger')
            return redirect(url_for('main.manage_categories'))
        
        # 将帖子迁移到新分类
        posts = Post.query.filter_by(category=category).all()
        for post in posts:
            post.category = new_category
        
        db.session.commit()
        flash(f'分类 "{category}" 下的 {post_count} 个帖子已迁移至 "{new_category}"', 'success')
    
    flash(f'分类 "{category}" 已删除', 'success')
    return redirect(url_for('main.manage_categories'))
# 分类管理路由 - 结束

# 添加相册详情路由
@main.route('/memories/album/<int:album_id>')
def album_detail(album_id):
    album = Album.query.get_or_404(album_id)
    all_albums = Album.query.all()
    # 创建表单实例并设置选项
    form = MovePhotoForm()
    form.target_album_id.choices = [(a.id, a.title) for a in all_albums if a.id != album_id]
    return render_template('main/album_detail.html', album=album, all_albums=all_albums, form=form)

# 添加照片上传路由
from flask_wtf import FlaskForm
from wtforms import FileField, StringField, SubmitField
from wtforms.validators import DataRequired

# 添加照片上传表单
class PhotoUploadForm(FlaskForm):
    photo = FileField('照片', validators=[DataRequired()])
    caption = StringField('照片描述')
    submit = SubmitField('上传照片')

# 添加照片上传路由
@main.route('/memories/album/<int:album_id>/upload', methods=['GET', 'POST'])
@login_required
def upload_photo(album_id):
    album = Album.query.get_or_404(album_id)
    form = PhotoUploadForm()  # 初始化表单
    
    if form.validate_on_submit():
        file = form.photo.data
        caption = form.caption.data
        
        if file and allowed_file(file.filename):
            s3_url = upload_to_s3(file, album_id)
            if s3_url:
                photo = Photo(
                    album_id=album.id,
                    s3_url=s3_url,
                    filename=secure_filename(file.filename),
                    caption=caption
                )
                db.session.add(photo)
                db.session.commit()
                flash('照片上传成功', 'success')
                return redirect(url_for('main.album_detail', album_id=album.id))
            else:
                flash('照片上传失败，请检查文件格式', 'danger')
    
    return render_template('main/upload_photo.html', album=album, form=form)  # 传递表单实例

# 添加删除相册路由
@main.route('/admin/albums/delete/<int:album_id>', methods=['POST'])
@login_required
def delete_album(album_id):
    if not current_user.is_admin:
        flash('只有管理员可以删除相册', 'danger')
        return redirect(url_for('main.memories'))

    album = Album.query.get_or_404(album_id)
    
    try:
        # 删除相册中的所有照片
        for photo in album.photos:
            # 从S3删除照片
            try:
                delete_from_s3(photo.s3_url)
            except Exception as e:
                logger.warning(f"忽略S3删除错误: {str(e)}")
            db.session.delete(photo)
        
        # 删除相册
        db.session.delete(album)
        db.session.commit()
        flash('相册已成功删除', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'删除相册失败: {str(e)}')
        flash(f'删除相册失败: {str(e)}', 'danger')
    
    return redirect(url_for('main.memories'))  # 确保始终返回响应

# 添加删除照片路由
@main.route('/admin/photos/delete/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    if not current_user.is_admin:
        flash('只有管理员可以删除照片', 'danger')
        return jsonify({'status': 'error', 'message': '权限不足'}), 403

    photo = Photo.query.get_or_404(photo_id)
    album_id = photo.album_id
    
    # 从S3删除照片
    if delete_from_s3(photo.s3_url):
        # 从数据库删除照片记录
        db.session.delete(photo)
        db.session.commit()
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': '删除S3文件失败'}), 500

# 添加移动照片路由
@main.route('/admin/photos/move', methods=['POST'])
@login_required
def move_photo():
    # 获取所有相册用于表单选项
    all_albums = Album.query.all()
    form = MovePhotoForm()
    # 为目标相册字段设置选项
    form.target_album_id.choices = [(a.id, a.title) for a in all_albums]
    
    # 验证表单和CSRF令牌
    if not form.validate_on_submit():
        current_app.logger.error('表单验证失败: %s', form.errors)
        return jsonify({'status': 'error', 'message': '表单验证失败', 'errors': form.errors}), 400
    
    if not current_user.is_admin:
        flash('只有管理员可以移动照片', 'danger')
        return redirect(url_for('main.memories'))

    photo = Photo.query.get_or_404(form.photo_id.data)
    target_album = Album.query.get_or_404(form.target_album_id.data)
    
    # 保存原相册ID用于重定向
    original_album_id = photo.album_id
    
    # 更新照片的相册ID
    photo.album_id = target_album.id
    db.session.commit()
    
    flash('照片已成功移动到相册《{}》'.format(target_album.title), 'success')
    # 使用原相册ID重定向，保持在原相册页面
    return redirect(url_for('main.album_detail', album_id=original_album_id))
from flask_wtf import FlaskForm
from wtforms import HiddenField, SelectField
from wtforms.validators import DataRequired

# 添加移动照片表单类
class MovePhotoForm(FlaskForm):
    photo_id = HiddenField('Photo ID', validators=[DataRequired()])
    target_album_id = SelectField('Target Album', validators=[DataRequired()])