from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, HiddenField, SelectField  # 添加 SelectField 导入
from wtforms.validators import DataRequired, Email, Length, Optional

class LoginForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

class RegistrationForm(FlaskForm):
    name = StringField('姓名', validators=[DataRequired()])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('注册')

class EditProfileForm(FlaskForm):
    name = StringField('姓名', validators=[DataRequired()])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('新密码', validators=[Optional(), Length(min=6, max=128)])  # 允许空值
    avatar = FileField('头像', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png'], '只允许JPG和PNG图片')])
    submit = SubmitField('保存')

class MovePhotoForm(FlaskForm):
    photo_id = HiddenField('照片ID', validators=[DataRequired()])
    target_album_id = SelectField('目标相册', coerce=int, validators=[DataRequired()])
    submit = SubmitField('移动')