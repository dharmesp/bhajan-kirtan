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
    if db_url.startswith('sqlite://'):
        # Ensure the directory exists (e.g. /data on Fly.io volume)
        import re as _re
        m = _re.match(r'sqlite:////(.+)', db_url)
        if m:
            os.makedirs(os.path.dirname('/' + m.group(1)), exist_ok=True)
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

        # Add is_visible column to existing bhajans tables (one-time migration)
        try:
            from sqlalchemy import text, inspect as sa_inspect
            insp = sa_inspect(db.engine)
            cols = [c['name'] for c in insp.get_columns('bhajans')]
            if 'is_visible' not in cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        'ALTER TABLE bhajans ADD COLUMN is_visible BOOLEAN NOT NULL DEFAULT 1'
                    ))
                    conn.commit()
        except Exception:
            pass  # Column already exists or table not yet created — safe to ignore

        # Add show_in_filter column to categories (one-time migration)
        try:
            insp = sa_inspect(db.engine)
            cols = [c['name'] for c in insp.get_columns('categories')]
            if 'show_in_filter' not in cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        'ALTER TABLE categories ADD COLUMN show_in_filter BOOLEAN NOT NULL DEFAULT 1'
                    ))
                    conn.commit()
        except Exception:
            pass

        # Add audio_filename column to bhajans (one-time migration)
        try:
            insp = sa_inspect(db.engine)
            cols = [c['name'] for c in insp.get_columns('bhajans')]
            if 'audio_filename' not in cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        'ALTER TABLE bhajans ADD COLUMN audio_filename VARCHAR(300)'
                    ))
                    conn.commit()
        except Exception:
            pass

        # Add view_count column to bhajans (one-time migration)
        try:
            insp = sa_inspect(db.engine)
            cols = [c['name'] for c in insp.get_columns('bhajans')]
            if 'view_count' not in cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        'ALTER TABLE bhajans ADD COLUMN view_count INTEGER NOT NULL DEFAULT 0'
                    ))
                    conn.commit()
        except Exception:
            pass

        # Migrate bhajan_categories junction table from legacy category_id
        try:
            from sqlalchemy import text, inspect as sa_inspect
            insp = sa_inspect(db.engine)
            tables = insp.get_table_names()
            if 'bhajan_categories' in tables:
                # Populate junction from legacy category_id where not already migrated
                with db.engine.connect() as conn:
                    conn.execute(text('''
                        INSERT OR IGNORE INTO bhajan_categories (bhajan_id, category_id)
                        SELECT id, category_id FROM bhajans
                        WHERE category_id IS NOT NULL
                    '''))
                    conn.commit()
        except Exception:
            pass

    from .routes.public import public_bp
    from .routes.admin import admin_bp
    from .routes.setup import setup_bp
    from .routes.manage import manage_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(manage_bp)

    # Inject app title and helper into all templates
    @app.context_processor
    def inject_globals():
        from .models import Setting
        # Collect print image slots that have a file uploaded
        print_image_slots = [s for s in (1, 2) if Setting.get(f'print_image_{s}', '')]
        return {
            'app_title': Setting.get('app_title', 'ShriKirtan'),
            'print_image_slots': print_image_slots,
        }

    return app
