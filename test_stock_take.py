import requests
import json
import time

BASE_URL = 'http://localhost:5000/api'

def login(username, password):
    response = requests.post(
        f'{BASE_URL}/auth/login',
        json={'username': username, 'password': password}
    )
    if response.status_code == 200:
        return response.json()['access_token']
    return None

def get_headers(token):
    return {'Authorization': f'Bearer {token}'}

def test_case(name, func):
    print(f'\n{"="*60}')
    print(f'测试: {name}')
    print('='*60)
    try:
        result = func()
        print(f'✅ {name} - 通过')
        return result
    except AssertionError as e:
        print(f'❌ {name} - 失败: {e}')
        return False
    except Exception as e:
        print(f'❌ {name} - 异常: {e}')
        return False

def test_admin_create_and_confirm_stock_take():
    """测试1: 管理员成功盘点"""
    admin_token = login('admin', 'admin123')
    assert admin_token, '管理员登录失败'
    
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
    response = requests.post(
        f'{BASE_URL}/batches',
        json=batch_data,
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, f'创建批次失败: {response.text}'
    batch = response.json()
    batch_id = batch['id']
    print(f'  - 创建批次成功: {batch["batch_no"]}, 可用库存: {batch["available_quantity"]}')
    
    response = requests.post(
        f'{BASE_URL}/stock-takes',
        json={'material_batch_id': batch_id, 'reason': '月度库存盘点'},
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, f'创建盘点单失败: {response.text}'
    stock_take = response.json()
    stock_take_id = stock_take['id']
    print(f'  - 创建盘点单成功: {stock_take["stock_take_no"]}, 账面数量: {stock_take["expected_quantity"]}')
    assert stock_take['status'] == 'pending_confirm', '盘点单状态应为待确认'
    assert stock_take['expected_quantity'] == 100, '账面数量应等于批次可用库存'
    
    response = requests.post(
        f'{BASE_URL}/stock-takes/{stock_take_id}/update',
        json={
            'actual_quantity': 95,
            'difference_reason': '发现5个物资损坏，已报损',
            'handling_opinion': '调整库存至实盘数量'
        },
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, f'录入实盘数量失败: {response.text}'
    stock_take = response.json()
    print(f'  - 录入实盘数量成功: 实盘={stock_take["actual_quantity"]}, 差异={stock_take["difference_quantity"]}')
    assert stock_take['actual_quantity'] == 95, '实盘数量应为95'
    assert stock_take['difference_quantity'] == -5, '差异数量应为-5'
    
    response = requests.post(
        f'{BASE_URL}/stock-takes/{stock_take_id}/confirm',
        json={'handling_opinion': '确认盘点结果，调整库存'},
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, f'确认盘点失败: {response.text}'
    stock_take = response.json()
    print(f'  - 确认盘点成功: 状态={stock_take["status_text"]}')
    assert stock_take['status'] == 'confirmed', '盘点单状态应为已确认'
    
    response = requests.get(
        f'{BASE_URL}/batches/{batch_id}',
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, f'查询批次失败: {response.text}'
    batch_detail = response.json()['batch']
    print(f'  - 批次库存已调整: 可用={batch_detail["available_quantity"]}, 总数量={batch_detail["total_quantity"]}')
    assert batch_detail['available_quantity'] == 95, '可用库存应调整为95'
    assert batch_detail['total_quantity'] == 95, '总数量应调整为95'
    
    response = requests.get(
        f'{BASE_URL}/audit-logs',
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, f'查询审计日志失败: {response.text}'
    logs = response.json()
    stock_adjust_logs = [log for log in logs if log['action'] == 'stock_adjust' and log['material_batch_id'] == batch_id]
    assert len(stock_adjust_logs) >= 1, '应存在库存调整审计日志'
    adjust_log = stock_adjust_logs[0]
    print(f'  - 审计日志已记录: 数量 {adjust_log["old_quantity"]} → {adjust_log["new_quantity"]}')
    assert adjust_log['old_quantity'] == 100, '旧数量应为100'
    assert adjust_log['new_quantity'] == 95, '新数量应为95'
    assert adjust_log['operator_name'] == 'admin', '操作人应为admin'
    
    return True

def test_duty_officer_permission():
    """测试2: 值班员越权失败"""
    duty_token = login('duty', 'duty123')
    assert duty_token, '值班员登录失败'
    
    admin_token = login('admin', 'admin123')
    assert admin_token, '管理员登录失败'
    
    batch_data = {
        'batch_no': f'TEST-PD-DUTY-{int(time.time())}',
        'material_name': '权限测试物资',
        'total_quantity': 50,
        'unit': '箱',
        'production_date': '2024-01-01',
        'expiry_date': '2026-12-31',
        'warehouse_location': 'A-02-01',
        'reason': '权限测试批次'
    }
    response = requests.post(
        f'{BASE_URL}/batches',
        json=batch_data,
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '创建批次失败'
    batch = response.json()
    batch_id = batch['id']
    
    response = requests.post(
        f'{BASE_URL}/stock-takes',
        json={'material_batch_id': batch_id, 'reason': '越权测试'},
        headers=get_headers(duty_token)
    )
    assert response.status_code == 403, f'值班员创建盘点单应被拒绝，实际状态码: {response.status_code}'
    print(f'  - 值班员创建盘点单被正确拒绝: {response.status_code}')
    assert '只有仓库管理员可以执行此操作' in response.json()['message']
    
    response = requests.get(
        f'{BASE_URL}/stock-takes',
        headers=get_headers(admin_token)
    )
    all_stock_takes = response.json()
    assert len(all_stock_takes) >= 1, '应存在盘点单'
    confirmed_ids = [st['id'] for st in all_stock_takes if st['status'] == 'confirmed']
    if confirmed_ids:
        test_id = confirmed_ids[0]
        response = requests.get(
            f'{BASE_URL}/stock-takes/{test_id}',
            headers=get_headers(duty_token)
        )
        assert response.status_code == 200, f'值班员查看已确认盘点单应成功: {response.status_code}'
        print(f'  - 值班员可以查看已确认的盘点单')
        
        if len(all_stock_takes) > 0:
            pending_ids = [st['id'] for st in all_stock_takes if st['status'] == 'pending_confirm']
            if pending_ids:
                response = requests.get(
                    f'{BASE_URL}/stock-takes/{pending_ids[0]}',
                    headers=get_headers(duty_token)
                )
                assert response.status_code == 403, f'值班员查看待确认盘点单应被拒绝: {response.status_code}'
                print(f'  - 值班员查看待确认盘点单被正确拒绝: {response.status_code}')
    
    response = requests.get(
        f'{BASE_URL}/stock-takes',
        headers=get_headers(duty_token)
    )
    duty_stock_takes = response.json()
    for st in duty_stock_takes:
        assert st['status'] == 'confirmed', '值班员只能看到已确认的盘点单'
    print(f'  - 值班员列表只显示已确认盘点单，共 {len(duty_stock_takes)} 条')
    
    return True

def test_duplicate_stock_take_conflict():
    """测试3: 重复盘点冲突"""
    admin_token = login('admin', 'admin123')
    assert admin_token, '管理员登录失败'
    
    batch_data = {
        'batch_no': f'TEST-PD-DUP-{int(time.time())}',
        'material_name': '重复盘点测试物资',
        'total_quantity': 200,
        'unit': '件',
        'production_date': '2024-01-01',
        'expiry_date': '2026-12-31',
        'warehouse_location': 'A-03-01',
        'reason': '重复盘点测试批次'
    }
    response = requests.post(
        f'{BASE_URL}/batches',
        json=batch_data,
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '创建批次失败'
    batch = response.json()
    batch_id = batch['id']
    print(f'  - 创建批次成功: {batch["batch_no"]}')
    
    response = requests.post(
        f'{BASE_URL}/stock-takes',
        json={'material_batch_id': batch_id, 'reason': '第一次盘点'},
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '创建第一个盘点单失败'
    first_st = response.json()
    print(f'  - 创建第一个盘点单成功: {first_st["stock_take_no"]}, 状态={first_st["status_text"]}')
    
    response = requests.post(
        f'{BASE_URL}/stock-takes',
        json={'material_batch_id': batch_id, 'reason': '第二次盘点'},
        headers=get_headers(admin_token)
    )
    assert response.status_code == 400, f'重复创建盘点单应被拒绝，实际状态码: {response.status_code}'
    result = response.json()
    print(f'  - 重复创建盘点单被正确拒绝: {result["message"]}')
    assert 'conflicts' in result, '应返回冲突信息'
    assert len(result['conflicts']) >= 1, '应至少有一条冲突信息'
    assert first_st['stock_take_no'] in result['conflicts'][0], '冲突信息应包含盘点单号'
    print(f'  - 冲突信息: {result["conflicts"][0]}')
    
    return True

def test_borrow_conflict_detection():
    """测试4: 借用冲突检测"""
    admin_token = login('admin', 'admin123')
    assert admin_token, '管理员登录失败'
    duty_token = login('duty', 'duty123')
    assert duty_token, '值班员登录失败'
    
    batch_data = {
        'batch_no': f'TEST-PD-BORROW-{int(time.time())}',
        'material_name': '借用冲突测试物资',
        'total_quantity': 100,
        'unit': '套',
        'production_date': '2024-01-01',
        'expiry_date': '2026-12-31',
        'warehouse_location': 'A-04-01',
        'reason': '借用冲突测试批次'
    }
    response = requests.post(
        f'{BASE_URL}/batches',
        json=batch_data,
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '创建批次失败'
    batch = response.json()
    batch_id = batch['id']
    print(f'  - 创建批次成功: {batch["batch_no"]}')
    
    order_data = {
        'purpose': '盘点冲突测试借用',
        'items': [{'material_batch_id': batch_id, 'quantity': 10}]
    }
    response = requests.post(
        f'{BASE_URL}/orders',
        json=order_data,
        headers=get_headers(duty_token)
    )
    assert response.status_code == 200, '创建借用单失败'
    order = response.json()
    print(f'  - 创建借用单成功: {order["order_no"]}, 状态={order["status_text"]}')
    
    response = requests.post(
        f'{BASE_URL}/stock-takes',
        json={'material_batch_id': batch_id, 'reason': '测试借用冲突'},
        headers=get_headers(admin_token)
    )
    assert response.status_code == 400, f'有待审批借用单时应拒绝创建盘点单'
    result = response.json()
    print(f'  - 存在待审批借用单时创建盘点单被正确拒绝')
    assert 'conflicts' in result
    assert any('待审批' in c for c in result['conflicts']), '应提示存在待审批借用单'
    print(f'  - 冲突信息: {result["conflicts"][0]}')
    
    response = requests.post(
        f'{BASE_URL}/orders/{order["id"]}/approve',
        json={'reason': '同意测试借用'},
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '审批借用单失败'
    
    response = requests.post(
        f'{BASE_URL}/stock-takes',
        json={'material_batch_id': batch_id, 'reason': '测试借用冲突'},
        headers=get_headers(admin_token)
    )
    assert response.status_code == 400, f'有待领用借用单时应拒绝创建盘点单'
    result = response.json()
    print(f'  - 存在待领用借用单时创建盘点单被正确拒绝')
    assert any('待领用' in c for c in result['conflicts']), '应提示存在待领用借用单'
    
    response = requests.post(
        f'{BASE_URL}/orders/{order["id"]}/receive',
        json={'reason': '测试领用'},
        headers=get_headers(duty_token)
    )
    assert response.status_code == 200, '领用失败'
    
    response = requests.post(
        f'{BASE_URL}/stock-takes',
        json={'material_batch_id': batch_id, 'reason': '测试借用冲突'},
        headers=get_headers(admin_token)
    )
    assert response.status_code == 400, f'有未完成借用时应拒绝创建盘点单'
    result = response.json()
    print(f'  - 存在未完成借用时创建盘点单被正确拒绝')
    assert any('未完成借用' in c for c in result['conflicts']), '应提示存在未完成借用'
    
    return_data = {
        'items': [{'id': order['items'][0]['id'], 'returned_quantity': 10}]
    }
    response = requests.post(
        f'{BASE_URL}/orders/{order["id"]}/return',
        json=return_data,
        headers=get_headers(duty_token)
    )
    assert response.status_code == 200, '归还失败'
    print(f'  - 归还借用单成功')
    
    response = requests.post(
        f'{BASE_URL}/stock-takes',
        json={'material_batch_id': batch_id, 'reason': '借用归还后盘点'},
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, f'借用归还后应可以创建盘点单'
    st = response.json()
    print(f'  - 借用归还后成功创建盘点单: {st["stock_take_no"]}')
    
    return True

def test_data_persistence_after_restart():
    """测试5: 重启后仍可查询"""
    admin_token = login('admin', 'admin123')
    assert admin_token, '管理员登录失败'
    
    response = requests.get(
        f'{BASE_URL}/stock-takes',
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '查询盘点单失败'
    stock_takes_before = response.json()
    assert len(stock_takes_before) > 0, '应存在盘点单记录'
    
    confirmed_before = [st for st in stock_takes_before if st['status'] == 'confirmed']
    assert len(confirmed_before) > 0, '应存在已确认的盘点单'
    test_st_id = confirmed_before[0]['id']
    test_st_no = confirmed_before[0]['stock_take_no']
    print(f'  - 重启前查询到盘点单: {test_st_no}')
    
    response = requests.get(
        f'{BASE_URL}/stock-takes/{test_st_id}',
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '查询盘点单详情失败'
    detail_before = response.json()
    assert detail_before['stock_take']['stock_take_no'] == test_st_no
    
    response = requests.get(
        f'{BASE_URL}/audit-logs',
        headers=get_headers(admin_token)
    )
    logs_before = response.json()
    stock_take_logs_before = [log for log in logs_before if log['stock_take_id'] == test_st_id]
    assert len(stock_take_logs_before) > 0, '应存在盘点单相关审计日志'
    print(f'  - 重启前查询到审计日志 {len(stock_take_logs_before)} 条')
    
    print(f'  - 请重启后端服务后按任意键继续验证...')
    try:
        input()
    except:
        pass
    
    admin_token = login('admin', 'admin123')
    assert admin_token, '重启后管理员登录失败'
    
    response = requests.get(
        f'{BASE_URL}/stock-takes',
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '重启后查询盘点单失败'
    stock_takes_after = response.json()
    
    found = any(st['id'] == test_st_id and st['stock_take_no'] == test_st_no for st in stock_takes_after)
    assert found, f'重启后未找到盘点单 {test_st_no}'
    print(f'  - 重启后成功查询到盘点单: {test_st_no}')
    
    response = requests.get(
        f'{BASE_URL}/stock-takes/{test_st_id}',
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '重启后查询盘点单详情失败'
    detail_after = response.json()
    assert detail_after['stock_take']['stock_take_no'] == test_st_no
    assert detail_after['stock_take']['status'] == detail_before['stock_take']['status']
    print(f'  - 重启后盘点单详情一致，状态={detail_after["stock_take"]["status_text"]}')
    
    response = requests.get(
        f'{BASE_URL}/audit-logs',
        headers=get_headers(admin_token)
    )
    logs_after = response.json()
    stock_take_logs_after = [log for log in logs_after if log['stock_take_id'] == test_st_id]
    assert len(stock_take_logs_after) == len(stock_take_logs_before), '重启后审计日志数量不一致'
    print(f'  - 重启后审计日志完整，共 {len(stock_take_logs_after)} 条')
    
    return True

def test_borrow_return_not_affected():
    """测试6: 借用、归还、导入导出功能未被破坏"""
    admin_token = login('admin', 'admin123')
    assert admin_token, '管理员登录失败'
    duty_token = login('duty', 'duty123')
    assert duty_token, '值班员登录失败'
    
    batch_data = {
        'batch_no': f'TEST-BORROW-{int(time.time())}',
        'material_name': '借用流程测试物资',
        'total_quantity': 50,
        'unit': '个',
        'production_date': '2024-01-01',
        'expiry_date': '2026-12-31',
        'warehouse_location': 'B-01-01',
        'reason': '借用流程测试'
    }
    response = requests.post(
        f'{BASE_URL}/batches',
        json=batch_data,
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '创建批次失败'
    batch = response.json()
    batch_id = batch['id']
    print(f'  - 创建批次成功: {batch["batch_no"]}, 库存={batch["available_quantity"]}')
    
    order_data = {
        'purpose': '盘点功能回归测试借用',
        'items': [{'material_batch_id': batch_id, 'quantity': 10}]
    }
    response = requests.post(
        f'{BASE_URL}/orders',
        json=order_data,
        headers=get_headers(duty_token)
    )
    assert response.status_code == 200, '创建借用单失败'
    order = response.json()
    print(f'  - 值班员创建借用单成功: {order["order_no"]}')
    
    response = requests.post(
        f'{BASE_URL}/orders/{order["id"]}/approve',
        json={'reason': '同意测试借用'},
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '审批借用单失败'
    print(f'  - 管理员审批通过')
    
    response = requests.post(
        f'{BASE_URL}/orders/{order["id"]}/receive',
        json={'reason': '领用确认'},
        headers=get_headers(duty_token)
    )
    assert response.status_code == 200, '领用失败'
    print(f'  - 值班员领用成功')
    
    response = requests.get(
        f'{BASE_URL}/batches/{batch_id}',
        headers=get_headers(admin_token)
    )
    batch_after = response.json()['batch']
    assert batch_after['available_quantity'] == 40, '领用后库存应为40'
    print(f'  - 领用后库存: {batch_after["available_quantity"]}')
    
    return_data = {
        'items': [{'id': order['items'][0]['id'], 'returned_quantity': 10}],
        'reason': '使用完毕归还'
    }
    response = requests.post(
        f'{BASE_URL}/orders/{order["id"]}/return',
        json=return_data,
        headers=get_headers(duty_token)
    )
    assert response.status_code == 200, '归还失败'
    print(f'  - 值班员归还成功')
    
    response = requests.get(
        f'{BASE_URL}/batches/{batch_id}',
        headers=get_headers(admin_token)
    )
    batch_final = response.json()['batch']
    assert batch_final['available_quantity'] == 50, '归还后库存应恢复为50'
    print(f'  - 归还后库存恢复: {batch_final["available_quantity"]}')
    
    response = requests.get(
        f'{BASE_URL}/batches/export',
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, '导出失败'
    assert 'application/vnd.openxmlformats' in response.headers['Content-Type'], '导出格式错误'
    print(f'  - 导出功能正常')
    
    return True

def main():
    print('\n' + '='*60)
    print('库存盘点功能回归测试')
    print('='*60)
    
    results = []
    
    results.append(test_case('测试1: 管理员成功盘点', test_admin_create_and_confirm_stock_take))
    results.append(test_case('测试2: 值班员越权失败', test_duty_officer_permission))
    results.append(test_case('测试3: 重复盘点冲突', test_duplicate_stock_take_conflict))
    results.append(test_case('测试4: 借用冲突检测', test_borrow_conflict_detection))
    results.append(test_case('测试6: 借用归还流程未破坏', test_borrow_return_not_affected))
    results.append(test_case('测试5: 重启后数据持久化', test_data_persistence_after_restart))
    
    print('\n' + '='*60)
    print('测试总结')
    print('='*60)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f'通过: {passed}/{total}')
    
    if passed == total:
        print('\n✅ 所有测试通过！')
    else:
        print(f'\n❌ 有 {total - passed} 个测试失败，请检查！')
    
    return passed == total

if __name__ == '__main__':
    main()
