import io
from flask import Blueprint, render_template, send_file, request, jsonify
from ..models import Bhajan, Category, Setting
import qrcode

public_bp = Blueprint('public', __name__)

PER_PAGE = 30


@public_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    categories = Category.query.order_by(Category.display_order, Category.name).all()
    pagination = (
        Bhajan.query
        .filter_by(is_active=True)
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
    if not q:
        return jsonify([])

    query = Bhajan.query.filter(
        Bhajan.is_active == True,
        Bhajan.title_english.ilike(f'%{q}%')
    )
    if cat_id and cat_id.isdigit():
        query = query.filter(Bhajan.category_id == int(cat_id))

    results = query.order_by(Bhajan.display_order, Bhajan.id).limit(100).all()
    return jsonify([{
        'title_gujarati': b.title_gujarati,
        'title_english':  b.title_english,
        'category':       b.category.name if b.category else None,
        'category_id':    b.category_id,
        'url':            f'/bhajan/{b.slug}',
    } for b in results])


@public_bp.route('/bhajan/<slug>')
def view_bhajan(slug):
    bhajan = Bhajan.query.filter_by(slug=slug, is_active=True).first_or_404()
    bhajans = (
        Bhajan.query
        .filter_by(is_active=True)
        .order_by(Bhajan.display_order, Bhajan.id)
        .all()
    )
    return render_template('bhajan.html', bhajan=bhajan, bhajans=bhajans)


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
