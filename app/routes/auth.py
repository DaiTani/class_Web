from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user, logout_user
from app.models.user import User
from app import db
from app.utils.s3_upload import upload_to_s3, delete_from_s3
import os
import uuid
from app.forms import LoginForm, RegistrationForm, EditProfileForm, ForgotPasswordForm, ResetPasswordForm  # 调整导入位置并添加新表单
from werkzeug.security import generate_password_hash
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
    
    student_id = request.form.get('student_id').lower()
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(student_id=student_id).first()

    # 验证用户状态和密码
    if not user:
        flash('该学号不存在，请先注册', 'danger')
        return redirect(url_for('auth.login'))
    if user.is_active == 0:
        flash('账号未激活，请先激活账号', 'danger')
        return redirect(url_for('auth.login'))
    if not user.check_password(password):
        flash('密码错误，请重试', 'danger')
        return redirect(url_for('auth.login'))

    login_user(user, remember=remember)
    return redirect(url_for('main.index'))

@auth.route('/register')
def register():
    form = RegistrationForm()  # 创建表单实例
    return render_template('auth/register.html', form=form)  # 传递表单对象

@auth.route('/register', methods=['POST'])
def register_post():
    # 在函数内部导入所需模块
    from app.models.user import User
    from app import db
    
    # 将email改为student_id
    student_id = request.form.get('student_id')
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    id_card = request.form.get('id_card', '')  # 身份证号可选
    # 检查学号是否已存在
    user = User.query.filter_by(student_id=student_id).first()
    if user:
        # 如果用户存在且未激活，则激活账号
        if user.is_active == 0:
            user.is_active = 1
            user.role = 'student'
            if password == confirm_password:
                user.set_password(password)
            db.session.commit()
            flash('账号已激活，请登录', 'success')
        else:
            flash('该学号已被注册，请使用其他学号。')
        return redirect(url_for('auth.register'))

    if password != confirm_password:
        flash('两次输入的密码不一致，请重试。')
        return redirect(url_for('auth.register'))

    # 创建新用户 - 默认为未激活状态的游客
    new_user = User(
        student_id=student_id,
        nickname=username,  # 将name改为nickname
        id_card=id_card,
        is_active=0,  # 默认为未激活
        role='guest'  # 默认为游客
    )
    if password:  # 可选密码，未激活用户可以没有密码
        new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()

    flash('注册成功，请等待激活或联系管理员', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# 添加忘记密码路由
@auth.route('/forgot_password')
def forgot_password():
    form = ForgotPasswordForm()
    return render_template('auth/forgot_password.html', form=form)

@auth.route('/forgot_password', methods=['POST'])
def forgot_password_post():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        student_id = form.student_id.data
        id_card = form.id_card.data
        user = User.query.filter_by(student_id=student_id, id_card=id_card).first()
        
        if user:
            # 验证通过，跳转到密码重置页面
            return redirect(url_for('auth.reset_password', user_id=user.id))
        flash('学号或身份证号不正确', 'danger')
    return render_template('auth/forgot_password.html', form=form)

# 添加密码重置路由
@auth.route('/reset-password/<int:user_id>')
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    form = ResetPasswordForm()
    return render_template('auth/reset_password.html', form=form, user_id=user_id)

@auth.route('/reset-password/<int:user_id>', methods=['POST'])
def reset_password_post(user_id):
    user = User.query.get_or_404(user_id)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)  # 将new_password改为password
        db.session.commit()
        flash('密码已成功重置，请使用新密码登录', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form, user_id=user_id)

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
        current_user.nickname = form.nickname.data
        current_user.email = form.email.data
        if form.password.data:
            current_user.set_password(form.password.data)
        db.session.commit()
        flash('个人资料已更新', 'success')
        return redirect(url_for('auth.profile'))
    elif request.method == 'GET':
        form.nickname.data = current_user.nickname
    # 修改render_template调用，添加user参数
    return render_template('auth/edit_profile.html', form=form, user=current_user)
from app.forms import LoginForm, RegistrationForm, EditProfileForm  # 添加此行导入新表单
from werkzeug.security import generate_password_hash
import uuid