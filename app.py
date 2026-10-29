import os
import csv
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, session, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Child, Redemption

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=90)

db_url = os.getenv('DATABASE_URL', 'sqlite:///local.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

    # Seed admin user
    if not User.query.filter_by(role='admin').first():
        admin = User(
            email=os.getenv('ADMIN_EMAIL', 'admin@kibanda.com'),
            password_hash=generate_password_hash(os.getenv('ADMIN_PASSWORD', 'changeme')),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()

    # --- THE HARD RESET FIX ---
    # This will forcefully clean the database if it has more than 50 children.
    # It deletes ALL meals (redemptions) and ALL children, then recreates the exact 50.
    if Child.query.count() != 50:
        print(f"Detected {Child.query.count()} children. Cleaning database...")
        
        # 1. Delete all meal records first (to avoid foreign key errors)
        db.session.query(Redemption).delete()
        
        # 2. Delete all children
        db.session.query(Child).delete()
        
        db.session.commit()
        
        # 3. Insert the exact 50 children
        for i in range(1, 51):
            uid = f"00000000-0000-0000-0000-{i:012d}"
            name = f"Child {i:02d}"
            db.session.add(Child(uuid=uid, name=name))
        db.session.commit()
        print("Database cleaned and reset to exactly 50 children.")
    else:
        print("Database already has exactly 50 children. No cleanup needed.")

# --- The rest of the app.py code remains exactly the same as before ---
# (Copy the remaining functions from the previous app.py code you have,
# starting from `def login_required(roles=None):` down to the end)

def login_required(roles=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = session.get('user')
            if not user:
                return redirect(url_for('login', next=request.url))
            if roles and user['role'] not in roles:
                return "Forbidden: You do not have permission to view this page.", 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/')
def index():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    if user['role'] == 'admin':
        return redirect(url_for('dashboard'))
    return redirect(url_for('scan_page'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session.permanent = True
            session['user'] = {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'hotel_id': user.hotel_id
            }
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            if user.role == 'admin':
                return redirect(url_for('dashboard'))
            return redirect(url_for('scan_page'))
        error = "Invalid email or password"
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/scan')
@app.route('/scan/<child_uuid>')
@login_required(roles=['hotel', 'admin'])
def scan_page(child_uuid=None):
    hotel_id = session['user'].get('hotel_id') or 'default_hotel'
    scanned_child = child_uuid or request.args.get('child', '')
    return render_template('scan.html', hotel_id=hotel_id, scanned_child=scanned_child)

@app.route('/admin')
@login_required(roles=['admin'])
def dashboard():
    return render_template('admin.html')

@app.route('/api/roster')
@login_required(roles=['hotel', 'admin'])
def get_roster():
    children = Child.query.all()
    return jsonify([{
        'uuid': c.uuid,
        'name': c.name,
        'last_meal_at': (c.last_meal_at.isoformat() + 'Z') if c.last_meal_at else None
    } for c in children])

@app.route('/api/sync', methods=['POST'])
@login_required(roles=['hotel', 'admin'])
def sync():
    payload = request.get_json(silent=True) or {}
    events = payload.get('events', [])
    hotel_id = session['user'].get('hotel_id') or 'unknown'
    processed = 0

    for e in events:
        if not e.get('event_id') or not e.get('child_uuid') or not e.get('scanned_at'):
            continue
        if Redemption.query.filter_by(event_id=e['event_id']).first():
            continue
        try:
            scanned_at = datetime.fromisoformat(e['scanned_at'].replace('Z', '+00:00'))
            if scanned_at.tzinfo is not None:
                scanned_at = scanned_at.replace(tzinfo=None)
        except Exception:
            scanned_at = datetime.utcnow()

        db.session.add(Redemption(
            event_id=e['event_id'],
            child_uuid=e['child_uuid'],
            hotel_id=hotel_id,
            scanned_at=scanned_at
        ))
        child = Child.query.filter_by(uuid=e['child_uuid']).first()
        if child and (not child.last_meal_at or scanned_at > child.last_meal_at):
            child.last_meal_at = scanned_at
        processed += 1

    db.session.commit()
    _flag_conflicts()
    return jsonify({'ok': True, 'processed': processed})

def _flag_conflicts():
    for child in Child.query.all():
        rows = Redemption.query.filter_by(child_uuid=child.uuid).order_by(Redemption.scanned_at).all()
        for i in range(1, len(rows)):
            if rows[i].scanned_at - rows[i - 1].scanned_at < timedelta(hours=24):
                rows[i].conflict = True
    db.session.commit()

@app.route('/api/admin/stats')
@login_required(roles=['admin'])
def admin_stats():
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return jsonify({
        'total_children': Child.query.count(),
        'meals_today': Redemption.query.filter(Redemption.scanned_at >= today_start).count(),
        'conflicts': Redemption.query.filter_by(conflict=True).count()
    })

@app.route('/api/users', methods=['GET', 'POST'])
@login_required(roles=['admin'])
def handle_users():
    if request.method == 'GET':
        users = User.query.all()
        return jsonify([{'email': u.email, 'role': u.role, 'hotel_id': u.hotel_id} for u in users])
    
    d = request.get_json(silent=True) or {}
    if not d.get('email') or not d.get('password'):
        return jsonify({'error': 'email and password required'}), 400
    if User.query.filter_by(email=d['email']).first():
        return jsonify({'error': 'user already exists'}), 400
    db.session.add(User(
        email=d['email'],
        password_hash=generate_password_hash(d['password']),
        role=d.get('role', 'hotel'),
        hotel_id=d.get('hotel_id')
    ))
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/sw.js')
def sw():
    resp = send_from_directory('static', 'sw.js', mimetype='application/javascript')
    resp.headers['Service-Worker-Allowed'] = '/'
    return resp

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)