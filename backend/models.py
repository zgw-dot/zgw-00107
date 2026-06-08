from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class MaterialBatch(db.Model):
    __tablename__ = 'material_batches'
    id = db.Column(db.Integer, primary_key=True)
    batch_no = db.Column(db.String(100), unique=True, nullable=False)
    material_name = db.Column(db.String(200), nullable=False)
    specification = db.Column(db.String(200))
    total_quantity = db.Column(db.Integer, nullable=False, default=0)
    available_quantity = db.Column(db.Integer, nullable=False, default=0)
    unit = db.Column(db.String(20), nullable=False)
    production_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    warehouse_location = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='normal')
    supplier = db.Column(db.String(200))
    remark = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    creator = db.relationship('User', foreign_keys=[created_by])

    def is_expired(self):
        return datetime.now().date() > self.expiry_date

    def to_dict(self):
        return {
            'id': self.id,
            'batch_no': self.batch_no,
            'material_name': self.material_name,
            'specification': self.specification,
            'total_quantity': self.total_quantity,
            'available_quantity': self.available_quantity,
            'unit': self.unit,
            'production_date': self.production_date.strftime('%Y-%m-%d'),
            'expiry_date': self.expiry_date.strftime('%Y-%m-%d'),
            'warehouse_location': self.warehouse_location,
            'status': self.status,
            'is_expired': self.is_expired(),
            'supplier': self.supplier,
            'remark': self.remark,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class BorrowOrder(db.Model):
    __tablename__ = 'borrow_orders'
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending_approval')
    purpose = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    received_at = db.Column(db.DateTime)
    returned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    returned_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    creator = db.relationship('User', foreign_keys=[created_by])
    approver = db.relationship('User', foreign_keys=[approved_by])
    receiver = db.relationship('User', foreign_keys=[received_by])
    returner = db.relationship('User', foreign_keys=[returned_by])
    items = db.relationship('BorrowItem', backref='order', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='borrow_order', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'status': self.status,
            'status_text': self.get_status_text(),
            'purpose': self.purpose,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else '',
            'approved_by': self.approved_by,
            'approver_name': self.approver.username if self.approver else '',
            'approved_at': self.approved_at.strftime('%Y-%m-%d %H:%M:%S') if self.approved_at else '',
            'received_by': self.received_by,
            'receiver_name': self.receiver.username if self.receiver else '',
            'received_at': self.received_at.strftime('%Y-%m-%d %H:%M:%S') if self.received_at else '',
            'returned_by': self.returned_by,
            'returner_name': self.returner.username if self.returner else '',
            'returned_at': self.returned_at.strftime('%Y-%m-%d %H:%M:%S') if self.returned_at else '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'items': [item.to_dict() for item in self.items]
        }

    def get_status_text(self):
        status_map = {
            'pending_approval': '待审批',
            'approved': '待领用',
            'rejected': '已拒绝',
            'received': '使用中',
            'returned': '已归还',
            'damaged': '已报损'
        }
        return status_map.get(self.status, self.status)


class BorrowItem(db.Model):
    __tablename__ = 'borrow_items'
    id = db.Column(db.Integer, primary_key=True)
    borrow_order_id = db.Column(db.Integer, db.ForeignKey('borrow_orders.id'), nullable=False)
    material_batch_id = db.Column(db.Integer, db.ForeignKey('material_batches.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    returned_quantity = db.Column(db.Integer, nullable=False, default=0)
    damaged_quantity = db.Column(db.Integer, nullable=False, default=0)

    batch = db.relationship('MaterialBatch')

    def to_dict(self):
        return {
            'id': self.id,
            'borrow_order_id': self.borrow_order_id,
            'material_batch_id': self.material_batch_id,
            'batch_no': self.batch.batch_no if self.batch else '',
            'material_name': self.batch.material_name if self.batch else '',
            'specification': self.batch.specification if self.batch else '',
            'unit': self.batch.unit if self.batch else '',
            'quantity': self.quantity,
            'returned_quantity': self.returned_quantity,
            'damaged_quantity': self.damaged_quantity,
            'warehouse_location': self.batch.warehouse_location if self.batch else ''
        }


class StockTake(db.Model):
    __tablename__ = 'stock_takes'
    id = db.Column(db.Integer, primary_key=True)
    stock_take_no = db.Column(db.String(50), unique=True, nullable=False)
    material_batch_id = db.Column(db.Integer, db.ForeignKey('material_batches.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending_confirm')
    expected_quantity = db.Column(db.Integer, nullable=False)
    actual_quantity = db.Column(db.Integer)
    difference_quantity = db.Column(db.Integer, default=0)
    difference_reason = db.Column(db.Text)
    handling_opinion = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    confirmed_at = db.Column(db.DateTime)
    cancelled_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    cancelled_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    batch = db.relationship('MaterialBatch', foreign_keys=[material_batch_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    confirmer = db.relationship('User', foreign_keys=[confirmed_by])
    canceller = db.relationship('User', foreign_keys=[cancelled_by])
    audit_logs = db.relationship('AuditLog', backref='stock_take', cascade='all, delete-orphan')

    def get_status_text(self):
        status_map = {
            'pending_confirm': '待确认',
            'confirmed': '已确认',
            'cancelled': '已撤销'
        }
        return status_map.get(self.status, self.status)

    def to_dict(self):
        return {
            'id': self.id,
            'stock_take_no': self.stock_take_no,
            'material_batch_id': self.material_batch_id,
            'batch_no': self.batch.batch_no if self.batch else '',
            'material_name': self.batch.material_name if self.batch else '',
            'specification': self.batch.specification if self.batch else '',
            'unit': self.batch.unit if self.batch else '',
            'status': self.status,
            'status_text': self.get_status_text(),
            'expected_quantity': self.expected_quantity,
            'actual_quantity': self.actual_quantity,
            'difference_quantity': self.difference_quantity,
            'difference_reason': self.difference_reason,
            'handling_opinion': self.handling_opinion,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else '',
            'confirmed_by': self.confirmed_by,
            'confirmer_name': self.confirmer.username if self.confirmer else '',
            'confirmed_at': self.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if self.confirmed_at else '',
            'cancelled_by': self.cancelled_by,
            'canceller_name': self.canceller.username if self.canceller else '',
            'cancelled_at': self.cancelled_at.strftime('%Y-%m-%d %H:%M:%S') if self.cancelled_at else '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    borrow_order_id = db.Column(db.Integer, db.ForeignKey('borrow_orders.id'))
    material_batch_id = db.Column(db.Integer, db.ForeignKey('material_batches.id'))
    stock_take_id = db.Column(db.Integer, db.ForeignKey('stock_takes.id'))
    action = db.Column(db.String(50), nullable=False)
    action_text = db.Column(db.String(100), nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    old_status = db.Column(db.String(50))
    new_status = db.Column(db.String(50))
    old_quantity = db.Column(db.Integer)
    new_quantity = db.Column(db.Integer)
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    operator = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'borrow_order_id': self.borrow_order_id,
            'material_batch_id': self.material_batch_id,
            'stock_take_id': self.stock_take_id,
            'action': self.action,
            'action_text': self.action_text,
            'operator_id': self.operator_id,
            'operator_name': self.operator.username if self.operator else '',
            'reason': self.reason,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'old_quantity': self.old_quantity,
            'new_quantity': self.new_quantity,
            'detail': self.detail,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
