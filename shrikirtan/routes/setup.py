from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from ..models import db, AdminUser

setup_bp = Blueprint('setup', __name__)


@setup_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    # Only allow setup if no admin exists yet
    if AdminUser.query.first():
        return redirect(url_for('admin.login'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not username or len(username) < 3:
            error = 'Username must be at least 3 characters.'
        elif not password or len(password) < 8:
            error = 'Password must be at least 8 characters.'
        elif password != confirm:
            error = 'Passwords do not match.'
        else:
            user = AdminUser(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session['admin_logged_in'] = True
            session['admin_username'] = username
            session.permanent = True
            flash('Admin account created! Welcome to ShriKirtan.', 'success')
            return redirect(url_for('admin.dashboard'))

    return render_template('setup.html', error=error)
