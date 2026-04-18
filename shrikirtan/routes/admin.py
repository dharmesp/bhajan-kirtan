import io
import json as json_module
from datetime import datetime, timezone
from functools import wraps
from flask import (
    Blueprint, render_template, redirect, url_for,
    session, request, flash, send_file
)
from ..models import db, Bhajan, Category, Setting, AdminUser
import qrcode

admin_bp = Blueprint('admin', __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated


def setup_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not AdminUser.query.first():
            return redirect(url_for('setup.setup'))
        return f(*args, **kwargs)
    return decorated


# ── Authentication ────────────────────────────────────────────────────────────

@admin_bp.route('/getmein', methods=['GET', 'POST'])
@setup_required
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            session.permanent = True
            return redirect(url_for('admin.dashboard'))
        error = 'Invalid credentials. Please try again.'
    return render_template('login.html', error=error)


@admin_bp.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('public.index'))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/')
@login_required
def dashboard():
    bhajans = Bhajan.query.order_by(Bhajan.display_order, Bhajan.id).all()
    categories = Category.query.order_by(Category.display_order, Category.name).all()
    return render_template('admin/dashboard.html', bhajans=bhajans, categories=categories)


# ── Bhajan CRUD ───────────────────────────────────────────────────────────────

@admin_bp.route('/admin/bhajan/add', methods=['GET', 'POST'])
@login_required
def add_bhajan():
    categories = Category.query.order_by(Category.display_order, Category.name).all()
    if request.method == 'POST':
        title_gu = request.form.get('title_gujarati', '').strip()
        title_en = request.form.get('title_english', '').strip()
        content_gu = request.form.get('content_gujarati', '').strip()
        content_en = request.form.get('content_english', '').strip()
        cat_id = request.form.get('category_id') or None
        try:
            display_order = int(request.form.get('display_order', 999))
        except ValueError:
            display_order = 999
        is_active = request.form.get('is_active') == 'on'

        if not title_gu or not title_en:
            flash('Both Gujarati and English titles are required.', 'danger')
        else:
            slug = Bhajan.generate_unique_slug(title_en)
            bhajan = Bhajan(
                title_gujarati=title_gu,
                title_english=title_en,
                content_gujarati=content_gu,
                content_english=content_en,
                category_id=int(cat_id) if cat_id else None,
                slug=slug,
                display_order=display_order,
                is_active=is_active,
            )
            db.session.add(bhajan)
            db.session.commit()
            flash(f'Bhajan "{title_en}" added successfully!', 'success')
            return redirect(url_for('admin.dashboard'))

    return render_template('admin/bhajan_form.html',
                           bhajan=None, categories=categories, action='Add')


@admin_bp.route('/admin/bhajan/edit/<int:bhajan_id>', methods=['GET', 'POST'])
@login_required
def edit_bhajan(bhajan_id):
    bhajan = db.get_or_404(Bhajan, bhajan_id)
    categories = Category.query.order_by(Category.display_order, Category.name).all()

    if request.method == 'POST':
        title_gu = request.form.get('title_gujarati', '').strip()
        title_en = request.form.get('title_english', '').strip()
        content_gu = request.form.get('content_gujarati', '').strip()
        content_en = request.form.get('content_english', '').strip()
        cat_id = request.form.get('category_id') or None
        try:
            display_order = int(request.form.get('display_order', 999))
        except ValueError:
            display_order = 999
        is_active = request.form.get('is_active') == 'on'

        if not title_gu or not title_en:
            flash('Both Gujarati and English titles are required.', 'danger')
        else:
            if title_en != bhajan.title_english:
                bhajan.slug = Bhajan.generate_unique_slug(title_en, exclude_id=bhajan.id)
            bhajan.title_gujarati = title_gu
            bhajan.title_english = title_en
            bhajan.content_gujarati = content_gu
            bhajan.content_english = content_en
            bhajan.category_id = int(cat_id) if cat_id else None
            bhajan.display_order = display_order
            bhajan.is_active = is_active
            db.session.commit()
            flash(f'Bhajan "{title_en}" updated!', 'success')
            return redirect(url_for('admin.dashboard'))

    return render_template('admin/bhajan_form.html',
                           bhajan=bhajan, categories=categories, action='Edit')


@admin_bp.route('/admin/bhajan/delete/<int:bhajan_id>', methods=['POST'])
@login_required
def delete_bhajan(bhajan_id):
    bhajan = db.get_or_404(Bhajan, bhajan_id)
    name = bhajan.title_english
    db.session.delete(bhajan)
    db.session.commit()
    flash(f'Bhajan "{name}" deleted.', 'info')
    return redirect(url_for('admin.dashboard'))


# ── Category CRUD ─────────────────────────────────────────────────────────────

@admin_bp.route('/admin/category/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name', '').strip()
    try:
        order = int(request.form.get('display_order', 0))
    except ValueError:
        order = 0
    if name:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name, display_order=order))
            db.session.commit()
            flash(f'Category "{name}" added.', 'success')
        else:
            flash('A category with that name already exists.', 'warning')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/category/delete/<int:cat_id>', methods=['POST'])
@login_required
def delete_category(cat_id):
    cat = db.get_or_404(Category, cat_id)
    Bhajan.query.filter_by(category_id=cat_id).update({'category_id': None})
    db.session.delete(cat)
    db.session.commit()
    flash(f'Category "{cat.name}" deleted.', 'info')
    return redirect(url_for('admin.dashboard'))


# ── Settings ──────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        domain = request.form.get('domain_name', '').strip().rstrip('/')
        app_title = request.form.get('app_title', '').strip()
        Setting.set('domain_name', domain)
        Setting.set('app_title', app_title or 'ShriKirtan')
        flash('Settings saved successfully.', 'success')
        return redirect(url_for('admin.settings'))

    domain = Setting.get('domain_name', '')
    app_title = Setting.get('app_title', 'ShriKirtan')
    # Build a sample QR preview URL
    sample_bhajan = Bhajan.query.filter_by(is_active=True).first()
    preview_url = None
    if sample_bhajan:
        d = domain or request.host_url.rstrip('/')
        preview_url = f"{d}/bhajan/{sample_bhajan.slug}"
    return render_template('admin/settings.html',
                           domain=domain, app_title=app_title,
                           preview_url=preview_url,
                           sample_bhajan=sample_bhajan)


# ── QR Code (admin preview) ───────────────────────────────────────────────────

@admin_bp.route('/admin/bhajan/<int:bhajan_id>/qrcode.png')
@login_required
def bhajan_qrcode_admin(bhajan_id):
    bhajan = db.get_or_404(Bhajan, bhajan_id)
    domain = Setting.get('domain_name', '').rstrip('/')
    if not domain:
        domain = request.host_url.rstrip('/')
    url = f"{domain}/bhajan/{bhajan.slug}"

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


# ── Export ────────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/export')
@login_required
def export_data():
    categories = Category.query.order_by(Category.display_order, Category.name).all()
    bhajans    = Bhajan.query.order_by(Bhajan.display_order, Bhajan.id).all()
    cat_map    = {c.id: c.name for c in categories}

    data = {
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "categories": [
            {"name": c.name, "display_order": c.display_order}
            for c in categories
        ],
        "bhajans": [
            {
                "title_gujarati":   b.title_gujarati,
                "title_english":    b.title_english,
                "content_gujarati": b.content_gujarati or "",
                "content_english":  b.content_english or "",
                "category":         cat_map.get(b.category_id),
                "slug":             b.slug,
                "display_order":    b.display_order,
                "is_active":        b.is_active,
            }
            for b in bhajans
        ],
    }

    buf = io.BytesIO(
        json_module.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    )
    buf.seek(0)
    filename = f"shrikirtan_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return send_file(buf, mimetype='application/json',
                     as_attachment=True, download_name=filename)


# ── Import ────────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/import', methods=['POST'])
@login_required
def import_data():
    f = request.files.get('import_file')
    if not f or not f.filename.lower().endswith('.json'):
        flash('Please upload a valid .json file.', 'danger')
        return redirect(url_for('admin.dashboard'))

    try:
        data = json_module.loads(f.read().decode('utf-8'))
    except (json_module.JSONDecodeError, UnicodeDecodeError) as e:
        flash(f'Invalid JSON file: {e}', 'danger')
        return redirect(url_for('admin.dashboard'))

    if not isinstance(data, dict) or 'bhajans' not in data:
        flash('Unrecognised file format — must be a ShriKirtan export file.', 'danger')
        return redirect(url_for('admin.dashboard'))

    # ── 1. Import categories ──────────────────────────────────────────────────
    cat_name_to_id = {c.name: c.id for c in Category.query.all()}
    cats_added = 0
    for cat_data in data.get('categories', []):
        name = (cat_data.get('name') or '').strip()
        if not name or name in cat_name_to_id:
            continue
        new_cat = Category(name=name, display_order=cat_data.get('display_order', 0))
        db.session.add(new_cat)
        db.session.flush()          # get generated id before commit
        cat_name_to_id[name] = new_cat.id
        cats_added += 1

    # ── 2. Import bhajans ─────────────────────────────────────────────────────
    added = updated = skipped = 0
    for bdata in data.get('bhajans', []):
        title_gu = (bdata.get('title_gujarati') or '').strip()
        title_en = (bdata.get('title_english')  or '').strip()
        if not title_gu or not title_en:
            skipped += 1
            continue

        cat_name = bdata.get('category')
        cat_id   = cat_name_to_id.get(cat_name) if cat_name else None
        slug     = (bdata.get('slug') or '').strip()

        existing = Bhajan.query.filter_by(slug=slug).first() if slug else None
        if existing:
            existing.title_gujarati   = title_gu
            existing.title_english    = title_en
            existing.content_gujarati = bdata.get('content_gujarati', '')
            existing.content_english  = bdata.get('content_english',  '')
            existing.category_id      = cat_id
            existing.display_order    = bdata.get('display_order', 999)
            existing.is_active        = bdata.get('is_active', True)
            updated += 1
        else:
            new_slug = slug if slug else Bhajan.generate_unique_slug(title_en)
            db.session.add(Bhajan(
                title_gujarati   = title_gu,
                title_english    = title_en,
                content_gujarati = bdata.get('content_gujarati', ''),
                content_english  = bdata.get('content_english',  ''),
                category_id      = cat_id,
                slug             = new_slug,
                display_order    = bdata.get('display_order', 999),
                is_active        = bdata.get('is_active', True),
            ))
            added += 1

    db.session.commit()

    parts = []
    if cats_added: parts.append(f'{cats_added} categor{"y" if cats_added == 1 else "ies"} added')
    if added:      parts.append(f'{added} bhajan{"" if added == 1 else "s"} added')
    if updated:    parts.append(f'{updated} bhajan{"" if updated == 1 else "s"} updated')
    if skipped:    parts.append(f'{skipped} skipped (missing title)')
    flash('Import complete — ' + (', '.join(parts) if parts else 'nothing new to import.'), 'success')
    return redirect(url_for('admin.dashboard'))
