import os
import secrets
from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    os.makedirs(app.instance_path, exist_ok=True)

    # Secret key: env var in production, file-based fallback for local dev
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        key_file = os.path.join(app.instance_path, 'secret.key')
        if os.path.exists(key_file):
            with open(key_file) as f:
                secret_key = f.read().strip()
        else:
            secret_key = secrets.token_hex(32)
            with open(key_file, 'w') as f:
                f.write(secret_key)

    app.config['SECRET_KEY'] = secret_key

    # Database: env var (Fly.io volume) → local SQLite fallback
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url.startswith('postgres://'):          # SQLAlchemy requires postgresql://
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        db_url or f"sqlite:///{os.path.join(app.instance_path, 'shrikirtan.db')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # Secure cookies when running on Fly.io (always HTTPS there)
    if os.environ.get('FLY_APP_NAME'):
        app.config['SESSION_COOKIE_SECURE'] = True

    db.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()

    from .routes.public import public_bp
    from .routes.admin import admin_bp
    from .routes.setup import setup_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(setup_bp)

    # Inject app title and helper into all templates
    @app.context_processor
    def inject_globals():
        from .models import Setting
        return {
            'app_title': Setting.get('app_title', 'ShriKirtan'),
        }

    return app
