from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from models import db, House, Payment, Transaction, AccountHead, OpeningBalance
from datetime import datetime, date

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    # Statistics
    total_houses = House.query.count()
    total_collections = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
    pending_count = House.query.filter(~House.payments.any()).count()
    
    # Monthly data for chart
    monthly_data = []
    for i in range(1, 13):
        amount = db.session.query(db.func.sum(Payment.amount)).filter(
            db.extract('month', Payment.payment_date) == i,
            db.extract('year', Payment.payment_date) == date.today().year
        ).scalar() or 0
        monthly_data.append(amount)
    
    return render_template('admin/dashboard.html', 
                          total_houses=total_houses,
                          total_collections=total_collections,
                          pending_count=pending_count,
                          monthly_data=monthly_data)

@admin_bp.route('/add_house', methods=['GET', 'POST'])
@login_required
def add_house():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        house_no = request.form.get('house_no')
        owner_name = request.form.get('owner_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        monthly_maintenance = request.form.get('monthly_maintenance', 2000)
        password = request.form.get('password')
        
        existing = House.query.filter_by(house_no=house_no).first()
        if existing:
            flash('House number already exists!', 'danger')
        else:
            house = House(
                house_no=house_no,
                owner_name=owner_name,
                phone=phone,
                email=email,
                monthly_maintenance=monthly_maintenance,
                password=password
            )
            db.session.add(house)
            db.session.commit()
            flash('House added successfully!', 'success')
            return redirect(url_for('admin.house_list'))
    
    return render_template('admin/add_house.html')

@admin_bp.route('/house_list')
@login_required
def house_list():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    search = request.args.get('search', '')
    query = House.query
    if search:
        query = query.filter(
            House.house_no.contains(search) | 
            House.owner_name.contains(search) |
            House.phone.contains(search)
        )
    houses = query.order_by(House.house_no).all()
    
    return render_template('admin/house_list.html', houses=houses, search=search)

@admin_bp.route('/edit_house/<int:id>', methods=['POST'])
@login_required
def edit_house(id):
    house = House.query.get_or_404(id)
    house.house_no = request.form.get('house_no')
    house.owner_name = request.form.get('owner_name')
    house.phone = request.form.get('phone')
    house.email = request.form.get('email')
    house.monthly_maintenance = request.form.get('monthly_maintenance')
    
    if request.form.get('password'):
        house.password = request.form.get('password')
    
    db.session.commit()
    flash('House updated successfully!', 'success')
    return redirect(url_for('admin.house_list'))

@admin_bp.route('/delete_house/<int:id>')
@login_required
def delete_house(id):
    house = House.query.get_or_404(id)
    
    # Check if has payments
    if house.payments:
        flash('Cannot delete house with existing payment records!', 'danger')
    else:
        db.session.delete(house)
        db.session.commit()
        flash('House deleted successfully!', 'success')
    
    return redirect(url_for('admin.house_list'))

@admin_bp.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    expense_heads = AccountHead.query.filter_by(head_type='expense').all()
    
    if request.method == 'POST':
        transaction = Transaction(
            transaction_date=datetime.strptime(request.form.get('date'), '%Y-%m-%d'),
            description=request.form.get('description'),
            head_id=request.form.get('head_id'),
            amount=request.form.get('amount'),
            type='debit',
            payment_method=request.form.get('payment_method'),
            created_by=current_user.id
        )
        db.session.add(transaction)
        db.session.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('admin.account_summary'))
    
    return render_template('admin/add_expense.html', expense_heads=expense_heads)

@admin_bp.route('/account_summary')
@login_required
def account_summary():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    from_date = request.args.get('from', date.today().replace(day=1).isoformat())
    to_date = request.args.get('to', date.today().isoformat())
    
    opening = OpeningBalance.query.order_by(OpeningBalance.balance_date.desc()).first()
    opening_balance = opening.amount if opening else 0
    
    total_credit = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.type == 'credit',
        Transaction.transaction_date.between(from_date, to_date)
    ).scalar() or 0
    
    total_debit = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.type == 'debit',
        Transaction.transaction_date.between(from_date, to_date)
    ).scalar() or 0
    
    transactions = Transaction.query.filter(
        Transaction.transaction_date.between(from_date, to_date)
    ).order_by(Transaction.transaction_date.desc()).all()
    
    return render_template('admin/account_summary.html',
                          opening_balance=opening_balance,
                          total_credit=total_credit,
                          total_debit=total_debit,
                          net_profit=total_credit - total_debit,
                          closing_balance=opening_balance + total_credit - total_debit,
                          transactions=transactions,
                          from_date=from_date,
                          to_date=to_date)

@admin_bp.route('/logout')
def logout():
    return redirect(url_for('logout'))
