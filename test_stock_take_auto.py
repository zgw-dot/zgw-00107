import requests
import time

BASE_URL = 'http://localhost:5000/api'

def login(username, password):
    response = requests.post(f'{BASE_URL}/auth/login', json={'username': username, 'password': password})
    if response.status_code == 200:
        return response.json()['access_token']
    return None

def get_headers(token):
    return {'Authorization': f'Bearer {token}'}

print('='*60)
print('库存盘点功能自动化测试（无重启部分）')
print('='*60)

admin_token = login('admin', 'admin123')
duty_token = login('duty', 'duty123')
assert admin_token and duty_token, '登录失败'
print('✅ 登录成功')

# 测试1: 管理员成功盘点
print('\n--- 测试1: 管理员成功盘点 ---')
batch_data = {
    'batch_no': f'TEST-PD-{int(time.time())}',
    'material_name': '盘点测试物资',
    'total_quantity': 100,
    'unit': '个',
    'production_date': '2024-01-01',
    'expiry_date': '2026-12-31',
    'warehouse_location': 'A-01-01',
    'reason': '盘点测试批次创建'
}
response = requests.post(f'{BASE_URL}/batches', json=batch_data, headers=get_headers(admin_token))
assert response.status_code == 200, f'创建批次失败: {response.text}'
batch = response.json()
batch_id = batch['id']
print(f'  ✅ 创建批次: {batch["batch_no"]}, 库存={batch["available_quantity"]}')

response = requests.post(f'{BASE_URL}/stock-takes', json={'material_batch_id': batch_id, 'reason': '月度盘点'}, headers=get_headers(admin_token))
assert response.status_code == 200, f'创建盘点单失败: {response.text}'
stock_take = response.json()
st_id = stock_take['id']
print(f'  ✅ 创建盘点单: {stock_take["stock_take_no"]}, 账面={stock_take["expected_quantity"]}')
assert stock_take['status'] == 'pending_confirm'

response = requests.post(f'{BASE_URL}/stock-takes/{st_id}/update', json={
    'actual_quantity': 95,
    'difference_reason': '5个物资损坏',
    'handling_opinion': '调整库存'
}, headers=get_headers(admin_token))
assert response.status_code == 200, f'录入失败: {response.text}'
stock_take = response.json()
print(f'  ✅ 录入实盘: 实盘={stock_take["actual_quantity"]}, 差异={stock_take["difference_quantity"]}')
assert stock_take['difference_quantity'] == -5

response = requests.post(f'{BASE_URL}/stock-takes/{st_id}/confirm', json={'handling_opinion': '确认调整'}, headers=get_headers(admin_token))
assert response.status_code == 200, f'确认失败: {response.text}'
stock_take = response.json()
print(f'  ✅ 确认盘点: 状态={stock_take["status_text"]}')
assert stock_take['status'] == 'confirmed'

response = requests.get(f'{BASE_URL}/batches/{batch_id}', headers=get_headers(admin_token))
batch_detail = response.json()['batch']
print(f'  ✅ 库存调整: 可用={batch_detail["available_quantity"]}, 总数={batch_detail["total_quantity"]}')
assert batch_detail['available_quantity'] == 95
assert batch_detail['total_quantity'] == 95

response = requests.get(f'{BASE_URL}/audit-logs', headers=get_headers(admin_token))
logs = response.json()
adjust_logs = [l for l in logs if l['action'] == 'stock_adjust' and l['material_batch_id'] == batch_id]
assert len(adjust_logs) >= 1, '缺少库存调整日志'
print(f'  ✅ 审计日志: {adjust_logs[0]["old_quantity"]} → {adjust_logs[0]["new_quantity"]}')

# 测试2: 值班员越权
print('\n--- 测试2: 值班员越权 ---')
batch_data2 = {
    'batch_no': f'TEST-PD2-{int(time.time())}',
    'material_name': '权限测试',
    'total_quantity': 50,
    'unit': '箱',
    'production_date': '2024-01-01',
    'expiry_date': '2026-12-31',
    'warehouse_location': 'A-02-01',
    'reason': '测试'
}
response = requests.post(f'{BASE_URL}/batches', json=batch_data2, headers=get_headers(admin_token))
batch2 = response.json()

response = requests.post(f'{BASE_URL}/stock-takes', json={'material_batch_id': batch2['id'], 'reason': '越权测试'}, headers=get_headers(duty_token))
assert response.status_code == 403, f'值班员应被拒绝: {response.status_code}'
print(f'  ✅ 值班员创建盘点单被拒绝: {response.status_code}')

response = requests.get(f'{BASE_URL}/stock-takes', headers=get_headers(duty_token))
duty_st_list = response.json()
for st in duty_st_list:
    assert st['status'] in ('confirmed', 'cancelled'), '值班员只能看已确认和已撤销'
print(f'  ✅ 值班员列表只显示终态: {len(duty_st_list)} 条 (已确认+已撤销)')

response = requests.get(f'{BASE_URL}/stock-takes/{st_id}', headers=get_headers(duty_token))
assert response.status_code == 200, '值班员应能查看已确认'
print('  ✅ 值班员可以查看已确认盘点单')

# 测试3: 重复盘点冲突
print('\n--- 测试3: 重复盘点冲突 ---')
batch_data3 = {
    'batch_no': f'TEST-PD3-{int(time.time())}',
    'material_name': '重复测试',
    'total_quantity': 200,
    'unit': '件',
    'production_date': '2024-01-01',
    'expiry_date': '2026-12-31',
    'warehouse_location': 'A-03-01',
    'reason': '测试'
}
response = requests.post(f'{BASE_URL}/batches', json=batch_data3, headers=get_headers(admin_token))
batch3 = response.json()

response = requests.post(f'{BASE_URL}/stock-takes', json={'material_batch_id': batch3['id'], 'reason': '第一次'}, headers=get_headers(admin_token))
assert response.status_code == 200
st1 = response.json()
print(f'  ✅ 第一个盘点单: {st1["stock_take_no"]}')

response = requests.post(f'{BASE_URL}/stock-takes', json={'material_batch_id': batch3['id'], 'reason': '第二次'}, headers=get_headers(admin_token))
assert response.status_code == 400, f'重复应被拒绝: {response.status_code}'
result = response.json()
assert 'conflicts' in result
print(f'  ✅ 重复盘点被拒绝: {result["conflicts"][0][:50]}...')

# 测试4: 借用冲突检测
print('\n--- 测试4: 借用冲突检测 ---')
batch_data4 = {
    'batch_no': f'TEST-PD4-{int(time.time())}',
    'material_name': '借用冲突测试',
    'total_quantity': 100,
    'unit': '套',
    'production_date': '2024-01-01',
    'expiry_date': '2026-12-31',
    'warehouse_location': 'A-04-01',
    'reason': '测试'
}
response = requests.post(f'{BASE_URL}/batches', json=batch_data4, headers=get_headers(admin_token))
batch4 = response.json()

response = requests.post(f'{BASE_URL}/orders', json={
    'purpose': '测试', 'items': [{'material_batch_id': batch4['id'], 'quantity': 10}]
}, headers=get_headers(duty_token))
order = response.json()
print(f'  ✅ 创建借用单: {order["order_no"]} ({order["status_text"]})')

response = requests.post(f'{BASE_URL}/stock-takes', json={'material_batch_id': batch4['id'], 'reason': '测试'}, headers=get_headers(admin_token))
assert response.status_code == 400
assert '待审批' in response.json()['conflicts'][0]
print('  ✅ 待审批借用单阻止盘点')

requests.post(f'{BASE_URL}/orders/{order["id"]}/approve', json={'reason': '同意'}, headers=get_headers(admin_token))
response = requests.post(f'{BASE_URL}/stock-takes', json={'material_batch_id': batch4['id'], 'reason': '测试'}, headers=get_headers(admin_token))
assert response.status_code == 400
assert '待领用' in response.json()['conflicts'][0]
print('  ✅ 待领用借用单阻止盘点')

requests.post(f'{BASE_URL}/orders/{order["id"]}/receive', json={'reason': '领用'}, headers=get_headers(duty_token))
response = requests.post(f'{BASE_URL}/stock-takes', json={'material_batch_id': batch4['id'], 'reason': '测试'}, headers=get_headers(admin_token))
assert response.status_code == 400
assert '未完成借用' in response.json()['conflicts'][0]
print('  ✅ 未完成借用阻止盘点')

requests.post(f'{BASE_URL}/orders/{order["id"]}/return', json={
    'items': [{'id': order['items'][0]['id'], 'returned_quantity': 10}], 'reason': '归还'
}, headers=get_headers(duty_token))
response = requests.post(f'{BASE_URL}/stock-takes', json={'material_batch_id': batch4['id'], 'reason': '测试'}, headers=get_headers(admin_token))
assert response.status_code == 200
print(f'  ✅ 借用归还后可盘点: {response.json()["stock_take_no"]}')

# 测试5: 借用归还流程未破坏
print('\n--- 测试5: 借用归还流程未破坏 ---')
batch_data5 = {
    'batch_no': f'TEST-BORROW-{int(time.time())}',
    'material_name': '回归测试',
    'total_quantity': 50,
    'unit': '个',
    'production_date': '2024-01-01',
    'expiry_date': '2026-12-31',
    'warehouse_location': 'B-01-01',
    'reason': '测试'
}
response = requests.post(f'{BASE_URL}/batches', json=batch_data5, headers=get_headers(admin_token))
batch5 = response.json()
print(f'  ✅ 创建批次: {batch5["batch_no"]}, 库存={batch5["available_quantity"]}')

response = requests.post(f'{BASE_URL}/orders', json={
    'purpose': '回归测试', 'items': [{'material_batch_id': batch5['id'], 'quantity': 10}]
}, headers=get_headers(duty_token))
order2 = response.json()

requests.post(f'{BASE_URL}/orders/{order2["id"]}/approve', json={'reason': '同意'}, headers=get_headers(admin_token))
requests.post(f'{BASE_URL}/orders/{order2["id"]}/receive', json={'reason': '领用'}, headers=get_headers(duty_token))
response = requests.get(f'{BASE_URL}/batches/{batch5["id"]}', headers=get_headers(admin_token))
assert response.json()['batch']['available_quantity'] == 40
print('  ✅ 领用后库存=40')

requests.post(f'{BASE_URL}/orders/{order2["id"]}/return', json={
    'items': [{'id': order2['items'][0]['id'], 'returned_quantity': 10}], 'reason': '归还'
}, headers=get_headers(duty_token))
response = requests.get(f'{BASE_URL}/batches/{batch5["id"]}', headers=get_headers(admin_token))
assert response.json()['batch']['available_quantity'] == 50
print('  ✅ 归还后库存=50')

response = requests.get(f'{BASE_URL}/batches/export', headers=get_headers(admin_token))
assert response.status_code == 200
assert 'vnd.openxmlformats' in response.headers['Content-Type']
print('  ✅ 导出功能正常')

# 测试6: 已撤销盘点单对值班员可见
print('\n--- 测试6: 已撤销盘点单对值班员可见 ---')
batch_data6 = {
    'batch_no': f'TEST-CANCEL-{int(time.time())}',
    'material_name': '撤销可见性测试',
    'total_quantity': 150,
    'unit': '个',
    'production_date': '2024-01-01',
    'expiry_date': '2026-12-31',
    'warehouse_location': 'B-02-01',
    'reason': '撤销可见性测试'
}
response = requests.post(f'{BASE_URL}/batches', json=batch_data6, headers=get_headers(admin_token))
batch6 = response.json()

response = requests.post(f'{BASE_URL}/stock-takes', json={'material_batch_id': batch6['id'], 'reason': '测试撤销可见性'}, headers=get_headers(admin_token))
assert response.status_code == 200
st_cancel = response.json()
st_cancel_id = st_cancel['id']

response = requests.post(f'{BASE_URL}/stock-takes/{st_cancel_id}/cancel', json={'reason': '信息有误重新盘点'}, headers=get_headers(admin_token))
assert response.status_code == 200
st_cancelled = response.json()
assert st_cancelled['status'] == 'cancelled'
assert st_cancelled['status_text'] == '已撤销'
assert st_cancelled['canceller_name'] == 'admin'
assert st_cancelled['cancelled_at'] != ''
print(f'  ✅ 管理员撤销盘点单: {st_cancelled["stock_take_no"]}, 状态={st_cancelled["status_text"]}')

response = requests.get(f'{BASE_URL}/stock-takes', headers=get_headers(duty_token))
duty_list_after = response.json()
cancelled_in_duty = [st for st in duty_list_after if st['id'] == st_cancel_id]
assert len(cancelled_in_duty) == 1, '值班员列表应能看到已撤销盘点单'
assert cancelled_in_duty[0]['status'] == 'cancelled'
assert cancelled_in_duty[0]['status_text'] == '已撤销'
assert cancelled_in_duty[0]['canceller_name'] == 'admin'
print(f'  ✅ 值班员列表能查到已撤销: {cancelled_in_duty[0]["stock_take_no"]}')

response = requests.get(f'{BASE_URL}/stock-takes/{st_cancel_id}', headers=get_headers(duty_token))
assert response.status_code == 200, '值班员应能打开已撤销详情'
detail = response.json()
assert detail['stock_take']['status'] == 'cancelled'
assert detail['stock_take']['canceller_name'] == 'admin'
assert len(detail['audit_logs']) > 0
cancel_logs = [l for l in detail['audit_logs'] if l['action'] == 'cancel_stock_take']
assert len(cancel_logs) > 0
print(f'  ✅ 值班员能打开已撤销详情，撤销人={detail["stock_take"]["canceller_name"]}，审计日志={len(detail["audit_logs"])}条')

response = requests.post(f'{BASE_URL}/stock-takes/{st_cancel_id}/cancel', json={'reason': '越权测试'}, headers=get_headers(duty_token))
assert response.status_code == 403, '值班员撤销操作应被拒绝'
print('  ✅ 值班员写操作仍被拒绝: 403')

print('\n' + '='*60)
print('✅ 所有自动化测试通过！')
print('='*60)
print()
print('持久化测试请手动运行:')
print('  1. 记录上面已确认的盘点单号')
print('  2. 重启后端服务 (Ctrl+C 后重新运行 python app.py)')
print('  3. 运行完整测试: python test_stock_take.py')
print('  4. 选择测试5验证数据持久化')
