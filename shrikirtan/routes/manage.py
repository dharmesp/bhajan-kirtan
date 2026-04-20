from functools import wraps
from datetime import datetime
from flask import (
    Blueprint, render_template, redirect, url_for,
    session, request, jsonify, flash
)
from ..models import db, Bhajan, Category, SiteManager, Setting

manage_bp = Blueprint('manage', __name__)


def manager_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('manager_logged_in'):
            return redirect(url_for('manage.login'))
        return f(*args, **kwargs)
    return decorated


# ── Authentication ────────────────────────────────────────────────────────────

@manage_bp.route('/manage/login', methods=['GET', 'POST'])
def login():
    if session.get('manager_logged_in'):
        return redirect(url_for('manage.dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = SiteManager.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['manager_logged_in'] = True
            session['manager_username'] = username
            session.permanent = True
            return redirect(url_for('manage.dashboard'))
        error = 'Invalid credentials. Please try again.'
    return render_template('manage/login.html', error=error)


@manage_bp.route('/manage/logout')
def logout():
    session.pop('manager_logged_in', None)
    session.pop('manager_username', None)
    return redirect(url_for('manage.login'))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@manage_bp.route('/manage/')
@manager_login_required
def dashboard():
    bhajans = (
        Bhajan.query
        .filter_by(is_active=True)
        .order_by(Bhajan.display_order, Bhajan.id)
        .all()
    )
    categories = Category.query.order_by(Category.display_order, Category.name).all()
    visible_count = sum(1 for b in bhajans if b.is_visible)
    return render_template('manage/dashboard.html',
                           bhajans=bhajans,
                           categories=categories,
                           visible_count=visible_count)


# ── AJAX API ──────────────────────────────────────────────────────────────────

@manage_bp.route('/manage/api/toggle/<int:bhajan_id>', methods=['POST'])
@manager_login_required
def toggle_visibility(bhajan_id):
    bhajan = db.get_or_404(Bhajan, bhajan_id)
    bhajan.is_visible = not bhajan.is_visible
    db.session.commit()
    return jsonify({'id': bhajan.id, 'is_visible': bhajan.is_visible})


@manage_bp.route('/manage/api/show-all', methods=['POST'])
@manager_login_required
def show_all():
    Bhajan.query.filter(Bhajan.is_active == True).update({'is_visible': True})
    db.session.commit()
    return jsonify({'ok': True})


@manage_bp.route('/manage/api/hide-all', methods=['POST'])
@manager_login_required
def hide_all():
    Bhajan.query.filter(Bhajan.is_active == True).update({'is_visible': False})
    db.session.commit()
    return jsonify({'ok': True})


@manage_bp.route('/manage/api/order/<int:bhajan_id>', methods=['POST'])
@manager_login_required
def update_order(bhajan_id):
    bhajan = db.get_or_404(Bhajan, bhajan_id)
    data = request.get_json(silent=True) or {}
    try:
        order = int(data.get('order', bhajan.display_order))
        bhajan.display_order = order
        db.session.commit()
        return jsonify({'id': bhajan.id, 'display_order': bhajan.display_order})
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid order value'}), 400


@manage_bp.route('/manage/api/now-playing/set/<int:bhajan_id>', methods=['POST'])
@manager_login_required
def set_now_playing(bhajan_id):
    bhajan = db.get_or_404(Bhajan, bhajan_id)
    Setting.set('now_playing_id', str(bhajan.id))
    Setting.set('now_playing_at', datetime.utcnow().isoformat())
    return jsonify({'ok': True, 'id': bhajan.id})


@manage_bp.route('/manage/api/now-playing/clear', methods=['POST'])
@manager_login_required
def clear_now_playing():
    Setting.set('now_playing_id', '')
    Setting.set('now_playing_at', '')
    return jsonify({'ok': True})
