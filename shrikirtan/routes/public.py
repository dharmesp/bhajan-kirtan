import io
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, send_file, request, jsonify, abort
from sqlalchemy import or_
from ..models import Bhajan, Category, Setting, Event
import qrcode

public_bp = Blueprint('public', __name__)

PER_PAGE = 30


@public_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    categories = Category.query.order_by(Category.display_order, Category.name).all()
    pagination = (
        Bhajan.query
        .filter(Bhajan.is_active == True, Bhajan.is_visible == True)
        .order_by(Bhajan.display_order, Bhajan.id)
        .paginate(page=page, per_page=PER_PAGE, error_out=False)
    )
    return render_template('index.html',
                           bhajans=pagination.items,
                           pagination=pagination,
                           categories=categories)


@public_bp.route('/api/search')
def search_bhajans():
    q = request.args.get('q', '').strip()
    cat_id = request.args.get('cat', '', type=str)

    # Return empty only when both q and cat are absent
    if not q and not cat_id:
        return jsonify([])

    query = Bhajan.query.filter(Bhajan.is_active == True, Bhajan.is_visible == True)

    if q:
        query = query.filter(or_(
            Bhajan.title_english.ilike(f'%{q}%'),
            Bhajan.title_gujarati.contains(q)
        ))

    if cat_id and cat_id.isdigit():
        query = query.filter(Bhajan.categories.any(Category.id == int(cat_id)))

    results = query.order_by(Bhajan.display_order, Bhajan.id).limit(200).all()
    return jsonify([{
        'id':             b.id,
        'title_gujarati': b.title_gujarati,
        'title_english':  b.title_english,
        'categories':     [{'id': c.id, 'name': c.name} for c in b.categories],
        'url':            f'/bhajan/{b.slug}',
    } for b in results])


@public_bp.route('/bhajan/<slug>')
def view_bhajan(slug):
    bhajan = Bhajan.query.filter_by(slug=slug, is_active=True).first_or_404()
    bhajans = (
        Bhajan.query
        .filter(Bhajan.is_active == True, Bhajan.is_visible == True)
        .order_by(Bhajan.display_order, Bhajan.id)
        .all()
    )
    return render_template('bhajan.html', bhajan=bhajan, bhajans=bhajans)


@public_bp.route('/api/now-playing')
def now_playing():
    np_id = Setting.get('now_playing_id', '')
    np_at = Setting.get('now_playing_at', '')
    if not np_id or not np_at:
        return jsonify(None)
    try:
        ts = datetime.fromisoformat(np_at)
        if (datetime.utcnow() - ts).total_seconds() > 60:
            return jsonify(None)
    except (ValueError, TypeError):
        return jsonify(None)
    bhajan = Bhajan.query.filter_by(id=int(np_id), is_active=True).first()
    if not bhajan:
        return jsonify(None)
    return jsonify({
        'id':             bhajan.id,
        'slug':           bhajan.slug,
        'title_gujarati': bhajan.title_gujarati,
        'title_english':  bhajan.title_english,
    })


@public_bp.route('/qrcode.png')
def home_qrcode():
    domain = Setting.get('domain_name', '').rstrip('/')
    if not domain:
        domain = request.host_url.rstrip('/')

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(domain)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#92400e', back_color='white')

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', max_age=3600)


@public_bp.route('/bhajan/<slug>/qrcode.png')
def bhajan_qrcode(slug):
    bhajan = Bhajan.query.filter_by(slug=slug, is_active=True).first_or_404()
    domain = Setting.get('domain_name', '').rstrip('/')
    if not domain:
        domain = request.host_url.rstrip('/')
    url = f"{domain}/bhajan/{slug}"

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', max_age=3600)


@public_bp.route('/print-image/<int:slot>')
def print_image(slot):
    if slot not in (1, 2):
        abort(404)
    fname = Setting.get(f'print_image_{slot}', '')
    if not fname:
        abort(404)
    from flask import current_app
    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    base = '/data' if db_url.startswith('sqlite:////data/') else current_app.instance_path
    path = os.path.join(base, 'uploads', fname)
    if not os.path.isfile(path):
        abort(404)
    ext = fname.rsplit('.', 1)[-1].lower()
    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp'}
    return send_file(path, mimetype=mime_map.get(ext, 'image/png'), max_age=3600)


@public_bp.route('/api/events')
def api_events():
    ev_list = Event.query.filter_by(is_active=True).order_by(Event.sort_order, Event.id).all()
    return jsonify([{
        'id':        e.id,
        'title_en':  e.title_en,
        'title_gu':  e.title_gu,
        'desc_en':   e.desc_en,
        'desc_gu':   e.desc_gu,
        'image_url': f'/event-image/{e.id}' if e.image_filename else None,
    } for e in ev_list])


@public_bp.route('/event-image/<int:event_id>')
def event_image(event_id):
    event = Event.query.get_or_404(event_id)
    if not event.image_filename:
        abort(404)
    from flask import current_app
    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    base = '/data' if db_url.startswith('sqlite:////data/') else current_app.instance_path
    path = os.path.join(base, 'uploads', event.image_filename)
    if not os.path.isfile(path):
        abort(404)
    ext = event.image_filename.rsplit('.', 1)[-1].lower()
    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp'}
    return send_file(path, mimetype=mime_map.get(ext, 'image/png'), max_age=3600)
