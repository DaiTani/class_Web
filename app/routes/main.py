from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.user import Post, db
from flask_login import login_required, current_user
from app.models.user import Post, Comment, User, Like, db  # 添加Like导入
from datetime import datetime  # 确保已导入datetime
from app.models.user import User, Announcement  
from app import db

main = Blueprint('main', __name__)

@main.route('/')
def index():
    # 模拟在线用户数量
    online_count = 12 if current_user.is_authenticated else 11
    # 获取最新的两条公告
    announcements = Announcement.query.order_by(Announcement.timestamp.desc()).limit(2).all()
    return render_template('main/index.html', online_count=online_count, announcements=announcements)

@main.route('/forum')
def forum():
    # 获取分类筛选参数
    selected_category = request.args.get('category', 'all')
    
    # 分离置顶帖子和普通帖子查询
    sticky_posts = Post.query.filter_by(is_sticky=True)
    regular_posts = Post.query.filter_by(is_sticky=False)
    
    # 应用分类筛选（如果选择了特定分类）
    if selected_category != 'all':
        sticky_posts = sticky_posts.filter_by(category=selected_category)
        regular_posts = regular_posts.filter_by(category=selected_category)
    
    # 排序：置顶帖按更新时间降序，普通帖按创建时间降序
    sticky_posts = sticky_posts.order_by(Post.updated_at.desc()).all()
    regular_posts = regular_posts.order_by(Post.created_at.desc()).all()
    
    # 合并结果：置顶帖在前，普通帖在后
    posts = sticky_posts + regular_posts
    
    # 获取所有可用分类（用于筛选下拉框）
    categories = db.session.query(Post.category).distinct().all()
    categories = [c[0] for c in categories]  # 提取分类名称
    
    # 添加默认分类（如果数据库中没有分类）
    if not categories:
        categories = ['学习交流', '资源共享', '活动组织', '问题求助', '创意分享']
    return render_template('main/forum.html', 
                          posts=posts, 
                          selected_category=selected_category, 
                          categories=categories)  # 传递分类数据

@main.route('/memories')
def memories():
    return render_template('main/memories.html')

@main.route('/about')
def about():
    # 查询真实数据
    member_count = User.query.count()
    post_count = Post.query.count()
    # 注意：回忆照片和班级活动需要创建对应的模型后才能查询
    photo_count = 0  # 临时值，需创建Photo模型
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
    title = request.form.get('title')
    content = request.form.get('content')
    # 获取分类参数（默认为'default'）
    category = request.form.get('category', 'default')
    
    if not title or not content:
        flash('标题和内容不能为空', 'danger')
        return redirect(url_for('main.forum'))
    
    # 创建帖子时包含分类信息
    post = Post(title=title, content=content, 
               author_id=current_user.id, category=category)
    db.session.add(post)
    db.session.commit()
    
    flash('帖子发布成功', 'success')
    return redirect(url_for('main.forum'))

@main.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content')
    
    if content:
        comment = Comment(content=content, post_id=post_id, author_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        flash('评论成功', 'success')
    
    return redirect(url_for('main.post_detail', post_id=post_id))

@main.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # 检查权限
    if post.author_id != current_user.id:
        flash('没有权限删除此帖子', 'danger')
        return redirect(url_for('main.forum'))
    
    # 先删除帖子相关评论的点赞
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
def toggle_sticky(post_id):
    # 检查是否为管理员
    if not current_user.is_admin:
        flash('只有管理员可以设置置顶帖子', 'danger')
        return redirect(url_for('main.forum'))
    
    post = Post.query.get_or_404(post_id)
    # 切换置顶状态
    post.is_sticky = not post.is_sticky
    # 更新帖子的更新时间
    post.updated_at = datetime.utcnow()
    db.session.commit()
    
    status = '置顶' if post.is_sticky else '取消置顶'
    flash(f'帖子已成功{status}', 'success')
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