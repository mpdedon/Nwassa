from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, StringField, PasswordField, BooleanField, \
    DateField, TextAreaField, BooleanField, SelectField, SubmitField
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from flask_wtf.file import FileField,FileAllowed
from wtforms import ValidationError
from flask_pagedown.fields import PageDownField

from app.models import Cooperative
from app.models import User, Role, Product, Cooperative


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name', validators=[DataRequired()])
    mobile_no = IntegerField('Phone Number', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Email already registered.')

    def validate_mobile_no(self, field):
        if User.query.filter_by(mobile_no=field.data).first():
            raise ValidationError('Mobile Number already registered.')


def user_choice():
    return User.query


class EditUserForm(FlaskForm):
    firstname = StringField('First Name', validators=[Length(0, 64)])
    lastname = StringField('Last Name', validators=[Length(0, 64)])
    date_of_birth = DateField('Date of Birth',format='%Y-%m-%d')
    location = StringField('Location', validators=[Length(0, 64)])
    state_of_origin = StringField('State', validators=[Length(0, 20)])
    country = StringField('Country', validators=[Length(0, 20)])
    about_me = TextAreaField('About me')
    cooperative = SelectField('Choose Cooperative',coerce=int, validate_choice=False)
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.cooperative.choices = [(cooperative.id, cooperative.name)
                             for cooperative in Cooperative.query.order_by(Cooperative.name).all()]
        self.user = user


class EditAgentForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    confirmed = BooleanField('Confirmed')
    date_of_birth = DateField('Date of Birth',format='%Y-%m-%d')
    location = StringField('Location', validators=[Length(0, 64)])
    state_of_origin = StringField('State', validators=[Length(0, 20)])
    country = StringField('Country', validators=[Length(0, 20)])
    about_me = TextAreaField('About me')
    cooperative = SelectField('Choose Cooperative',coerce=int, validate_choice=False)
    submit = SubmitField('Submit')


    def __init__(self, user, *args, **kwargs):
        super(EditAgentForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user


    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_mobile_no(self, field):
        if field.data != self.user.mobile_no and \
                User.query.filter_by(mobile_no=field.data).first():
            raise ValidationError('Mobile Number already in use.')


class ProductForm(FlaskForm):

    product_name = StringField("Product Name", validators=[DataRequired()])
    product_type = StringField("Product Type", validators=[DataRequired()])
    product_variety = StringField("Variety", validators=[DataRequired()])
    location = StringField("Location", validators=[DataRequired()])
    price = IntegerField("Price", validators=[DataRequired()])
    submit = SubmitField('Add Product')

    def validate_name(self, field):
        if Product.query.filter_by(product_name=field.data).first():
            raise ValidationError('Product already exists!')

    def __init__(self, owner_supplier, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.owner_supplier.choices = [(owner_supplier.id, owner_supplier.firstname)
                             for owner_supplier in User.query.order_by(User.firstname).all()]
        self.owner_supplier = owner_supplier


class UpdateProductForm(FlaskForm):

    product_name = StringField("Product Name", validators=[DataRequired()])
    product_type = StringField("Product Type", validators=[DataRequired()])
    product_variety = StringField("Variety", validators=[DataRequired()])
    location = StringField("Location", validators=[DataRequired()])
    price = IntegerField("Price", validators=[DataRequired()])
    picture = FileField('Upload Product Image',validators=[FileAllowed(['jpg','png','PNG','JPG','pdf','PDF'])])
    description = StringField("About Product", validators=[DataRequired()])
    is_available = BooleanField("Available", validators=[DataRequired()])
    submit = SubmitField('Update Profile')

class CooperativeForm(FlaskForm):
    name = StringField("Cooperative Name", validators=[DataRequired()])
    purpose = StringField("Purpose", validators=[DataRequired()])
    products = StringField("Products", validators=[DataRequired()])
    location = StringField("Official Address", validators=[DataRequired()])
    submit = SubmitField('Create Cooperative')

    def validate_name(self, field):
        if Cooperative.query.filter_by(name=field.data).first():
            raise ValidationError('Cooperative has already been created.')


class PostForm(FlaskForm):
    body = PageDownField("What's on your mind?", validators=[DataRequired()])
    submit = SubmitField('Make Post')


class CommentForm(FlaskForm):
    body = StringField('Enter your comment', validators=[DataRequired()])
    submit = SubmitField('Make Comment')


class PurchaseForm(FlaskForm):
    submit = SubmitField('Make Payment')

class SellingForm(FlaskForm):
    submit = SubmitField('Sell Product')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password', validators=[DataRequired()])
    password = PasswordField('New password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm new password',
                              validators=[DataRequired()])
    submit = SubmitField('Update Password')


class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    submit = SubmitField('Reset Password')


class PasswordResetForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Reset Password')


class ChangeEmailForm(FlaskForm):
    email = StringField('New Email', validators=[DataRequired(), Length(1, 64),
                                                 Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Update Email Address')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Email already registered.')