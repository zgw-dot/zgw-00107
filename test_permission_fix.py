#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
权限修复验证测试脚本

测试目标：
1. duty账号越权操作（创建批次、轮换、导入）必须失败且数据库不新增
2. admin账号同样操作必须成功
3. 正常借用审批链路不受影响，库存、审计日志、非法状态校验正常
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = 'http://localhost:5000'

def login(username, password):
    """登录获取token"""
    r = requests.post(f'{BASE_URL}/api/auth/login',
        json={'username': username, 'password': password})
    assert r.status_code == 200, f'{username} 登录失败: {r.text}'
    return r.json()['access_token']

def get_headers(token):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

def test_duty_cannot_create_batch():
    """测试1：值班员不能创建批次"""
    print('='*60)
    print('测试1：值班员(duty)尝试创建批次，应该被拒绝')
    token = login('duty', 'duty123')
    
    batch_data = {
        'batch_no': 'TEST-DUTY-BYPASS-001',
        'material_name': '越权测试物资',
        'specification': '测试',
        'total_quantity': 100,
        'unit': '个',
        'production_date': '2024-01-01',
        'expiry_date': '2026-12-31',
        'warehouse_location': 'A-01-01',
        'supplier': '测试',
        'remark': '越权测试',
        'reason': '越权测试入库'
    }
    
    r = requests.post(f'{BASE_URL}/api/batches',
        headers=get_headers(token), json=batch_data)
    
    print(f'  状态码: {r.status_code}')
    print(f'  返回: {r.json()}')
    
    assert r.status_code == 403, f'预期403，实际{r.status_code}'
    assert '只有仓库管理员可以执行此操作' in r.json()['message'], '错误信息不正确'
    
    # 验证数据库没有新增
    admin_token = login('admin', 'admin123')
    r = requests.get(f'{BASE_URL}/api/batches', headers=get_headers(admin_token))
    batches = r.json()
    for b in batches:
        assert b['batch_no'] != 'TEST-DUTY-BYPASS-001', '数据库中不应该存在越权创建的批次!'
    
    print('  ✅ 通过：duty创建批次被拒绝，数据库未新增')

def test_admin_can_create_batch():
    """测试2：仓库管理员可以创建批次"""
    print('='*60)
    print('测试2：管理员(admin)创建批次，应该成功')
    token = login('admin', 'admin123')
    
    batch_no = f'TEST-ADMIN-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    batch_data = {
        'batch_no': batch_no,
        'material_name': '权限测试-医用手套',
        'specification': 'M号',
        'total_quantity': 500,
        'unit': '盒',
        'production_date': '2024-01-01',
        'expiry_date': '2026-12-31',
        'warehouse_location': 'A-02-03',
        'supplier': '正规供应商',
        'remark': '权限测试',
        'reason': '正常采购入库'
    }
    
    r = requests.post(f'{BASE_URL}/api/batches',
        headers=get_headers(token), json=batch_data)
    
    print(f'  状态码: {r.status_code}')
    if r.status_code != 200:
        print(f'  返回: {r.json()}')
    
    assert r.status_code == 200, f'预期200，实际{r.status_code}'
    
    # 验证数据库有新增
    r = requests.get(f'{BASE_URL}/api/batches', headers=get_headers(token))
    batches = r.json()
    found = any(b['batch_no'] == batch_no for b in batches)
    assert found, f'数据库中应该存在管理员创建的批次 {batch_no}!'
    
    print(f'  ✅ 通过：admin创建批次成功，批次号 {batch_no} 已入库')
    return batch_no

def test_duty_cannot_rotate_batch():
    """测试3：值班员不能轮换批次"""
    print('='*60)
    print('测试3：值班员(duty)尝试轮换批次，应该被拒绝')
    admin_token = login('admin', 'admin123')
    duty_token = login('duty', 'duty123')
    
    # 先让admin创建一个批次用于测试
    batch_no = f'TEST-ROTATE-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    batch_data = {
        'batch_no': batch_no,
        'material_name': '轮换测试物资',
        'total_quantity': 200,
        'unit': '个',
        'production_date': '2024-01-01',
        'expiry_date': '2026-12-31',
        'warehouse_location': 'B-01-01',
        'reason': '轮换测试入库'
    }
    r = requests.post(f'{BASE_URL}/api/batches',
        headers=get_headers(admin_token), json=batch_data)
    batch_id = r.json()['id']
    
    # duty尝试轮换
    rotate_data = {
        'reason': '越权轮换测试',
        'new_batch': {
            'batch_no': f'NEW-{batch_no}',
            'production_date': '2024-06-01',
            'expiry_date': '2027-06-01',
            'remark': ''
        }
    }
    
    r = requests.post(f'{BASE_URL}/api/batches/{batch_id}/rotate',
        headers=get_headers(duty_token), json=rotate_data)
    
    print(f'  状态码: {r.status_code}')
    print(f'  返回: {r.json()}')
    
    assert r.status_code == 403, f'预期403，实际{r.status_code}'
    assert '只有仓库管理员可以执行此操作' in r.json()['message']
    
    # 验证原批次未被修改
    r = requests.get(f'{BASE_URL}/api/batches/{batch_id}', headers=get_headers(admin_token))
    batch = r.json()['batch']
    assert batch['status'] == 'normal', f'批次状态不应该改变，实际: {batch["status"]}'
    assert batch['available_quantity'] == 200, f'库存不应该改变，实际: {batch["available_quantity"]}'
    
    print('  ✅ 通过：duty轮换批次被拒绝，原批次状态和库存未变')

def test_duty_cannot_import():
    """测试4：值班员不能导入批次"""
    print('='*60)
    print('测试4：值班员(duty)尝试导入批次，应该被拒绝')
    token = login('duty', 'duty123')
    
    csv_content = '批次号,物资名称,总数量,单位,生产日期,有效期至,库位\nDUTY-IMPORT-001,越权导入物资,100,个,2024-01-01,2026-12-31,A-01-01'
    
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    headers = {'Authorization': f'Bearer {token}'}
    data = {'reason': '越权导入测试'}
    
    r = requests.post(f'{BASE_URL}/api/batches/import',
        headers=headers, files=files, data=data)
    
    print(f'  状态码: {r.status_code}')
    print(f'  返回: {r.json()}')
    
    assert r.status_code == 403, f'预期403，实际{r.status_code}'
    assert '只有仓库管理员可以执行此操作' in r.json()['message']
    
    # 验证数据库没有新增
    admin_token = login('admin', 'admin123')
    r = requests.get(f'{BASE_URL}/api/batches', headers=get_headers(admin_token))
    batches = r.json()
    for b in batches:
        assert b['batch_no'] != 'DUTY-IMPORT-001', '数据库中不应该存在越权导入的批次!'
    
    print('  ✅ 通过：duty导入批次被拒绝，数据库未新增')

def test_duty_cannot_export():
    """测试5：值班员不能导出批次"""
    print('='*60)
    print('测试5：值班员(duty)尝试导出批次，应该被拒绝')
    token = login('duty', 'duty123')
    
    r = requests.get(f'{BASE_URL}/api/batches/export', headers=get_headers(token))
    
    print(f'  状态码: {r.status_code}')
    
    assert r.status_code == 403, f'预期403，实际{r.status_code}'
    assert '只有仓库管理员可以执行此操作' in r.json()['message']
    
    print('  ✅ 通过：duty导出批次被拒绝')

def test_normal_borrow_flow():
    """测试6：正常借用审批链路未被破坏"""
    print('='*60)
    print('测试6：正常借用审批链路（主流程回归测试）')
    
    admin_token = login('admin', 'admin123')
    duty_token = login('duty', 'duty123')
    
    # 1. admin创建批次
    print('  步骤1：admin创建批次...')
    batch_no = f'BORROW-TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    batch_data = {
        'batch_no': batch_no,
        'material_name': '借用流程测试物资',
        'total_quantity': 100,
        'unit': '个',
        'production_date': '2024-01-01',
        'expiry_date': '2026-12-31',
        'warehouse_location': 'C-01-01',
        'reason': '流程测试入库'
    }
    r = requests.post(f'{BASE_URL}/api/batches',
        headers=get_headers(admin_token), json=batch_data)
    batch_id = r.json()['id']
    print(f'    ✅ 批次创建成功，ID={batch_id}')
    
    # 2. duty发起借用申请
    print('  步骤2：duty发起借用申请...')
    order_data = {
        'purpose': '应急演练借用',
        'items': [{'material_batch_id': batch_id, 'quantity': 10}]
    }
    r = requests.post(f'{BASE_URL}/api/orders',
        headers=get_headers(duty_token), json=order_data)
    assert r.status_code == 200, f'创建借用单失败: {r.text}'
    order_id = r.json()['id']
    print(f'    ✅ 借用单创建成功，ID={order_id}，状态={r.json()["status"]}')
    
    # 3. admin审批通过
    print('  步骤3：admin审批通过...')
    r = requests.post(f'{BASE_URL}/api/orders/{order_id}/approve',
        headers=get_headers(admin_token), json={'reason': '审批通过，同意领用'})
    assert r.status_code == 200, f'审批失败: {r.text}'
    print(f'    ✅ 审批通过，状态={r.json()["status"]}')
    
    # 4. duty领用
    print('  步骤4：duty领用...')
    r = requests.post(f'{BASE_URL}/api/orders/{order_id}/receive',
        headers=get_headers(duty_token), json={'reason': '现场领用确认'})
    assert r.status_code == 200, f'领用失败: {r.text}'
    
    # 验证库存扣减
    r = requests.get(f'{BASE_URL}/api/batches/{batch_id}', headers=get_headers(admin_token))
    batch = r.json()['batch']
    assert batch['available_quantity'] == 90, f'库存扣减错误，预期90，实际{batch["available_quantity"]}'
    print(f'    ✅ 领用成功，库存扣减为 {batch["available_quantity"]}')
    
    # 5. duty归还 - 需要先获取借用单详情，得到明细项的id
    print('  步骤5：duty归还...')
    r = requests.get(f'{BASE_URL}/api/orders/{order_id}', headers=get_headers(duty_token))
    order_detail = r.json()['order']
    item_id = order_detail['items'][0]['id']
    
    return_data = {
        'reason': '演练完成归还',
        'items': [{'id': item_id, 'returned_quantity': 10}]
    }
    r = requests.post(f'{BASE_URL}/api/orders/{order_id}/return',
        headers=get_headers(duty_token), json=return_data)
    assert r.status_code == 200, f'归还失败: {r.text}'
    
    # 验证库存恢复
    r = requests.get(f'{BASE_URL}/api/batches/{batch_id}', headers=get_headers(admin_token))
    batch = r.json()['batch']
    assert batch['available_quantity'] == 100, f'库存恢复错误，预期100，实际{batch["available_quantity"]}'
    print(f'    ✅ 归还成功，库存恢复为 {batch["available_quantity"]}')
    
    # 6. 验证审计日志存在
    print('  步骤6：验证审计日志...')
    r = requests.get(f'{BASE_URL}/api/audit-logs', headers=get_headers(admin_token))
    logs = r.json()
    order_logs = [l for l in logs if l.get('borrow_order_id') == order_id]
    assert len(order_logs) >= 4, f'审计日志数量不足，预期至少4条，实际{len(order_logs)}'
    
    actions = [l['action'] for l in order_logs]
    expected = ['create_order', 'approve', 'receive', 'return']
    for exp in expected:
        assert exp in actions, f'缺少审计日志: {exp}'
    
    # 验证每条日志都有reason
    for l in order_logs:
        assert l.get('reason'), f'日志缺少reason: {l["action"]}'
    
    print(f'    ✅ 审计日志完整，共{len(order_logs)}条，均有原因备注')
    
    print('  ✅ 通过：完整借用审批链路正常')

def test_illegal_status_validation():
    """测试7：非法状态校验未被破坏"""
    print('='*60)
    print('测试7：非法状态校验（回归测试）')
    
    admin_token = login('admin', 'admin123')
    duty_token = login('duty', 'duty123')
    
    # 创建批次
    batch_no = f'ILLEGAL-TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    batch_data = {
        'batch_no': batch_no,
        'material_name': '非法状态测试物资',
        'total_quantity': 50,
        'unit': '个',
        'production_date': '2024-01-01',
        'expiry_date': '2026-12-31',
        'warehouse_location': 'D-01-01',
        'reason': '测试入库'
    }
    r = requests.post(f'{BASE_URL}/api/batches',
        headers=get_headers(admin_token), json=batch_data)
    batch_id = r.json()['id']
    
    # 测试：未领用就归还（应该拒绝）
    print('  测试未领用就归还...')
    order_data = {
        'purpose': '测试未领用归还',
        'items': [{'material_batch_id': batch_id, 'quantity': 10}]
    }
    r = requests.post(f'{BASE_URL}/api/orders',
        headers=get_headers(duty_token), json=order_data)
    order_id = r.json()['id']
    
    # 先获取借用单详情，得到明细项的id
    r = requests.get(f'{BASE_URL}/api/orders/{order_id}', headers=get_headers(duty_token))
    order_detail = r.json()['order']
    item_id = order_detail['items'][0]['id']
    
    # 直接尝试归还（跳过领用）
    return_data = {
        'reason': '测试未领用归还',
        'items': [{'id': item_id, 'returned_quantity': 10}]
    }
    r = requests.post(f'{BASE_URL}/api/orders/{order_id}/return',
        headers=get_headers(duty_token), json=return_data)
    
    assert r.status_code == 400, f'预期400，实际{r.status_code}'
    assert '无法归还' in r.json()['message'] or '待领用' in r.json()['message']
    print(f'    ✅ 未领用归还被正确拒绝: {r.json()["message"]}')
    
    # 测试：借用数量超库存（应该拒绝）
    print('  测试借用数量超库存...')
    order_data = {
        'purpose': '测试超库存借用',
        'items': [{'material_batch_id': batch_id, 'quantity': 100}]  # 库存只有50
    }
    r = requests.post(f'{BASE_URL}/api/orders',
        headers=get_headers(duty_token), json=order_data)
    
    assert r.status_code == 400, f'预期400，实际{r.status_code}'
    assert '库存不足' in r.json()['message']
    
    # 验证库存未变
    r = requests.get(f'{BASE_URL}/api/batches/{batch_id}', headers=get_headers(admin_token))
    batch = r.json()['batch']
    assert batch['available_quantity'] == 50, f'库存不应该改变，实际{batch["available_quantity"]}'
    print(f'    ✅ 超库存借用被正确拒绝，库存保持{batch["available_quantity"]}')
    
    # 测试：过期批次借用（应该拒绝）
    print('  测试过期批次借用...')
    # 创建一个过期批次
    exp_batch_no = f'EXPIRED-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    exp_batch_data = {
        'batch_no': exp_batch_no,
        'material_name': '过期测试物资',
        'total_quantity': 100,
        'unit': '个',
        'production_date': '2022-01-01',
        'expiry_date': yesterday,  # 昨天过期
        'warehouse_location': 'E-01-01',
        'reason': '测试过期'
    }
    r = requests.post(f'{BASE_URL}/api/batches',
        headers=get_headers(admin_token), json=exp_batch_data)
    exp_batch_id = r.json()['id']
    
    # 尝试借用过期批次
    order_data = {
        'purpose': '测试过期借用',
        'items': [{'material_batch_id': exp_batch_id, 'quantity': 10}]
    }
    r = requests.post(f'{BASE_URL}/api/orders',
        headers=get_headers(duty_token), json=order_data)
    
    assert r.status_code == 400, f'预期400，实际{r.status_code}'
    assert '过期' in r.json()['message']
    print(f'    ✅ 过期批次借用被正确拒绝: {r.json()["message"]}')
    
    print('  ✅ 通过：非法状态校验全部正常')

if __name__ == '__main__':
    print('='*60)
    print('🚨 应急物资系统 - 权限修复验证测试')
    print('='*60)
    
    try:
        # 越权测试
        test_duty_cannot_create_batch()
        test_admin_can_create_batch()
        test_duty_cannot_rotate_batch()
        test_duty_cannot_import()
        test_duty_cannot_export()
        
        # 回归测试
        test_normal_borrow_flow()
        test_illegal_status_validation()
        
        print('='*60)
        print('✅ 所有测试通过！权限修复验证成功！')
        print('='*60)
    except AssertionError as e:
        print(f'\n❌ 测试失败: {e}')
        exit(1)
    except Exception as e:
        print(f'\n❌ 测试异常: {e}')
        import traceback
        traceback.print_exc()
        exit(1)
