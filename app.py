import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, Admin, Collector, House, SecurityGuard
from werkzeug.security import check_password_hash

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import blueprints
from admin.routes import admin_bp
from collector.routes import collector_bp
from user.routes import user_bp
from security.routes import security_bp

# Register blueprints with URL prefixes
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(collector_bp, url_prefix='/collector')
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(security_bp, url_prefix='/security')

# ============================================
# USER LOADER FOR FLASK-LOGIN
# ============================================

@login_manager.user_loader
def load_user(user_id):
    # Check in all tables - simpler approach using session role
    if 'role' in session:
        if session['role'] == 'admin':
            return Admin.query.get(int(user_id))
        elif session['role'] == 'collector':
            return Collector.query.get(int(user_id))
        elif session['role'] == 'user':
            return House.query.get(int(user_id))
        elif session['role'] == 'security':
            return SecurityGuard.query.get(int(user_id))
    return None

# ============================================
# MAIN ROUTES
# ============================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check Admin
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.password == password:
            login_user(admin)
            session['role'] = 'admin'
            session['user_id'] = admin.id
            return redirect(url_for('admin.dashboard'))
        
        # Check Collector
        collector = Collector.query.filter_by(username=username, is_active=True).first()
        if collector and collector.password == password:
            login_user(collector)
            session['role'] = 'collector'
            session['user_id'] = collector.id
            return redirect(url_for('collector.dashboard'))
        
        # Check Resident (using house number as username)
        resident = House.query.filter_by(house_no=username).first()
        if resident and resident.password == password:
            login_user(resident)
            session['role'] = 'user'
            session['user_id'] = resident.id
            session['user_name'] = resident.owner_name
            session['user_house'] = resident.house_no
            return redirect(url_for('user.dashboard'))
        
        # Check Security
        security = SecurityGuard.query.filter_by(username=username, is_active=True).first()
        if security and security.password == password:
            login_user(security)
            session['role'] = 'security'
            session['user_id'] = security.id
            return redirect(url_for('security.dashboard'))
        
        flash('Invalid username or password!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

# ============================================
# CREATE TABLES (Run once)
# ============================================

@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Database tables created!')

# ============================================
# RUN APP
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
