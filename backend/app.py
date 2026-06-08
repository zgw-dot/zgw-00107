import os
from datetime import datetime, date
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from models import db, User, MaterialBatch, BorrowOrder, BorrowItem, AuditLog, StockTake
import pandas as pd
from io import BytesIO, StringIO

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'emergency-material-system-secret-key-2024'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400

CORS(app, supports_credentials=True)
jwt = JWTManager(app)
db.init_app(app)


def generate_order_no():
    today = datetime.now().strftime('%Y%m%d')
    count = BorrowOrder.query.filter(BorrowOrder.order_no.like(f'BY{today}%')).count()
    return f'BY{today}{count + 1:04d}'


def add_audit_log(order_id=None, batch_id=None, stock_take_id=None, action='', action_text='', operator_id=None, reason='', old_status=None, new_status=None, old_quantity=None, new_quantity=None, detail=''):
    log = AuditLog(
        borrow_order_id=order_id,
        material_batch_id=batch_id,
        stock_take_id=stock_take_id,
        action=action,
        action_text=action_text,
        operator_id=operator_id,
        reason=reason,
        old_status=old_status,
        new_status=new_status,
        old_quantity=old_quantity,
        new_quantity=new_quantity,
        detail=detail
    )
    db.session.add(log)
    db.session.flush()


def generate_stock_take_no():
    today = datetime.now().strftime('%Y%m%d')
    count = StockTake.query.filter(StockTake.stock_take_no.like(f'PD{today}%')).count()
    return f'PD{today}{count + 1:04d}'


def check_batch_conflicts(batch_id, exclude_stock_take_id=None):
    conflicts = []
    
    pending_stock_take_query = StockTake.query.filter_by(
        material_batch_id=batch_id,
        status='pending_confirm'
    )
    if exclude_stock_take_id:
        pending_stock_take_query = pending_stock_take_query.filter(StockTake.id != exclude_stock_take_id)
    
    pending_stock_take = pending_stock_take_query.first()
    if pending_stock_take:
        conflicts.append(f'该批次存在未完成的盘点单：{pending_stock_take.stock_take_no}，请先处理后再发起新盘点')
    
    pending_orders = BorrowOrder.query.join(BorrowItem).filter(
        BorrowItem.material_batch_id == batch_id,
        BorrowOrder.status.in_(['pending_approval', 'approved', 'received'])
    ).all()
    
    for order in pending_orders:
        if order.status == 'pending_approval':
            conflicts.append(f'该批次存在待审批借用单：{order.order_no}')
        elif order.status == 'approved':
            conflicts.append(f'该批次存在待领用借用单：{order.order_no}')
        elif order.status == 'received':
            for item in order.items:
                if item.material_batch_id == batch_id and (item.quantity - item.returned_quantity - item.damaged_quantity) > 0:
                    conflicts.append(f'该批次存在未完成借用：借用单 {order.order_no}，未归还数量 {item.quantity - item.returned_quantity - item.damaged_quantity}')
                    break
    
    return conflicts


def require_warehouse_keeper():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user or user.role != 'warehouse_keeper':
        return jsonify({'message': '只有仓库管理员可以执行此操作'}), 403
    return None


def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='warehouse_keeper')
            admin.set_password('admin123')
            db.session.add(admin)

        if not User.query.filter_by(username='duty').first():
            duty = User(username='duty', role='duty_officer')
            duty.set_password('duty123')
            db.session.add(duty)

        db.session.commit()
        print('Database initialized with default users.')


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'message': '用户名或密码错误'}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    })


@app.route('/api/auth/user', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': '用户不存在'}), 404
    return jsonify(user.to_dict())


@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])


@app.route('/api/batches', methods=['GET'])
@jwt_required()
def get_batches():
    batches = MaterialBatch.query.order_by(MaterialBatch.created_at.desc()).all()
    result = []
    for b in batches:
        batch_dict = b.to_dict()
        pending_count = StockTake.query.filter_by(
            material_batch_id=b.id,
            status='pending_confirm'
        ).count()
        confirmed_count = StockTake.query.filter_by(
            material_batch_id=b.id,
            status='confirmed'
        ).count()
        cancelled_count = StockTake.query.filter_by(
            material_batch_id=b.id,
            status='cancelled'
        ).count()
        diff_count = db.session.query(db.func.sum(StockTake.difference_quantity)).filter_by(
            material_batch_id=b.id,
            status='confirmed'
        ).scalar() or 0
        batch_dict['pending_stock_take_count'] = pending_count
        batch_dict['confirmed_stock_take_count'] = confirmed_count
        batch_dict['cancelled_stock_take_count'] = cancelled_count
        batch_dict['total_difference_quantity'] = diff_count
        result.append(batch_dict)
    return jsonify(result)


@app.route('/api/batches/available', methods=['GET'])
@jwt_required()
def get_available_batches():
    batches = MaterialBatch.query.filter(
        MaterialBatch.available_quantity > 0,
        MaterialBatch.status == 'normal'
    ).order_by(MaterialBatch.created_at.desc()).all()
    result = []
    for b in batches:
        if not b.is_expired():
            result.append(b.to_dict())
    return jsonify(result)


@app.route('/api/batches', methods=['POST'])
@jwt_required()
def create_batch():
    auth_err = require_warehouse_keeper()
    if auth_err:
        return auth_err
    user_id = int(get_jwt_identity())
    data = request.get_json()

    existing = MaterialBatch.query.filter_by(batch_no=data['batch_no']).first()
    if existing:
        return jsonify({'message': f'批次号 {data["batch_no"]} 已存在'}), 400

    try:
        prod_date = datetime.strptime(data['production_date'], '%Y-%m-%d').date()
        exp_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
    except:
        return jsonify({'message': '日期格式错误'}), 400

    if exp_date < prod_date:
        return jsonify({'message': '有效期不能早于生产日期'}), 400

    batch = MaterialBatch(
        batch_no=data['batch_no'],
        material_name=data['material_name'],
        specification=data.get('specification', ''),
        total_quantity=int(data['total_quantity']),
        available_quantity=int(data['total_quantity']),
        unit=data['unit'],
        production_date=prod_date,
        expiry_date=exp_date,
        warehouse_location=data['warehouse_location'],
        supplier=data.get('supplier', ''),
        remark=data.get('remark', ''),
        created_by=user_id
    )
    db.session.add(batch)
    db.session.flush()

    add_audit_log(
        batch_id=batch.id,
        action='create_batch',
        action_text='创建批次',
        operator_id=user_id,
        reason=data.get('reason', '系统初始化入库'),
        detail=f'创建批次 {batch.batch_no}，物资 {batch.material_name}，数量 {batch.total_quantity}{batch.unit}'
    )

    db.session.commit()
    return jsonify(batch.to_dict())


@app.route('/api/batches/<int:batch_id>', methods=['GET'])
@jwt_required()
def get_batch_detail(batch_id):
    batch = MaterialBatch.query.get(batch_id)
    if not batch:
        return jsonify({'message': '批次不存在'}), 404

    logs = AuditLog.query.filter_by(material_batch_id=batch_id).order_by(AuditLog.created_at.desc()).all()
    stock_takes = StockTake.query.filter_by(material_batch_id=batch_id).order_by(StockTake.created_at.desc()).all()

    return jsonify({
        'batch': batch.to_dict(),
        'audit_logs': [l.to_dict() for l in logs],
        'stock_takes': [st.to_dict() for st in stock_takes]
    })


@app.route('/api/batches/<int:batch_id>/rotate', methods=['POST'])
@jwt_required()
def rotate_batch(batch_id):
    auth_err = require_warehouse_keeper()
    if auth_err:
        return auth_err
    user_id = int(get_jwt_identity())
    data = request.get_json()
    reason = data.get('reason', '').strip()
    if not reason:
        return jsonify({'message': '轮换原因不能为空'}), 400

    batch = MaterialBatch.query.get(batch_id)
    if not batch:
        return jsonify({'message': '批次不存在'}), 404

    new_batch_data = data.get('new_batch', {})
    if not new_batch_data:
        return jsonify({'message': '新批次信息不能为空'}), 400

    existing = MaterialBatch.query.filter_by(batch_no=new_batch_data['batch_no']).first()
    if existing:
        return jsonify({'message': f'新批次号 {new_batch_data["batch_no"]} 已存在'}), 400

    old_batch_no = batch.batch_no
    old_quantity = batch.available_quantity

    batch.status = 'rotated'
    batch.available_quantity = 0

    try:
        prod_date = datetime.strptime(new_batch_data['production_date'], '%Y-%m-%d').date()
        exp_date = datetime.strptime(new_batch_data['expiry_date'], '%Y-%m-%d').date()
    except:
        db.session.rollback()
        return jsonify({'message': '日期格式错误'}), 400

    new_batch = MaterialBatch(
        batch_no=new_batch_data['batch_no'],
        material_name=batch.material_name,
        specification=batch.specification,
        total_quantity=old_quantity,
        available_quantity=old_quantity,
        unit=batch.unit,
        production_date=prod_date,
        expiry_date=exp_date,
        warehouse_location=batch.warehouse_location,
        supplier=batch.supplier,
        remark=new_batch_data.get('remark', ''),
        created_by=user_id
    )
    db.session.add(new_batch)
    db.session.flush()

    add_audit_log(
        batch_id=batch.id,
        action='rotate_out',
        action_text='批次轮换-出库',
        operator_id=user_id,
        reason=reason,
        old_status='normal',
        new_status='rotated',
        detail=f'批次 {old_batch_no} 轮换出库，数量 {old_quantity}{batch.unit}'
    )

    add_audit_log(
        batch_id=new_batch.id,
        action='rotate_in',
        action_text='批次轮换-入库',
        operator_id=user_id,
        reason=reason,
        detail=f'新批次 {new_batch.batch_no} 轮换入库，替换 {old_batch_no}，数量 {old_quantity}{batch.unit}'
    )

    db.session.commit()
    return jsonify({'old_batch': batch.to_dict(), 'new_batch': new_batch.to_dict()})


@app.route('/api/orders', methods=['GET'])
@jwt_required()
def get_orders():
    orders = BorrowOrder.query.order_by(BorrowOrder.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])


@app.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    purpose = data.get('purpose', '').strip()
    if not purpose:
        return jsonify({'message': '借用用途不能为空'}), 400

    items = data.get('items', [])
    if not items:
        return jsonify({'message': '请选择借用物资'}), 400

    for item in items:
        batch = MaterialBatch.query.get(item['material_batch_id'])
        if not batch:
            return jsonify({'message': f'物资批次不存在'}), 400

        if batch.is_expired():
            return jsonify({'message': f'批次 {batch.batch_no} 已过期，不能借用'}), 400

        if batch.status != 'normal':
            return jsonify({'message': f'批次 {batch.batch_no} 状态异常，不能借用'}), 400

        if int(item['quantity']) > batch.available_quantity:
            return jsonify({
                'message': f'批次 {batch.batch_no} 库存不足，可用 {batch.available_quantity}{batch.unit}，申请 {item["quantity"]}{batch.unit}'
            }), 400

        if int(item['quantity']) <= 0:
            return jsonify({'message': '借用数量必须大于0'}), 400

    order = BorrowOrder(
        order_no=generate_order_no(),
        purpose=purpose,
        created_by=user_id,
        status='pending_approval'
    )
    db.session.add(order)
    db.session.flush()

    for item in items:
        bi = BorrowItem(
            borrow_order_id=order.id,
            material_batch_id=item['material_batch_id'],
            quantity=int(item['quantity'])
        )
        db.session.add(bi)

    add_audit_log(
        order_id=order.id,
        action='create_order',
        action_text='创建借用单',
        operator_id=user_id,
        reason=purpose,
        new_status='pending_approval',
        detail=f'创建借用单 {order.order_no}，包含 {len(items)} 项物资'
    )

    db.session.commit()
    return jsonify(order.to_dict())


@app.route('/api/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_detail(order_id):
    order = BorrowOrder.query.get(order_id)
    if not order:
        return jsonify({'message': '借用单不存在'}), 404

    logs = AuditLog.query.filter_by(borrow_order_id=order_id).order_by(AuditLog.created_at.desc()).all()

    return jsonify({
        'order': order.to_dict(),
        'audit_logs': [l.to_dict() for l in logs]
    })


@app.route('/api/orders/<int:order_id>/approve', methods=['POST'])
@jwt_required()
def approve_order(order_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    reason = data.get('reason', '').strip()
    if not reason:
        return jsonify({'message': '审批意见不能为空'}), 400

    user = User.query.get(user_id)
    if user.role != 'warehouse_keeper':
        return jsonify({'message': '只有仓库管理员可以审批'}), 403

    order = BorrowOrder.query.get(order_id)
    if not order:
        return jsonify({'message': '借用单不存在'}), 404

    if order.status != 'pending_approval':
        return jsonify({'message': f'当前状态为{order.get_status_text()}，无法审批'}), 400

    for item in order.items:
        batch = MaterialBatch.query.get(item.material_batch_id)
        if not batch:
            db.session.rollback()
            return jsonify({'message': f'物资批次不存在'}), 400

        if batch.is_expired():
            db.session.rollback()
            return jsonify({'message': f'批次 {batch.batch_no} 已过期，不能审批通过'}), 400

        if item.quantity > batch.available_quantity:
            db.session.rollback()
            return jsonify({
                'message': f'批次 {batch.batch_no} 库存不足，可用 {batch.available_quantity}{batch.unit}，申请 {item.quantity}{batch.unit}'
            }), 400

    old_status = order.status
    order.status = 'approved'
    order.approved_by = user_id
    order.approved_at = datetime.now()

    add_audit_log(
        order_id=order.id,
        action='approve',
        action_text='审批通过',
        operator_id=user_id,
        reason=reason,
        old_status=old_status,
        new_status='approved'
    )

    db.session.commit()
    return jsonify(order.to_dict())


@app.route('/api/orders/<int:order_id>/reject', methods=['POST'])
@jwt_required()
def reject_order(order_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    reason = data.get('reason', '').strip()
    if not reason:
        return jsonify({'message': '拒绝原因不能为空'}), 400

    user = User.query.get(user_id)
    if user.role != 'warehouse_keeper':
        return jsonify({'message': '只有仓库管理员可以审批'}), 403

    order = BorrowOrder.query.get(order_id)
    if not order:
        return jsonify({'message': '借用单不存在'}), 404

    if order.status != 'pending_approval':
        return jsonify({'message': f'当前状态为{order.get_status_text()}，无法审批'}), 400

    old_status = order.status
    order.status = 'rejected'
    order.approved_by = user_id
    order.approved_at = datetime.now()

    add_audit_log(
        order_id=order.id,
        action='reject',
        action_text='审批拒绝',
        operator_id=user_id,
        reason=reason,
        old_status=old_status,
        new_status='rejected'
    )

    db.session.commit()
    return jsonify(order.to_dict())


@app.route('/api/orders/<int:order_id>/receive', methods=['POST'])
@jwt_required()
def receive_order(order_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    reason = data.get('reason', '').strip()
    if not reason:
        return jsonify({'message': '领用备注不能为空'}), 400

    order = BorrowOrder.query.get(order_id)
    if not order:
        return jsonify({'message': '借用单不存在'}), 404

    if order.status != 'approved':
        return jsonify({'message': f'当前状态为{order.get_status_text()}，无法领用'}), 400

    for item in order.items:
        batch = MaterialBatch.query.get(item.material_batch_id)
        if not batch:
            db.session.rollback()
            return jsonify({'message': f'物资批次不存在'}), 400

        if batch.is_expired():
            db.session.rollback()
            return jsonify({'message': f'批次 {batch.batch_no} 已过期，不能领用'}), 400

        if item.quantity > batch.available_quantity:
            db.session.rollback()
            return jsonify({
                'message': f'批次 {batch.batch_no} 库存不足，可用 {batch.available_quantity}{batch.unit}，申请 {item.quantity}{batch.unit}'
            }), 400

        batch.available_quantity -= item.quantity

    old_status = order.status
    order.status = 'received'
    order.received_by = user_id
    order.received_at = datetime.now()

    add_audit_log(
        order_id=order.id,
        action='receive',
        action_text='领用出库',
        operator_id=user_id,
        reason=reason,
        old_status=old_status,
        new_status='received'
    )

    db.session.commit()
    return jsonify(order.to_dict())


@app.route('/api/orders/<int:order_id>/return', methods=['POST'])
@jwt_required()
def return_order(order_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    reason = data.get('reason', '').strip()
    if not reason:
        return jsonify({'message': '归还备注不能为空'}), 400

    order = BorrowOrder.query.get(order_id)
    if not order:
        return jsonify({'message': '借用单不存在'}), 404

    if order.status != 'received':
        return jsonify({'message': f'当前状态为{order.get_status_text()}，无法归还'}), 400

    return_items = data.get('items', [])
    if not return_items:
        return jsonify({'message': '请填写归还数量'}), 400

    return_map = {}
    for ri in return_items:
        return_map[ri['id']] = int(ri.get('returned_quantity', 0))

    for item in order.items:
        return_qty = return_map.get(item.id, 0)
        if return_qty < 0 or return_qty > item.quantity - item.returned_quantity - item.damaged_quantity:
            db.session.rollback()
            return jsonify({
                'message': f'{item.material_name} 归还数量超出未归还数量'
            }), 400

        batch = MaterialBatch.query.get(item.material_batch_id)
        if not batch:
            db.session.rollback()
            return jsonify({'message': f'物资批次不存在'}), 400

        item.returned_quantity += return_qty
        batch.available_quantity += return_qty

    total_remaining = sum(item.quantity - item.returned_quantity - item.damaged_quantity for item in order.items)
    old_status = order.status
    if total_remaining == 0:
        order.status = 'returned'
        order.returned_by = user_id
        order.returned_at = datetime.now()

    add_audit_log(
        order_id=order.id,
        action='return',
        action_text='归还入库',
        operator_id=user_id,
        reason=reason,
        old_status=old_status,
        new_status=order.status,
        detail=f'归还物资 {sum(return_map.values())} 件'
    )

    db.session.commit()
    return jsonify(order.to_dict())


@app.route('/api/orders/<int:order_id>/damage', methods=['POST'])
@jwt_required()
def damage_order(order_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    reason = data.get('reason', '').strip()
    if not reason:
        return jsonify({'message': '报损原因不能为空'}), 400

    order = BorrowOrder.query.get(order_id)
    if not order:
        return jsonify({'message': '借用单不存在'}), 404

    if order.status != 'received':
        return jsonify({'message': f'当前状态为{order.get_status_text()}，无法报损'}), 400

    damage_items = data.get('items', [])
    if not damage_items:
        return jsonify({'message': '请填写报损数量'}), 400

    damage_map = {}
    for di in damage_items:
        damage_map[di['id']] = int(di.get('damaged_quantity', 0))

    for item in order.items:
        damage_qty = damage_map.get(item.id, 0)
        if damage_qty < 0 or damage_qty > item.quantity - item.returned_quantity - item.damaged_quantity:
            db.session.rollback()
            return jsonify({
                'message': f'{item.material_name} 报损数量超出未归还数量'
            }), 400

        item.damaged_quantity += damage_qty

    total_remaining = sum(item.quantity - item.returned_quantity - item.damaged_quantity for item in order.items)
    old_status = order.status
    if total_remaining == 0:
        order.status = 'damaged'
        order.returned_by = user_id
        order.returned_at = datetime.now()

    add_audit_log(
        order_id=order.id,
        action='damage',
        action_text='物资报损',
        operator_id=user_id,
        reason=reason,
        old_status=old_status,
        new_status=order.status,
        detail=f'报损物资 {sum(damage_map.values())} 件'
    )

    db.session.commit()
    return jsonify(order.to_dict())


@app.route('/api/batches/export', methods=['GET'])
@jwt_required()
def export_batches():
    auth_err = require_warehouse_keeper()
    if auth_err:
        return auth_err
    batches = MaterialBatch.query.order_by(MaterialBatch.created_at.desc()).all()
    data = []
    for b in batches:
        data.append({
            '批次号': b.batch_no,
            '物资名称': b.material_name,
            '规格型号': b.specification,
            '总数量': b.total_quantity,
            '可用数量': b.available_quantity,
            '单位': b.unit,
            '生产日期': b.production_date.strftime('%Y-%m-%d'),
            '有效期至': b.expiry_date.strftime('%Y-%m-%d'),
            '库位': b.warehouse_location,
            '状态': b.status,
            '供应商': b.supplier,
            '备注': b.remark
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='物资批次')

    output.seek(0)
    filename = f'物资批次_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx'
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/batches/import', methods=['POST'])
@jwt_required()
def import_batches():
    auth_err = require_warehouse_keeper()
    if auth_err:
        return auth_err
    user_id = int(get_jwt_identity())
    reason = request.form.get('reason', '').strip()
    if not reason:
        return jsonify({'message': '导入原因不能为空'}), 400

    if 'file' not in request.files:
        return jsonify({'message': '请选择上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': '请选择上传文件'}), 400

    try:
        if file.filename.endswith('.csv'):
            content = file.read().decode('utf-8-sig')
            df = pd.read_csv(StringIO(content))
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            return jsonify({'message': '仅支持CSV和Excel文件'}), 400

        required_cols = ['批次号', '物资名称', '总数量', '单位', '生产日期', '有效期至', '库位']
        for col in required_cols:
            if col not in df.columns:
                return jsonify({'message': f'缺少必填列: {col}'}), 400

        success_count = 0
        skip_count = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                batch_no = str(row['批次号']).strip()
                existing = MaterialBatch.query.filter_by(batch_no=batch_no).first()
                if existing:
                    skip_count += 1
                    errors.append(f'第{idx + 2}行: 批次号 {batch_no} 已存在，跳过')
                    continue

                prod_date = pd.to_datetime(row['生产日期']).date()
                exp_date = pd.to_datetime(row['有效期至']).date()

                if exp_date < prod_date:
                    skip_count += 1
                    errors.append(f'第{idx + 2}行: 有效期早于生产日期，跳过')
                    continue

                batch = MaterialBatch(
                    batch_no=batch_no,
                    material_name=str(row['物资名称']).strip(),
                    specification=str(row.get('规格型号', '')).strip(),
                    total_quantity=int(row['总数量']),
                    available_quantity=int(row['总数量']),
                    unit=str(row['单位']).strip(),
                    production_date=prod_date,
                    expiry_date=exp_date,
                    warehouse_location=str(row['库位']).strip(),
                    supplier=str(row.get('供应商', '')).strip(),
                    remark=str(row.get('备注', '')).strip(),
                    created_by=user_id
                )
                db.session.add(batch)
                db.session.flush()

                add_audit_log(
                    batch_id=batch.id,
                    action='import_batch',
                    action_text='导入批次',
                    operator_id=user_id,
                    reason=reason,
                    detail=f'导入批次 {batch.batch_no}，物资 {batch.material_name}，数量 {batch.total_quantity}{batch.unit}'
                )
                success_count += 1
            except Exception as e:
                skip_count += 1
                errors.append(f'第{idx + 2}行: {str(e)}')
                continue

        db.session.commit()

        return jsonify({
            'success': success_count,
            'skip': skip_count,
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'导入失败: {str(e)}'}), 500


@app.route('/api/audit-logs', methods=['GET'])
@jwt_required()
def get_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return jsonify([l.to_dict() for l in logs])


@app.route('/api/stock-takes', methods=['GET'])
@jwt_required()
def get_stock_takes():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    stock_takes = StockTake.query.order_by(StockTake.created_at.desc()).all()
    
    if user.role == 'duty_officer':
        stock_takes = [st for st in stock_takes if st.status in ('confirmed', 'cancelled')]
    
    return jsonify([st.to_dict() for st in stock_takes])


@app.route('/api/stock-takes/<int:stock_take_id>', methods=['GET'])
@jwt_required()
def get_stock_take_detail(stock_take_id):
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    stock_take = StockTake.query.get(stock_take_id)
    if not stock_take:
        return jsonify({'message': '盘点单不存在'}), 404
    
    if user.role == 'duty_officer' and stock_take.status not in ('confirmed', 'cancelled'):
        return jsonify({'message': '值班员只能查看已完成的盘点记录'}), 403
    
    logs = AuditLog.query.filter_by(stock_take_id=stock_take_id).order_by(AuditLog.created_at.desc()).all()
    
    return jsonify({
        'stock_take': stock_take.to_dict(),
        'audit_logs': [l.to_dict() for l in logs]
    })


@app.route('/api/stock-takes', methods=['POST'])
@jwt_required()
def create_stock_take():
    auth_err = require_warehouse_keeper()
    if auth_err:
        return auth_err
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    batch_id = data.get('material_batch_id')
    if not batch_id:
        return jsonify({'message': '请选择盘点批次'}), 400
    
    batch = MaterialBatch.query.get(batch_id)
    if not batch:
        return jsonify({'message': '批次不存在'}), 404
    
    if batch.status != 'normal':
        return jsonify({'message': f'批次状态为{batch.status}，无法盘点'}), 400
    
    conflicts = check_batch_conflicts(batch_id)
    if conflicts:
        return jsonify({
            'message': '发起盘点失败，存在以下冲突：',
            'conflicts': conflicts
        }), 400
    
    stock_take = StockTake(
        stock_take_no=generate_stock_take_no(),
        material_batch_id=batch_id,
        expected_quantity=batch.available_quantity,
        created_by=user_id,
        status='pending_confirm'
    )
    db.session.add(stock_take)
    db.session.flush()
    
    add_audit_log(
        stock_take_id=stock_take.id,
        batch_id=batch_id,
        action='create_stock_take',
        action_text='创建盘点单',
        operator_id=user_id,
        reason=data.get('reason', '发起库存盘点'),
        new_status='pending_confirm',
        detail=f'创建盘点单 {stock_take.stock_take_no}，批次 {batch.batch_no}，账面数量 {batch.available_quantity}{batch.unit}'
    )
    
    db.session.commit()
    return jsonify(stock_take.to_dict())


@app.route('/api/stock-takes/<int:stock_take_id>/update', methods=['POST'])
@jwt_required()
def update_stock_take(stock_take_id):
    auth_err = require_warehouse_keeper()
    if auth_err:
        return auth_err
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    stock_take = StockTake.query.get(stock_take_id)
    if not stock_take:
        return jsonify({'message': '盘点单不存在'}), 404
    
    if stock_take.status != 'pending_confirm':
        return jsonify({'message': f'盘点单状态为{stock_take.get_status_text()}，无法修改'}), 400
    
    actual_quantity = data.get('actual_quantity')
    if actual_quantity is None:
        return jsonify({'message': '请输入实盘数量'}), 400
    
    actual_quantity = int(actual_quantity)
    if actual_quantity < 0:
        return jsonify({'message': '实盘数量不能为负数'}), 400
    
    stock_take.actual_quantity = actual_quantity
    stock_take.difference_quantity = actual_quantity - stock_take.expected_quantity
    stock_take.difference_reason = data.get('difference_reason', '')
    stock_take.handling_opinion = data.get('handling_opinion', '')
    
    db.session.commit()
    return jsonify(stock_take.to_dict())


@app.route('/api/stock-takes/<int:stock_take_id>/confirm', methods=['POST'])
@jwt_required()
def confirm_stock_take(stock_take_id):
    auth_err = require_warehouse_keeper()
    if auth_err:
        return auth_err
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    stock_take = StockTake.query.get(stock_take_id)
    if not stock_take:
        return jsonify({'message': '盘点单不存在'}), 404
    
    if stock_take.status != 'pending_confirm':
        return jsonify({'message': f'盘点单状态为{stock_take.get_status_text()}，无法确认'}), 400
    
    if stock_take.actual_quantity is None:
        return jsonify({'message': '请先录入实盘数量'}), 400
    
    difference_reason = data.get('difference_reason', stock_take.difference_reason or '').strip()
    handling_opinion = data.get('handling_opinion', stock_take.handling_opinion or '').strip()
    
    if stock_take.difference_quantity != 0 and not difference_reason:
        return jsonify({'message': '存在差异时必须填写差异原因'}), 400
    
    conflicts = check_batch_conflicts(stock_take.material_batch_id, exclude_stock_take_id=stock_take_id)
    if conflicts:
        return jsonify({
            'message': '确认盘点失败，存在以下冲突，请先处理：',
            'conflicts': conflicts
        }), 400
    
    batch = MaterialBatch.query.get(stock_take.material_batch_id)
    if not batch:
        db.session.rollback()
        return jsonify({'message': '关联批次不存在'}), 400
    
    old_available = batch.available_quantity
    old_total = batch.total_quantity
    diff = stock_take.difference_quantity
    
    if batch.available_quantity != stock_take.expected_quantity:
        return jsonify({
            'message': f'账面数量已变化，当前可用数量为 {batch.available_quantity}{batch.unit}，请重新发起盘点'
        }), 400
    
    batch.available_quantity = stock_take.actual_quantity
    batch.total_quantity = batch.total_quantity + diff
    
    stock_take.difference_reason = difference_reason
    stock_take.handling_opinion = handling_opinion
    stock_take.status = 'confirmed'
    stock_take.confirmed_by = user_id
    stock_take.confirmed_at = datetime.now()
    
    add_audit_log(
        stock_take_id=stock_take.id,
        batch_id=batch.id,
        action='confirm_stock_take',
        action_text='确认盘点',
        operator_id=user_id,
        reason=handling_opinion if handling_opinion else difference_reason,
        old_status='pending_confirm',
        new_status='confirmed',
        old_quantity=old_available,
        new_quantity=stock_take.actual_quantity,
        detail=f'盘点单 {stock_take.stock_take_no} 确认，批次 {batch.batch_no}，账面 {old_available}{batch.unit}，实盘 {stock_take.actual_quantity}{batch.unit}，差异 {diff:+d}{batch.unit}'
    )
    
    add_audit_log(
        batch_id=batch.id,
        action='stock_adjust',
        action_text='库存调整',
        operator_id=user_id,
        reason=f'盘点调整：{difference_reason}',
        old_quantity=old_available,
        new_quantity=stock_take.actual_quantity,
        detail=f'批次 {batch.batch_no} 库存调整，可用数量 {old_available}{batch.unit} → {stock_take.actual_quantity}{batch.unit}，总数量 {old_total}{batch.unit} → {batch.total_quantity}{batch.unit}，盘点单 {stock_take.stock_take_no}'
    )
    
    db.session.commit()
    return jsonify(stock_take.to_dict())


@app.route('/api/stock-takes/<int:stock_take_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_stock_take(stock_take_id):
    auth_err = require_warehouse_keeper()
    if auth_err:
        return auth_err
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    reason = data.get('reason', '').strip()
    if not reason:
        return jsonify({'message': '撤销原因不能为空'}), 400
    
    stock_take = StockTake.query.get(stock_take_id)
    if not stock_take:
        return jsonify({'message': '盘点单不存在'}), 404
    
    if stock_take.status != 'pending_confirm':
        return jsonify({'message': f'盘点单状态为{stock_take.get_status_text()}，无法撤销'}), 400
    
    stock_take.status = 'cancelled'
    stock_take.cancelled_by = user_id
    stock_take.cancelled_at = datetime.now()
    
    add_audit_log(
        stock_take_id=stock_take.id,
        batch_id=stock_take.material_batch_id,
        action='cancel_stock_take',
        action_text='撤销盘点',
        operator_id=user_id,
        reason=reason,
        old_status='pending_confirm',
        new_status='cancelled',
        detail=f'盘点单 {stock_take.stock_take_no} 撤销，原因：{reason}'
    )
    
    db.session.commit()
    return jsonify(stock_take.to_dict())


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
