from email.policy import default
from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app, request, url_for
from flask_login import LoginManager, UserMixin
from app.exceptions import ValidationError
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.orderinglist import ordering_list

from app import db, login_manager


class Permission:

    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    REGISTER = 16
    ADMIN = 32


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        roles = {
            'User': [Permission.COMMENT, Permission.WRITE],
            'Agent': [Permission.COMMENT, Permission.WRITE,
                          Permission.MODERATE, Permission.REGISTER],
            'Administrator': [Permission.COMMENT, Permission.WRITE,
                              Permission.MODERATE, Permission.REGISTER,
                              Permission.ADMIN],
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role %r>' % self.name


registered_farmers = db.Table('registered_farmers',
    db.Column('farmer_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('agent_id', db.Integer, db.ForeignKey('users.id'))
)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer(), primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=True)
    firstname = db.Column(db.String(64), nullable=False, index=True)
    lastname = db.Column(db.String(64), nullable=False)
    mobile_no = db.Column(db.Integer(), nullable=False)
    date_of_birth = db.Column(db.DateTime())
    location = db.Column(db.String(64), nullable=False)
    state_of_origin = db.Column(db.String(64))
    country = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    points = db.Column(db.Integer, default=0)
    wallet = db.Column(db.Integer, default=1000)

    farmers = db.relationship(
                         'User', secondary=registered_farmers,
                          primaryjoin=(registered_farmers.c.farmer_id == id),
                          secondaryjoin=(registered_farmers.c.agent_id == id),
                          backref=db.backref('registered_farmers', lazy='dynamic'), lazy='dynamic')
    products = db.relationship('Product', backref='supplier', lazy=True)
    cooperative = db.Column(db.Integer, db.ForeignKey('cooperatives.id'))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')


    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.mobile_no == 7034858160:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def reset_password(token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def is_agent(self):
        return self.can(Permission.REGISTER)

    @property 
    def styled_wallet(self):
        if len(str(self.wallet)) >= 4:
            return f'{str(self.wallet)[:-3]},{str(self.wallet)[-3:]}NGN'
        else:
            return f'{self.wallet}NGN'

    def can_purchase(self, purchase_object):
        return self.budget >= purchase_object.price

    def can_sell(self, sold_object):
        return sold_object in self.products

    def add_points(self, purchase_object):
        self.points += (purchase_object.price / 20)
        return self.points

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def gravatar(self, size=100, default='identicon', rating='g'):
        url = 'https://secure.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts_url': url_for('api.get_user_posts', id=self.id),
            'cooperative_url': url_for('api.get_cooperative', id=self.id),
            'post_count': self.posts.count()
        }
        return json_user

    def __repr__(self):
        return '<User %r>' % self.firstname


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer(), primary_key=True)
    product_name = db.Column(db.String(30), nullable=False)
    product_type = db.Column(db.String(30), nullable=False)
    product_variety = db.Column(db.String(30), nullable=False)
    location = db.Column(db.String(30), nullable=False)
    description = db.Column(db.String(200))
    price = db.Column(db.Integer(), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    is_available = db.Column(db.Boolean(), default=True)
    owner_supplier = db.Column(db.Integer(), db.ForeignKey('users.id'))
    product_image = db.Column(db.String(20),nullable=False,default='default.JPG')

    def purchase(self, user):
        self.owner_supplier = user.id 
        user.budget -= self.price
        db.session.commit()

    def sell(self, user):
        self.owner_supplier = user.id
        user.budget += self.price
        db.session.commit()

    def __repr__(self):
        return f'{self.product_name}, a {self.product_type} of {self.product_variety} \
                    variety available at {self.location}'


class Cooperative(db.Model):

    __tablename__ = 'cooperatives'

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    purpose = db.Column(db.String(64), nullable=False, unique=True)
    products = db.Column(db.String(30), nullable=False, unique=True)
    location = db.Column(db.String(30), nullable=False)
    members = db.relationship('User', backref='member', lazy=True)

    def __repr__(self):
        return f'{self.name}, located at {self.location}'


class Forum(db.Model):
    __tablename__ = 'forums'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    length = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    posts = db.relationship('Post',cascade='all,delete', backref='forum',
                                    lazy='dynamic')

    def to_json(self):
        json_sport = {
            'url': url_for('api.get_sport', id=self.id),
            'name': self.name,
            'description': self.description,
            'posts_url': url_for('api.get_posts', id=self.id),
        }
        return json_sport

    @staticmethod
    def from_json(json_sport):
        name = json_sport.get('name')
        if name is None or name == '':
            raise ValidationError('forum does not have a name')
        return Forum(name=name)


def forum_posts_append(forum, posts, initiator):
    """Update some sport values when `Sport.teams.append` is called."""
    forum.length += 1
    forum.updated = datetime.utcnow()

db.event.listen(Forum.name, 'append', forum_posts_append)

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    forum_id = db.Column(db.Integer, db.ForeignKey('forums.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_general_post = {
            'url': url_for('api.get_post', id=self.id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
            'comments_url': url_for('api.get_post_comments', id=self.id),
            'comment_count': self.general_comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)


db.event.listen(Post.body, 'set', Post.on_changed_body)


class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    general_post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_general_comment = {
            'url': url_for('api.get_comment', id=self.id),
            'general_post_url': url_for('api.get_post', id=self.post_id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        return Comment(body=body)


db.event.listen(Comment.body, 'set', Comment.on_changed_body)
