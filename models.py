from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ============================================
# USER MODELS
# ============================================

class Admin(UserMixin, db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Collector(UserMixin, db.Model):
    __tablename__ = 'collectors'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class House(UserMixin, db.Model):
    __tablename__ = 'houses'
    id = db.Column(db.Integer, primary_key=True)
    house_no = db.Column(db.String(20), unique=True, nullable=False)
    owner_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    password = db.Column(db.String(255), nullable=False)
    monthly_maintenance = db.Column(db.Float, default=2000)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SecurityGuard(UserMixin, db.Model):
    __tablename__ = 'security_guards'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    shift = db.Column(db.String(20), default='Morning')
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================
# PAYMENT MODELS
# ============================================

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('houses.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    method = db.Column(db.String(20))
    payment_date = db.Column(db.Date, nullable=False)
    receipt_no = db.Column(db.String(50))
    collector_id = db.Column(db.Integer, db.ForeignKey('collectors.id'))
    status = db.Column(db.String(20), default='Paid')
    
    # Relationships
    house = db.relationship('House', backref=db.backref('payments', lazy=True))
    collector = db.relationship('Collector', backref=db.backref('collections', lazy=True))

# ============================================
# ACCOUNTING MODELS
# ============================================

class AccountHead(db.Model):
    __tablename__ = 'account_heads'
    id = db.Column(db.Integer, primary_key=True)
    head_name = db.Column(db.String(100), nullable=False)
    head_type = db.Column(db.Enum('income', 'expense'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    transaction_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    head_id = db.Column(db.Integer, db.ForeignKey('account_heads.id'))
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.Enum('credit', 'debit'), nullable=False)
    payment_method = db.Column(db.String(20))
    reference_id = db.Column(db.Integer)
    created_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    head = db.relationship('AccountHead', backref=db.backref('transactions', lazy=True))

class OpeningBalance(db.Model):
    __tablename__ = 'opening_balance'
    id = db.Column(db.Integer, primary_key=True)
    balance_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================
# VISITOR MODELS
# ============================================

class Visitor(db.Model):
    __tablename__ = 'visitors'
    id = db.Column(db.Integer, primary_key=True)
    resident_id = db.Column(db.Integer, db.ForeignKey('houses.id'))
    resident_name = db.Column(db.String(100))
    resident_house = db.Column(db.String(20))
    visitor_name = db.Column(db.String(100), nullable=False)
    visitor_phone = db.Column(db.String(15))
    visitor_vehicle = db.Column(db.String(50))
    purpose = db.Column(db.Text)
    expected_date = db.Column(db.Date)
    expected_time = db.Column(db.Time)
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)
    request_type = db.Column(db.Enum('resident_to_security', 'security_to_resident'), default='resident_to_security')
    status = db.Column(db.String(20), default='pending')
    security_remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    resident = db.relationship('House', backref=db.backref('visitors', lazy=True))

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    user_type = db.Column(db.Enum('resident', 'security', 'admin'), nullable=False)
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    visitor_id = db.Column(db.Integer)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================
# COMPLAINT MODELS
# ============================================

class Complaint(db.Model):
    __tablename__ = 'complaints'
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('houses.id'))
    complaint_type = db.Column(db.String(50))
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    remarks = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_date = db.Column(db.DateTime)
    
    # Relationship
    house = db.relationship('House', backref=db.backref('complaints', lazy=True))

class ComplaintSetting(db.Model):
    __tablename__ = 'complaints_settings'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='active')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================
# ANNOUNCEMENT MODEL
# ============================================

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
