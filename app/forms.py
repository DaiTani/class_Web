from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, HiddenField, SelectField  # 添加 SelectField 导入
from wtforms.validators import DataRequired, Email, Length, Optional

class LoginForm(FlaskForm):
    # 将email字段改为student_id
    student_id = StringField('学号', validators=[DataRequired(), Length(min=8, max=20)])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

class RegistrationForm(FlaskForm):
    # 移除name字段，只保留username作为昵称输入
    student_id = StringField('学号', validators=[DataRequired(), Length(min=8, max=20)])
    username = StringField('昵称', validators=[DataRequired(), Length(min=2, max=64)])  # 标签为"昵称"
    password = PasswordField('密码', validators=[DataRequired()])
    # 添加身份证号字段（注册时可选，后续激活时必填）
    id_card = StringField('身份证号', validators=[Optional(), Length(min=18, max=18)])
    submit = SubmitField('注册')

class EditProfileForm(FlaskForm):
    nickname = StringField('昵称', validators=[DataRequired()])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('新密码', validators=[Optional(), Length(min=6, max=128)])  # 允许空值
    avatar = FileField('头像', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png'], '只允许JPG和PNG图片')])
    submit = SubmitField('保存')

class MovePhotoForm(FlaskForm):
    photo_id = HiddenField('照片ID', validators=[DataRequired()])
    target_album_id = SelectField('目标相册', coerce=int, validators=[DataRequired()])
    submit = SubmitField('移动')

class ForgotPasswordForm(FlaskForm):
    student_id = StringField('学号', validators=[DataRequired(), Length(min=8, max=20)])
    id_card = StringField('身份证号', validators=[DataRequired(), Length(min=18, max=18)])
    submit = SubmitField('验证身份')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('新密码', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('确认新密码', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('重置密码')