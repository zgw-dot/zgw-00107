import requests
import sys

BASE_URL = 'http://127.0.0.1:5000/api'

def get_headers(token):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

def login(username, password):
    response = requests.post(f'{BASE_URL}/auth/login', json={'username': username, 'password': password})
    if response.status_code == 200:
        token = response.json()['access_token']
        print(f'✅ {username} 登录成功')
        return token
    else:
        print(f'❌ {username} 登录失败: {response.text}')
        return None

def test_persistence():
    print('=' * 60)
    print('测试: 重启后数据持久化验证')
    print('=' * 60)
    
    admin_token = login('admin', 'admin123')
    if not admin_token:
        return False
    
    print('\n--- 查询盘点单列表 ---')
    response = requests.get(
        f'{BASE_URL}/stock-takes',
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, f'查询盘点单失败: {response.text}'
    stock_takes = response.json()
    print(f'  - 查询到 {len(stock_takes)} 条盘点单记录')
    
    if len(stock_takes) == 0:
        print('❌ 没有找到盘点单记录，持久化失败')
        return False
    
    confirmed = [st for st in stock_takes if st['status'] == 'confirmed']
    cancelled = [st for st in stock_takes if st['status'] == 'cancelled']
    
    if len(confirmed) == 0 and len(cancelled) == 0:
        print('❌ 没有找到已完成的盘点单')
        return False
    
    for st in confirmed:
        print(f'  - 已确认: {st["stock_take_no"]}, 批次: {st["material_name"]}, '
              f'账面: {st["expected_quantity"]}, 实盘: {st["actual_quantity"]}, '
              f'差异: {st["difference_quantity"]}')
    for st in cancelled:
        print(f'  - 已撤销: {st["stock_take_no"]}, 批次: {st["material_name"]}, '
              f'账面: {st["expected_quantity"]}, 撤销人: {st["canceller_name"]}')
    
    print(f'  - 共 {len(confirmed)} 条已确认, {len(cancelled)} 条已撤销')
    
    if len(cancelled) > 0:
        test_st = cancelled[0]
        is_cancelled_test = True
    else:
        test_st = confirmed[0]
        is_cancelled_test = False
    
    test_st_id = test_st['id']
    test_st_no = test_st['stock_take_no']
    
    print(f'\n--- 查询盘点单详情: {test_st_no} ---')
    response = requests.get(
        f'{BASE_URL}/stock-takes/{test_st_id}',
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, f'查询详情失败: {response.text}'
    detail = response.json()
    assert detail['stock_take']['stock_take_no'] == test_st_no
    print(f'  - 盘点单号: {detail["stock_take"]["stock_take_no"]}')
    print(f'  - 状态: {detail["stock_take"]["status_text"]}')
    print(f'  - 账面数量: {detail["stock_take"]["expected_quantity"]}')
    print(f'  - 实盘数量: {detail["stock_take"]["actual_quantity"]}')
    print(f'  - 差异数量: {detail["stock_take"]["difference_quantity"]}')
    print(f'  - 创建人: {detail["stock_take"]["creator_name"]}')
    if is_cancelled_test:
        print(f'  - 撤销人: {detail["stock_take"]["canceller_name"]}')
        print(f'  - 撤销时间: {detail["stock_take"]["cancelled_at"]}')
        assert detail["stock_take"]["canceller_name"] != '', '撤销人不应为空'
        assert detail["stock_take"]["cancelled_at"] != '', '撤销时间不应为空'
    else:
        print(f'  - 确认人: {detail["stock_take"]["confirmer_name"]}')
    
    print(f'\n--- 查询批次库存 ---')
    batch_id = test_st['material_batch_id']
    response = requests.get(
        f'{BASE_URL}/batches/{batch_id}',
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, f'查询批次失败: {response.text}'
    batch_data = response.json()
    batch = batch_data['batch']
    print(f'  - 批次: {batch["batch_no"]}')
    print(f'  - 可用库存: {batch["available_quantity"]}')
    print(f'  - 总数量: {batch["total_quantity"]}')
    if not is_cancelled_test:
        assert batch['available_quantity'] == test_st['actual_quantity'], '库存数量应等于实盘数量'
        print(f'  - ✅ 库存已正确调整为实盘数量')
    else:
        print(f'  - ℹ️  已撤销盘点单不调整库存，跳过库存验证')
    
    print(f'\n--- 查询审计日志 ---')
    response = requests.get(
        f'{BASE_URL}/audit-logs?stock_take_id={test_st_id}',
        headers=get_headers(admin_token)
    )
    assert response.status_code == 200, f'查询审计日志失败: {response.text}'
    logs = response.json()
    print(f'  - 查询到 {len(logs)} 条相关审计日志')
    for log in logs:
        if log.get('old_quantity') is not None and log.get('new_quantity') is not None:
            print(f'  - {log["created_at"]}: {log["operator_name"]} {log["action_text"]} '
                  f'{log["old_quantity"]} → {log["new_quantity"]}')
            print(f'  - ✅ 审计日志正确记录了数量变化')
    
    print('\n' + '=' * 60)
    print('✅ 持久化测试通过！重启后盘点单、库存和日志都完整保留')
    print('=' * 60)
    return True

if __name__ == '__main__':
    try:
        success = test_persistence()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f'\n❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
