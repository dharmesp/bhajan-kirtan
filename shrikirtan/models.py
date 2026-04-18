import re
from datetime import datetime
from . import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    display_order = db.Column(db.Integer, default=0)
    bhajans = db.relationship('Bhajan', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'


class Bhajan(db.Model):
    __tablename__ = 'bhajans'

    id = db.Column(db.Integer, primary_key=True)
    title_gujarati = db.Column(db.String(300), nullable=False)
    title_english = db.Column(db.String(300), nullable=False)
    content_gujarati = db.Column(db.Text, nullable=False, default='')
    content_english = db.Column(db.Text, nullable=False, default='')
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    slug = db.Column(db.String(300), nullable=False, unique=True, index=True)
    display_order = db.Column(db.Integer, default=999)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def _make_slug(title_english):
        slug = title_english.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        return slug.strip('-') or 'bhajan'

    @classmethod
    def generate_unique_slug(cls, title_english, exclude_id=None):
        base = cls._make_slug(title_english)
        slug = base
        n = 1
        while True:
            q = cls.query.filter_by(slug=slug)
            if exclude_id:
                q = q.filter(cls.id != exclude_id)
            if not q.first():
                return slug
            slug = f'{base}-{n}'
            n += 1

    def __repr__(self):
        return f'<Bhajan {self.title_english}>'


class Setting(db.Model):
    __tablename__ = 'settings'

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, default='')

    @classmethod
    def get(cls, key, default=''):
        s = cls.query.get(key)
        return s.value if s else default

    @classmethod
    def set(cls, key, value):
        s = cls.query.get(key)
        if s:
            s.value = value
        else:
            s = cls(key=key, value=value)
            db.session.add(s)
        db.session.commit()


class AdminUser(db.Model):
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
