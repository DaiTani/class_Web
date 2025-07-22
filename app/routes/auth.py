from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user, logout_user
from app.models.user import User
from app import db
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.utils.s3_upload import upload_to_s3, delete_from_s3
import os
import uuid

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('auth/login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    # 在函数内部导入所需模块
    from app.models.user import User
    from app import db
    
    email = request.form.get('email').lower()  # 添加.lower()统一转为小写
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    # 原代码：if not user or not check_password_hash(user.password_hash, password):
    if not user or not user.check_password(password):  # 使用模型方法
        flash('请检查您的登录信息并重试。')
        return redirect(url_for('auth.login'))

    login_user(user, remember=remember)
    return redirect(url_for('main.index'))

@auth.route('/register')
def register():
    return render_template('auth/register.html')

@auth.route('/register', methods=['POST'])
def register_post():
    # 在函数内部导入所需模块
    from app.models.user import User
    from app import db
    
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    user = User.query.filter_by(email=email).first()
    if user:
        flash('该邮箱已被注册，请使用其他邮箱。')
        return redirect(url_for('auth.register'))

    if password != confirm_password:
        flash('两次输入的密码不一致，请重试。')
        return redirect(url_for('auth.register'))

    # 修改注册用户代码（约第56行）
    new_user = User(email=email, name=username)  # 将 username 参数改为 name
    new_user.set_password(password)  # 使用模型中的set_password方法

    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth.route('/profile')
@login_required
def profile():
    # 添加user=current_user参数
    return render_template('auth/profile.html', user=current_user)

@auth.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        # 处理头像上传
        if 'avatar' in request.files and request.files['avatar'].filename:
            avatar_file = request.files['avatar']
            # 生成唯一文件名
            filename = f"avatars/{uuid.uuid4()}_{avatar_file.filename}"
            # 上传到S3
            try:
                # 删除旧头像（如果存在）
                if current_user.avatar_url:
                    delete_from_s3(current_user.avatar_url)
                # 上传新头像
                current_user.avatar_url = upload_to_s3(avatar_file, filename)
            except Exception as e:
                flash(f'头像上传失败: {str(e)}', 'danger')
                return redirect(url_for('auth.edit_profile'))

        # 更新用户信息
        current_user.name = form.name.data
        current_user.email = form.email.data
        if form.password.data:
            current_user.set_password(form.password.data)
        db.session.commit()
        flash('个人资料已更新', 'success')
        return redirect(url_for('auth.profile'))
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email
    # 修改render_template调用，添加user参数
    return render_template('auth/edit_profile.html', form=form, user=current_user)
from app.forms import LoginForm, RegistrationForm, EditProfileForm  # 添加此行导入新表单
from werkzeug.security import generate_password_hash
import uuid