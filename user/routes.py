from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from models import db, House, Payment, Visitor, Complaint

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    house = House.query.get(current_user.id)
    payments = Payment.query.filter_by(house_id=house.id).order_by(Payment.payment_date.desc()).limit(5).all()
    
    # Calculate pending months
    paid_months = [f"{p.month}-{p.year}" for p in Payment.query.filter_by(house_id=house.id).all()]
    total_paid = db.session.query(db.func.sum(Payment.amount)).filter_by(house_id=house.id).scalar() or 0
    
    return render_template('user/dashboard.html', 
                          house=house, 
                          payments=payments,
                          total_paid=total_paid,
                          paid_months=paid_months)

@user_bp.route('/send_visitor_request', methods=['GET', 'POST'])
@login_required
def send_visitor_request():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        visitor = Visitor(
            resident_id=current_user.id,
            resident_name=session.get('user_name'),
            resident_house=session.get('user_house'),
            visitor_name=request.form.get('visitor_name'),
            visitor_phone=request.form.get('visitor_phone'),
            visitor_vehicle=request.form.get('visitor_vehicle'),
            purpose=request.form.get('purpose'),
            expected_date=request.form.get('expected_date'),
            expected_time=request.form.get('expected_time'),
            request_type='resident_to_security'
        )
        db.session.add(visitor)
        db.session.commit()
        flash('Visitor request sent to security successfully!', 'success')
        return redirect(url_for('user.my_visitors'))
    
    return render_template('user/send_visitor_request.html')

@user_bp.route('/my_visitors')
@login_required
def my_visitors():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    visitors = Visitor.query.filter_by(resident_id=current_user.id).order_by(Visitor.created_at.desc()).all()
    return render_template('user/my_visitors.html', visitors=visitors)

@user_bp.route('/payment_history')
@login_required
def payment_history():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    payments = Payment.query.filter_by(house_id=current_user.id).order_by(Payment.payment_date.desc()).all()
    return render_template('user/payment_history.html', payments=payments)

@user_bp.route('/pending_dues')
@login_required
def pending_dues():
    house = House.query.get(current_user.id)
    paid_months = [f"{p.month}-{p.year}" for p in Payment.query.filter_by(house_id=house.id).all()]
    
    months = ['January', 'February', 'March', 'April', 'May', 'June', 
              'July', 'August', 'September', 'October', 'November', 'December']
    
    pending = []
    for month in months:
        key = f"{month}-{2024}"
        if key not in paid_months:
            pending.append({'month': month, 'amount': house.monthly_maintenance})
    
    return render_template('user/pending_dues.html', pending=pending)

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    house = House.query.get(current_user.id)
    
    if request.method == 'POST':
        house.phone = request.form.get('phone')
        house.email = request.form.get('email')
        if request.form.get('password'):
            house.password = request.form.get('password')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user.profile'))
    
    return render_template('user/profile.html', house=house)

@user_bp.route('/logout')
def logout():
    return redirect(url_for('logout'))
