import io
import json as json_module
import os
import uuid
import zipfile
from datetime import datetime, timezone
from functools import wraps
from flask import (
    Blueprint, render_template, redirect, url_for,
    session, request, flash, send_file, current_app, jsonify
)
from ..models import db, Bhajan, Category, Setting, AdminUser, SiteManager, Event
import qrcode

admin_bp = Blueprint('admin', __name__)

ALLOWED_AUDIO = {'mp3', 'm4a', 'ogg', 'wav'}


def _audio_upload_dir():
    """Return (and create) the directory where audio files are stored."""
    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    base = '/data' if db_url.startswith('sqlite:////data/') else current_app.instance_path
    path = os.path.join(base, 'uploads', 'audio')
    os.makedirs(path, exist_ok=True)
    return path


def _save_audio_file(file_storage):
    """Validate, sanitize and save an uploaded audio file. Returns saved filename or None."""
    if not file_storage or not file_storage.filename:
        return None
    original = file_storage.filename
    ext = original.rsplit('.', 1)[-1].lower() if '.' in original else ''
    if ext not in ALLOWED_AUDIO:
        return None
    # Keep original name but strip unsafe characters
    import re as _re
    stem = original.rsplit('.', 1)[0]
    safe_stem = _re.sub(r'[^\w\-.]', '_', stem).strip('._') or 'audio'
    filename = f"{safe_stem}.{ext}"
    # Avoid collisions: append a short suffix if file already exists
    dest_dir = _audio_upload_dir()
    dest = os.path.join(dest_dir, filename)
    if os.path.exists(dest):
        suffix = uuid.uuid4().hex[:6]
        filename = f"{safe_stem}_{suffix}.{ext}"
        dest = os.path.join(dest_dir, filename)
    file_storage.save(dest)
    return filename


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

    # Suggest reordering: active bhajans whose order rank lags their view rank by >5 positions
    active_with_views = [b for b in bhajans if b.is_active and (b.view_count or 0) > 0]
    by_views = sorted(active_with_views, key=lambda b: -(b.view_count or 0))
    view_rank = {b.id: i for i, b in enumerate(by_views)}
    by_order = sorted(active_with_views, key=lambda b: (b.display_order, b.id))
    order_rank = {b.id: i for i, b in enumerate(by_order)}
    suggestion_count = sum(
        1 for b in active_with_views
        if order_rank.get(b.id, 0) - view_rank.get(b.id, 0) > 5
    )

    categories_json = [{'id': c.id, 'name': c.name} for c in categories]

    return render_template('admin/dashboard.html',
                           bhajans=bhajans,
                           categories=categories,
                           categories_json=categories_json,
                           suggestion_count=suggestion_count)


@admin_bp.route('/admin/bhajan/order/<int:bhajan_id>', methods=['POST'])
@login_required
def update_order(bhajan_id):
    bhajan = db.get_or_404(Bhajan, bhajan_id)
    data = request.get_json(silent=True) or {}
    try:
        new_order = int(data.get('order', bhajan.display_order))
    except (ValueError, TypeError):
        return jsonify({'error': 'invalid'}), 400
    bhajan.display_order = new_order
    db.session.commit()
    return jsonify({'ok': True, 'order': new_order})


@admin_bp.route('/admin/bhajan/title/<int:bhajan_id>', methods=['POST'])
@login_required
def update_title(bhajan_id):
    bhajan = db.get_or_404(Bhajan, bhajan_id)
    data = request.get_json(silent=True) or {}
    field = data.get('field')
    value = (data.get('value') or '').strip()
    if not value:
        return jsonify({'error': 'empty'}), 400
    if field == 'gujarati':
        bhajan.title_gujarati = value
    elif field == 'english':
        bhajan.title_english = value
    else:
        return jsonify({'error': 'invalid'}), 400
    db.session.commit()
    return jsonify({'ok': True, 'value': value})


@admin_bp.route('/admin/bhajan/categories/<int:bhajan_id>', methods=['POST'])
@login_required
def update_categories(bhajan_id):
    bhajan = db.get_or_404(Bhajan, bhajan_id)
    data = request.get_json(silent=True) or {}
    cat_ids = [int(x) for x in (data.get('cat_ids') or []) if str(x).isdigit()]
    bhajan.categories = Category.query.filter(Category.id.in_(cat_ids)).all() if cat_ids else []
    db.session.commit()
    return jsonify({'ok': True, 'categories': [{'id': c.id, 'name': c.name} for c in bhajan.categories]})


@admin_bp.route('/admin/bhajan/active/<int:bhajan_id>', methods=['POST'])
@login_required
def toggle_active(bhajan_id):
    bhajan = db.get_or_404(Bhajan, bhajan_id)
    bhajan.is_active = not bhajan.is_active
    db.session.commit()
    return jsonify({'ok': True, 'is_active': bhajan.is_active})


@admin_bp.route('/admin/category/edit/<int:cat_id>', methods=['POST'])
@login_required
def edit_category(cat_id):
    cat = db.get_or_404(Category, cat_id)
    data = request.get_json(silent=True) or {}
    field = data.get('field')
    value = data.get('value')
    if field == 'name':
        name = (value or '').strip()
        if not name:
            return jsonify({'error': 'empty'}), 400
        duplicate = Category.query.filter_by(name=name).first()
        if duplicate and duplicate.id != cat_id:
            return jsonify({'error': 'duplicate', 'msg': f'"{name}" already exists'}), 400
        cat.name = name
    elif field == 'order':
        try:
            cat.display_order = int(value)
        except (ValueError, TypeError):
            return jsonify({'error': 'invalid'}), 400
    else:
        return jsonify({'error': 'invalid field'}), 400
    db.session.commit()
    return jsonify({'ok': True})


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
        cat_ids = [int(x) for x in request.form.getlist('category_ids') if x.isdigit()]
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
                slug=slug,
                display_order=display_order,
                is_active=is_active,
            )
            if cat_ids:
                bhajan.categories = Category.query.filter(Category.id.in_(cat_ids)).all()
            db.session.add(bhajan)
            db.session.commit()
            # Handle audio upload after commit (need bhajan.id)
            audio_file = request.files.get('audio_file')
            saved = _save_audio_file(audio_file)
            if saved:
                bhajan.audio_filename = saved
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
        cat_ids = [int(x) for x in request.form.getlist('category_ids') if x.isdigit()]
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
            bhajan.categories = Category.query.filter(Category.id.in_(cat_ids)).all() if cat_ids else []
            bhajan.display_order = display_order
            bhajan.is_active = is_active
            # Handle audio upload
            audio_file = request.files.get('audio_file')
            saved = _save_audio_file(audio_file)
            if saved:
                # Delete old file if replacing
                if bhajan.audio_filename:
                    old_path = os.path.join(_audio_upload_dir(), bhajan.audio_filename)
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                bhajan.audio_filename = saved
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
    # Remove audio file if present
    if bhajan.audio_filename:
        path = os.path.join(_audio_upload_dir(), bhajan.audio_filename)
        if os.path.isfile(path):
            os.remove(path)
    db.session.delete(bhajan)
    db.session.commit()
    flash(f'Bhajan "{name}" deleted.', 'info')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/bhajan/delete-audio/<int:bhajan_id>', methods=['POST'])
@login_required
def delete_bhajan_audio(bhajan_id):
    bhajan = db.get_or_404(Bhajan, bhajan_id)
    if bhajan.audio_filename:
        path = os.path.join(_audio_upload_dir(), bhajan.audio_filename)
        if os.path.isfile(path):
            os.remove(path)
        bhajan.audio_filename = None
        db.session.commit()
        flash('Audio track removed.', 'success')
    return redirect(url_for('admin.edit_bhajan', bhajan_id=bhajan_id))


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


@admin_bp.route('/admin/category/toggle-filter/<int:cat_id>', methods=['POST'])
@login_required
def toggle_category_filter(cat_id):
    cat = db.get_or_404(Category, cat_id)
    cat.show_in_filter = not cat.show_in_filter
    db.session.commit()
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/reset-view-counts', methods=['POST'])
@login_required
def reset_view_counts():
    Bhajan.query.update({'view_count': 0})
    db.session.commit()
    flash('All view counts have been reset to 0.', 'success')
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
    print_images = {
        slot: Setting.get(f'print_image_{slot}', '')
        for slot in [1, 2]
    }
    return render_template('admin/settings.html',
                           domain=domain, app_title=app_title,
                           preview_url=preview_url,
                           sample_bhajan=sample_bhajan,
                           print_images=print_images)


# ── Print sidebar image upload / delete ───────────────────────────────────────

_ALLOWED_IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


def _uploads_dir():
    from flask import current_app
    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    base = '/data' if db_url.startswith('sqlite:////data/') else current_app.instance_path
    path = os.path.join(base, 'uploads')
    os.makedirs(path, exist_ok=True)
    return path


def _validate_image(file_storage):
    name = file_storage.filename or ''
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    if ext not in _ALLOWED_IMAGE_EXTS:
        return None, 'Only JPG, PNG, GIF, or WEBP images are allowed.'
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > _MAX_IMAGE_BYTES:
        return None, 'Image must be under 5 MB.'
    try:
        from PIL import Image
        img = Image.open(file_storage.stream)
        img.verify()
        file_storage.seek(0)
    except Exception:
        return None, 'File does not appear to be a valid image.'
    # Normalise to png for simplicity; keep original ext otherwise
    save_ext = 'jpg' if ext in ('jpg', 'jpeg') else ext
    return save_ext, None


@admin_bp.route('/admin/upload-image/<int:slot>', methods=['POST'])
@login_required
def upload_print_image(slot):
    if slot not in (1, 2):
        flash('Invalid image slot.', 'danger')
        return redirect(url_for('admin.settings'))

    f = request.files.get('image_file')
    if not f or not f.filename:
        flash('No file selected.', 'warning')
        return redirect(url_for('admin.settings'))

    save_ext, err = _validate_image(f)
    if err:
        flash(err, 'danger')
        return redirect(url_for('admin.settings'))

    # Delete old file if present
    old_fname = Setting.get(f'print_image_{slot}', '')
    if old_fname:
        old_path = os.path.join(_uploads_dir(), old_fname)
        try:
            if os.path.isfile(old_path):
                os.remove(old_path)
        except OSError:
            pass

    # Save with a UUID filename
    fname = f'{uuid.uuid4().hex}.{save_ext}'
    f.save(os.path.join(_uploads_dir(), fname))
    Setting.set(f'print_image_{slot}', fname)
    flash(f'Image {slot} uploaded successfully.', 'success')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/admin/delete-image/<int:slot>', methods=['POST'])
@login_required
def delete_print_image(slot):
    if slot not in (1, 2):
        flash('Invalid image slot.', 'danger')
        return redirect(url_for('admin.settings'))

    fname = Setting.get(f'print_image_{slot}', '')
    if fname:
        path = os.path.join(_uploads_dir(), fname)
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass
        Setting.set(f'print_image_{slot}', '')
        flash(f'Image {slot} removed.', 'info')
    return redirect(url_for('admin.settings'))


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
        "version": 2,
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
                "categories":       [cat.name for cat in b.categories],
                "audio_filename":   b.audio_filename or "",
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

        # Prefer new "categories" list; fall back to legacy single "category"
        cat_names = bdata.get('categories') or []
        if not cat_names and bdata.get('category'):
            cat_names = [bdata['category']]
        cat_id   = cat_name_to_id.get(cat_names[0]) if cat_names else None
        cat_objs = [db.session.get(Category, cat_name_to_id[n])
                    for n in cat_names if n in cat_name_to_id]
        slug     = (bdata.get('slug') or '').strip()
        audio_fn = (bdata.get('audio_filename') or '').strip() or None

        existing = Bhajan.query.filter_by(slug=slug).first() if slug else None
        if existing:
            existing.title_gujarati   = title_gu
            existing.title_english    = title_en
            existing.content_gujarati = bdata.get('content_gujarati', '')
            existing.content_english  = bdata.get('content_english',  '')
            existing.category_id      = cat_id
            existing.categories       = cat_objs
            existing.display_order    = bdata.get('display_order', 999)
            existing.is_active        = bdata.get('is_active', True)
            if audio_fn:
                existing.audio_filename = audio_fn
            updated += 1
        else:
            new_slug = slug if slug else Bhajan.generate_unique_slug(title_en)
            new_b = Bhajan(
                title_gujarati   = title_gu,
                title_english    = title_en,
                content_gujarati = bdata.get('content_gujarati', ''),
                content_english  = bdata.get('content_english',  ''),
                category_id      = cat_id,
                slug             = new_slug,
                display_order    = bdata.get('display_order', 999),
                is_active        = bdata.get('is_active', True),
                audio_filename   = audio_fn,
            )
            db.session.add(new_b)
            new_b.categories = cat_objs
            added += 1

    db.session.commit()

    parts = []
    if cats_added: parts.append(f'{cats_added} categor{"y" if cats_added == 1 else "ies"} added')
    if added:      parts.append(f'{added} bhajan{"" if added == 1 else "s"} added')
    if updated:    parts.append(f'{updated} bhajan{"" if updated == 1 else "s"} updated')
    if skipped:    parts.append(f'{skipped} skipped (missing title)')
    flash('Import complete — ' + (', '.join(parts) if parts else 'nothing new to import.'), 'success')
    return redirect(url_for('admin.dashboard'))


# ── Audio ZIP Export / Import ─────────────────────────────────────────────────

@admin_bp.route('/admin/export-audio')
@login_required
def export_audio():
    """Download all audio files as a ZIP for backup/migration."""
    audio_dir = _audio_upload_dir()
    buf = io.BytesIO()
    files_added = 0
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(audio_dir)):
            fpath = os.path.join(audio_dir, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, fname)
                files_added += 1
    if files_added == 0:
        flash('No audio files found to export.', 'warning')
        return redirect(url_for('admin.dashboard'))
    buf.seek(0)
    filename = f"shrikirtan_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return send_file(buf, mimetype='application/zip',
                     as_attachment=True, download_name=filename)


@admin_bp.route('/admin/import-audio', methods=['POST'])
@login_required
def import_audio():
    """Restore audio files from a previously exported ZIP."""
    f = request.files.get('audio_zip')
    if not f or not f.filename.lower().endswith('.zip'):
        flash('Please upload a valid .zip file.', 'danger')
        return redirect(url_for('admin.dashboard'))
    audio_dir = _audio_upload_dir()
    restored = skipped = 0
    try:
        with zipfile.ZipFile(f, 'r') as zf:
            for entry in zf.infolist():
                safe_name = os.path.basename(entry.filename)
                if not safe_name or entry.is_dir():
                    continue
                ext = safe_name.rsplit('.', 1)[-1].lower() if '.' in safe_name else ''
                if ext not in ALLOWED_AUDIO:
                    skipped += 1
                    continue
                dest = os.path.join(audio_dir, safe_name)
                with zf.open(entry) as src, open(dest, 'wb') as dst:
                    dst.write(src.read())
                restored += 1
    except zipfile.BadZipFile:
        flash('Invalid ZIP file — could not read archive.', 'danger')
        return redirect(url_for('admin.dashboard'))
    parts = [f'{restored} audio file{"s" if restored != 1 else ""} restored']
    if skipped:
        parts.append(f'{skipped} skipped (not an allowed audio format)')
    flash('Audio import complete — ' + ', '.join(parts) + '.', 'success')
    return redirect(url_for('admin.dashboard'))


# ── Site Manager CRUD ─────────────────────────────────────────────────────────

@admin_bp.route('/admin/managers')
@login_required
def managers():
    mgrs = SiteManager.query.order_by(SiteManager.username).all()
    return render_template('admin/managers.html', managers=mgrs)


@admin_bp.route('/admin/managers/add', methods=['POST'])
@login_required
def add_manager():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    if not username or not password:
        flash('Username and password are required.', 'danger')
    elif len(password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
    elif SiteManager.query.filter_by(username=username).first():
        flash(f'Manager "{username}" already exists.', 'warning')
    else:
        m = SiteManager(username=username)
        m.set_password(password)
        db.session.add(m)
        db.session.commit()
        flash(f'Site manager "{username}" created.', 'success')
    return redirect(url_for('admin.managers'))


@admin_bp.route('/admin/managers/delete/<int:manager_id>', methods=['POST'])
@login_required
def delete_manager(manager_id):
    m = db.get_or_404(SiteManager, manager_id)
    name = m.username
    db.session.delete(m)
    db.session.commit()
    flash(f'Site manager "{name}" deleted.', 'info')
    return redirect(url_for('admin.managers'))


# ── Events ────────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/events')
@login_required
def events():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo('America/Los_Angeles')).date()
    ev_list = Event.query.order_by(Event.sort_order, Event.id).all()
    return render_template('admin/events.html', events=ev_list, today=today)


@admin_bp.route('/admin/event/field/<int:event_id>', methods=['POST'])
@login_required
def event_field(event_id):
    event = db.get_or_404(Event, event_id)
    data  = request.get_json(silent=True) or {}
    field = data.get('field')
    value = data.get('value')
    try:
        if field == 'sort_order':
            event.sort_order = int(value)
        elif field == 'title_en':
            event.title_en = (value or '').strip()
        elif field == 'title_gu':
            event.title_gu = (value or '').strip()
        elif field == 'desc_en':
            event.desc_en = (value or '').strip()
        elif field == 'desc_gu':
            event.desc_gu = (value or '').strip()
        elif field == 'expiry_date':
            from datetime import date
            event.expiry_date = date.fromisoformat(value) if value else None
        elif field == 'is_active':
            event.is_active = bool(value)
        else:
            return jsonify({'ok': False, 'error': 'Unknown field'}), 400
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 400


@admin_bp.route('/admin/events/add', methods=['GET', 'POST'])
@login_required
def add_event():
    if request.method == 'POST':
        title_en = request.form.get('title_en', '').strip()
        title_gu = request.form.get('title_gu', '').strip()
        desc_en  = request.form.get('desc_en', '').strip()
        desc_gu  = request.form.get('desc_gu', '').strip()
        try:
            sort_order = int(request.form.get('sort_order', 0))
        except ValueError:
            sort_order = 0
        is_active = request.form.get('is_active') == 'on'
        from datetime import date as _date
        expiry_raw = request.form.get('expiry_date', '').strip()
        expiry_date = _date.fromisoformat(expiry_raw) if expiry_raw else None

        event = Event(
            title_en=title_en, title_gu=title_gu,
            desc_en=desc_en, desc_gu=desc_gu,
            sort_order=sort_order, is_active=is_active,
            expiry_date=expiry_date,
        )
        db.session.add(event)
        db.session.flush()

        f = request.files.get('image_file')
        if f and f.filename:
            save_ext, err = _validate_image(f)
            if err:
                db.session.rollback()
                flash(err, 'danger')
                return render_template('admin/event_form.html', event=None, action='Add')
            fname = f'{uuid.uuid4().hex}.{save_ext}'
            f.save(os.path.join(_uploads_dir(), fname))
            event.image_filename = fname

        db.session.commit()
        flash('Event added.', 'success')
        return redirect(url_for('admin.events'))

    return render_template('admin/event_form.html', event=None, action='Add')


@admin_bp.route('/admin/events/edit/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = db.get_or_404(Event, event_id)
    if request.method == 'POST':
        event.title_en = request.form.get('title_en', '').strip()
        event.title_gu = request.form.get('title_gu', '').strip()
        event.desc_en  = request.form.get('desc_en', '').strip()
        event.desc_gu  = request.form.get('desc_gu', '').strip()
        try:
            event.sort_order = int(request.form.get('sort_order', 0))
        except ValueError:
            event.sort_order = 0
        event.is_active = request.form.get('is_active') == 'on'
        from datetime import date as _date
        expiry_raw = request.form.get('expiry_date', '').strip()
        event.expiry_date = _date.fromisoformat(expiry_raw) if expiry_raw else None

        f = request.files.get('image_file')
        if f and f.filename:
            save_ext, err = _validate_image(f)
            if err:
                flash(err, 'danger')
                return render_template('admin/event_form.html', event=event, action='Edit')
            if event.image_filename:
                old_path = os.path.join(_uploads_dir(), event.image_filename)
                try:
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                except OSError:
                    pass
            fname = f'{uuid.uuid4().hex}.{save_ext}'
            f.save(os.path.join(_uploads_dir(), fname))
            event.image_filename = fname

        if request.form.get('delete_image') == '1' and event.image_filename:
            old_path = os.path.join(_uploads_dir(), event.image_filename)
            try:
                if os.path.isfile(old_path):
                    os.remove(old_path)
            except OSError:
                pass
            event.image_filename = None

        db.session.commit()
        flash('Event updated.', 'success')
        return redirect(url_for('admin.events'))

    return render_template('admin/event_form.html', event=event, action='Edit')


@admin_bp.route('/admin/events/delete/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    event = db.get_or_404(Event, event_id)
    if event.image_filename:
        path = os.path.join(_uploads_dir(), event.image_filename)
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted.', 'info')
    return redirect(url_for('admin.events'))
