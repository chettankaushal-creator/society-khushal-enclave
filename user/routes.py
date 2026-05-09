from flask import Blueprint, render_template, redirect, url_for, flash, request, session, send_file
from flask_login import login_required, current_user
from models import db, House, Payment, Visitor, Complaint, Notification, Announcement
from datetime import datetime, date
import os

user_bp = Blueprint('user', __name__)

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_user_house():
    """Get the house object for current user"""
    return House.query.get(current_user.id)

def get_pending_months(house_id):
    """Calculate pending months for a house"""
    house = House.query.get(house_id)
    if not house:
        return []
    
    # Get paid months
    payments = Payment.query.filter_by(house_id=house_id).all()
    paid_months = [f"{p.month}-{p.year}" for p in payments]
    
    # Current year months (Jan to current month)
    months = ['January', 'February', 'March', 'April', 'May', 'June', 
              'July', 'August', 'September', 'October', 'November', 'December']
    current_month_index = datetime.now().month - 1
    pending = []
    
    for i in range(current_month_index + 1):
        month = months[i]
        year = datetime.now().year
        key = f"{month}-{year}"
        if key not in paid_months:
            pending.append({
                'month': month, 
                'year': year, 
                'amount': house.monthly_maintenance
            })
    
    return pending

# ============================================
# DASHBOARD ROUTE
# ============================================

@user_bp.route('/dashboard')
@login_required
def dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    house = get_user_house()
    
    # Get payment statistics
    payments = Payment.query.filter_by(house_id=house.id).order_by(Payment.payment_date.desc()).all()
    total_paid = db.session.query(db.func.sum(Payment.amount)).filter_by(house_id=house.id).scalar() or 0
    payment_count = len(payments)
    last_payment = payments[0] if payments else None
    
    # Get pending months
    pending_months = get_pending_months(house.id)
    total_pending_amount = sum(p['amount'] for p in pending_months)
    
    # Get recent payments (last 5)
    recent_payments = payments[:5]
    
    # Get unread notifications count
    notification_count = Notification.query.filter_by(
        user_id=house.id, 
        user_type='resident', 
        is_read=False
    ).count()
    
    # Get recent notifications
    notifications = Notification.query.filter_by(
        user_id=house.id, 
        user_type='resident'
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    # Get pending visitor requests (from security)
    pending_visitors = Visitor.query.filter_by(
        resident_id=house.id,
        request_type='security_to_resident',
        status='pending'
    ).order_by(Visitor.created_at.desc()).all()
    
    # Get recent complaints
    recent_complaints = Complaint.query.filter_by(
        house_id=house.id
    ).order_by(Complaint.created_date.desc()).limit(3).all()
    
    # Get announcements
    announcements = Announcement.query.order_by(Announcement.created_date.desc()).limit(3).all()
    
    # Payment trend for last 6 months
    payment_trend = []
    for i in range(5, -1, -1):
        month_date = datetime.now().replace(day=1) - pd.DateOffset(months=i)
        month_name = month_date.strftime('%b')
        year = month_date.year
        month_num = month_date.month
        
        payment = Payment.query.filter_by(
            house_id=house.id,
            month=month_name,
            year=year
        ).first()
        
        if payment:
            payment_trend.append({'month': month_name, 'amount': payment.amount, 'status': 'Paid'})
        elif month_num <= datetime.now().month:
            payment_trend.append({'month': month_name, 'amount': 0, 'status': 'Pending'})
    
    return render_template('user/dashboard.html',
                          house=house,
                          total_paid=total_paid,
                          payment_count=payment_count,
                          last_payment=last_payment,
                          pending_months=pending_months,
                          total_pending_amount=total_pending_amount,
                          recent_payments=recent_payments,
                          notifications=notifications,
                          notification_count=notification_count,
                          pending_visitors=pending_visitors,
                          recent_complaints=recent_complaints,
                          announcements=announcements,
                          payment_trend=payment_trend,
                          current_date=datetime.now().strftime('%d-%m-%Y'),
                          current_time=datetime.now().strftime('%I:%M %p'))

# ============================================
# VISITOR MANAGEMENT ROUTES
# ============================================

@user_bp.route('/send_visitor_request', methods=['GET', 'POST'])
@login_required
def send_visitor_request():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    house = get_user_house()
    
    if request.method == 'POST':
        visitor_name = request.form.get('visitor_name')
        visitor_phone = request.form.get('visitor_phone')
        visitor_vehicle = request.form.get('visitor_vehicle')
        purpose = request.form.get('purpose')
        expected_date = request.form.get('expected_date')
        expected_time = request.form.get('expected_time')
        
        if not visitor_name or not purpose:
            flash('Visitor name and purpose are required!', 'danger')
            return redirect(url_for('user.send_visitor_request'))
        
        visitor = Visitor(
            resident_id=house.id,
            resident_name=house.owner_name,
            resident_house=house.house_no,
            visitor_name=visitor_name,
            visitor_phone=visitor_phone,
            visitor_vehicle=visitor_vehicle,
            purpose=purpose,
            expected_date=datetime.strptime(expected_date, '%Y-%m-%d') if expected_date else None,
            expected_time=datetime.strptime(expected_time, '%H:%M').time() if expected_time else None,
            request_type='resident_to_security',
            status='pending'
        )
        
        db.session.add(visitor)
        db.session.commit()
        
        # Add notification for security (user_id 1 = security)
        notification = Notification(
            user_id=1,
            user_type='security',
            title='New Visitor Request',
            message=f'Resident {house.owner_name} ({house.house_no}) has requested visitor approval for {visitor_name}',
            visitor_id=visitor.id
        )
        db.session.add(notification)
        db.session.commit()
        
        flash('Visitor request sent to security successfully!', 'success')
        return redirect(url_for('user.my_visitors'))
    
    return render_template('user/send_visitor_request.html', house=house)

@user_bp.route('/my_visitors')
@login_required
def my_visitors():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    house = get_user_house()
    filter_type = request.args.get('filter', 'all')
    
    query = Visitor.query.filter_by(resident_id=house.id)
    
    if filter_type == 'pending':
        query = query.filter_by(status='pending')
    elif filter_type == 'approved':
        query = query.filter_by(status='approved')
    elif filter_type == 'rejected':
        query = query.filter_by(status='rejected')
    elif filter_type == 'checked_in':
        query = query.filter_by(status='checked_in')
    elif filter_type == 'checked_out':
        query = query.filter_by(status='checked_out')
    elif filter_type == 'sent':
        query = query.filter_by(request_type='resident_to_security')
    elif filter_type == 'received':
        query = query.filter_by(request_type='security_to_resident')
    
    visitors = query.order_by(Visitor.created_at.desc()).all()
    
    # Get counts for stats
    total_count = Visitor.query.filter_by(resident_id=house.id).count()
    pending_count = Visitor.query.filter_by(resident_id=house.id, status='pending').count()
    approved_count = Visitor.query.filter_by(resident_id=house.id, status='approved').count()
    rejected_count = Visitor.query.filter_by(resident_id=house.id, status='rejected').count()
    checked_in_count = Visitor.query.filter_by(resident_id=house.id, status='checked_in').count()
    checked_out_count = Visitor.query.filter_by(resident_id=house.id, status='checked_out').count()
    sent_count = Visitor.query.filter_by(resident_id=house.id, request_type='resident_to_security').count()
    received_count = Visitor.query.filter_by(resident_id=house.id, request_type='security_to_resident').count()
    
    return render_template('user/my_visitors.html',
                          visitors=visitors,
                          filter_type=filter_type,
                          total_count=total_count,
                          pending_count=pending_count,
                          approved_count=approved_count,
                          rejected_count=rejected_count,
                          checked_in_count=checked_in_count,
                          checked_out_count=checked_out_count,
                          sent_count=sent_count,
                          received_count=received_count)

@user_bp.route('/approve_visitor/<int:visitor_id>/<action>')
@login_required
def approve_visitor(visitor_id, action):
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    visitor = Visitor.query.get_or_404(visitor_id)
    house = get_user_house()
    
    if visitor.resident_id != house.id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('user.my_visitors'))
    
    if action == 'approve':
        visitor.status = 'approved'
        message = f'Resident {house.owner_name} has approved the visitor request'
    elif action == 'reject':
        visitor.status = 'rejected'
        message = f'Resident {house.owner_name} has rejected the visitor request'
    else:
        flash('Invalid action!', 'danger')
        return redirect(url_for('user.my_visitors'))
    
    db.session.commit()
    
    # Add notification for security
    notification = Notification(
        user_id=1,
        user_type='security',
        title=f'Visitor Request {action}d',
        message=message,
        visitor_id=visitor.id
    )
    db.session.add(notification)
    db.session.commit()
    
    flash(f'Visitor request {action}d successfully!', 'success')
    return redirect(url_for('user.my_visitors'))

# ============================================
# PAYMENT ROUTES
# ============================================

@user_bp.route('/payment_history')
@login_required
def payment_history():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    house = get_user_house()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    payments = Payment.query.filter_by(house_id=house.id)\
        .order_by(Payment.payment_date.desc())\
        .paginate(page=page, per_page=per_page)
    
    return render_template('user/payment_history.html', payments=payments)

@user_bp.route('/pending_dues')
@login_required
def pending_dues():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    house = get_user_house()
    pending_months = get_pending_months(house.id)
    total_pending = sum(p['amount'] for p in pending_months)
    
    return render_template('user/pending_dues.html', 
                          pending_months=pending_months, 
                          total_pending=total_pending,
                          monthly_maintenance=house.monthly_maintenance)

@user_bp.route('/view_receipt/<int:payment_id>')
@login_required
def view_receipt(payment_id):
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    payment = Payment.query.get_or_404(payment_id)
    house = get_user_house()
    
    if payment.house_id != house.id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('user.payment_history'))
    
    return render_template('user/receipt.html', payment=payment, house=house)

# ============================================
# COMPLAINT ROUTES
# ============================================

@user_bp.route('/complaints', methods=['GET', 'POST'])
@login_required
def complaints():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    house = get_user_house()
    
    if request.method == 'POST':
        complaint_type = request.form.get('complaint_type')
        description = request.form.get('description')
        
        if not complaint_type or not description:
            flash('Please fill all required fields!', 'danger')
            return redirect(url_for('user.complaints'))
        
        complaint = Complaint(
            house_id=house.id,
            complaint_type=complaint_type,
            description=description,
            status='Pending'
        )
        
        db.session.add(complaint)
        db.session.commit()
        
        flash('Complaint submitted successfully!', 'success')
        return redirect(url_for('user.complaints'))
    
    complaints_list = Complaint.query.filter_by(house_id=house.id)\
        .order_by(Complaint.created_date.desc()).all()
    
    return render_template('user/complaints.html', complaints=complaints_list)

# ============================================
# NOTIFICATION ROUTES
# ============================================

@user_bp.route('/notifications')
@login_required
def notifications():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    house = get_user_house()
    
    # Mark all as read
    Notification.query.filter_by(
        user_id=house.id, 
        user_type='resident', 
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    notifications_list = Notification.query.filter_by(
        user_id=house.id, 
        user_type='resident'
    ).order_by(Notification.created_at.desc()).all()
    
    return render_template('user/notifications.html', notifications=notifications_list)

@user_bp.route('/mark_notification_read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    house = get_user_house()
    
    if notification.user_id == house.id:
        notification.is_read = True
        db.session.commit()
    
    return redirect(url_for('user.notifications'))

# ============================================
# PROFILE ROUTES
# ============================================

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    house = get_user_house()
    
    if request.method == 'POST':
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')
        
        house.phone = phone
        house.email = email
        
        if password:
            house.password = password
        
        db.session.commit()
        
        # Update session
        session['user_phone'] = phone
        session['user_email'] = email
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user.profile'))
    
    return render_template('user/profile.html', house=house)

# ============================================
# MARK ALL NOTIFICATIONS READ
# ============================================

@user_bp.route('/read_all_notifications')
@login_required
def read_all_notifications():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    
    house = get_user_house()
    
    Notification.query.filter_by(
        user_id=house.id, 
        user_type='resident', 
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    flash('All notifications marked as read', 'success')
    return redirect(request.referrer or url_for('user.dashboard'))

# ============================================
# ADD THIS IMPORT AT THE TOP
# ============================================
# Add this import with the other imports at the top of the file
import pandas as pd  # For payment trend calculation (optional - remove if not needed)
