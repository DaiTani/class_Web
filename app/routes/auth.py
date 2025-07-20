from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user, logout_user
from app.models.user import User
from app import db

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
    return render_template('auth/profile.html')

@auth.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        password = request.form.get('password')
        if password:
            current_user.set_password(password)
        db.session.commit()
        flash('个人资料已更新!')
        return redirect(url_for('auth.profile'))
    return render_template('auth/edit_profile.html')