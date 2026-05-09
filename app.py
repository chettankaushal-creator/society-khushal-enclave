from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://username:password@localhost/society_payments'
db = SQLAlchemy(app)

# Models
class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    password = db.Column(db.String(255))

class Houses(db.Model):
    __tablename__ = 'houses'
    id = db.Column(db.Integer, primary_key=True)
    house_no = db.Column(db.String(20))
    owner_name = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    password = db.Column(db.String(255))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check Admin
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.password == password:
            session['role'] = 'admin'
            session['user_id'] = admin.id
            return redirect(url_for('admin_dashboard'))
        
        # Check Resident
        resident = Houses.query.filter_by(house_no=username).first()
        if resident and resident.password == password:
            session['role'] = 'user'
            session['user_id'] = resident.id
            return redirect(url_for('user_dashboard'))
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin/dashboard.html')

@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    return render_template('user/dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)
