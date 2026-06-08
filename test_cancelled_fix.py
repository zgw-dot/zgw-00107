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

def test_cancelled_stock_take_visible_to_duty():
    """测试：值班员能看到已撤销盘点单"""
    print('=' * 60)
    print('测试: 值班员查看已撤销盘点单修复验证')
    print('=' * 60)
    
    admin_token = login('admin', 'admin123')
    duty_token = login('duty', 'duty123')
    
    if not admin_token or not duty_token:
        return False
    
    try:
        # ========== 管理员创建批次 ==========
        print('\n--- 步骤1: 管理员创建测试批次 ---')
        batch_data = {
            'batch_no': f'TEST-CANCEL-{int(__import__("time").time())}',
            'material_name': '已撤销盘点测试物资',
            'specification': '规格1',
            'total_quantity': 200,
            'unit': '个',
            'production_date': '2024-01-01',
            'expiry_date': '2026-12-31',
            'warehouse_location': 'A-01-01',
            'reason': '已撤销盘点测试'
        }
        response = requests.post(f'{BASE_URL}/batches', json=batch_data, headers=get_headers(admin_token))
        assert response.status_code == 200, f'创建批次失败: {response.text}'
        batch = response.json()
        batch_id = batch['id']
        print(f'  ✅ 创建批次: {batch["batch_no"]}, 库存={batch["total_quantity"]}')
        
        # ========== 管理员创建盘点单 ==========
        print('\n--- 步骤2: 管理员创建盘点单 ---')
        response = requests.post(
            f'{BASE_URL}/stock-takes',
            json={'material_batch_id': batch_id, 'reason': '测试撤销场景'},
            headers=get_headers(admin_token)
        )
        assert response.status_code == 200, f'创建盘点单失败: {response.text}'
        stock_take = response.json()
        st_id = stock_take['id']
        st_no = stock_take['stock_take_no']
        print(f'  ✅ 创建盘点单: {st_no}, 状态={stock_take["status_text"]}')
        
        # ========== 管理员撤销盘点单 ==========
        print('\n--- 步骤3: 管理员撤销盘点单 ---')
        response = requests.post(
            f'{BASE_URL}/stock-takes/{st_id}/cancel',
            json={'reason': '测试撤销，信息有误重新盘点'},
            headers=get_headers(admin_token)
        )
        assert response.status_code == 200, f'撤销盘点单失败: {response.text}'
        cancelled_st = response.json()
        assert cancelled_st['status'] == 'cancelled', '状态应为cancelled'
        assert cancelled_st['status_text'] == '已撤销', '状态文本应为已撤销'
        assert cancelled_st['canceller_name'] == 'admin', '撤销人应为admin'
        assert cancelled_st['cancelled_at'] != '', '应有撤销时间'
        print(f'  ✅ 撤销盘点单成功: 状态={cancelled_st["status_text"]}, 撤销人={cancelled_st["canceller_name"]}, 撤销时间={cancelled_st["cancelled_at"]}')
        
        # ========== 值班员查询列表 ==========
        print('\n--- 步骤4: 值班员查询盘点单列表 ---')
        response = requests.get(f'{BASE_URL}/stock-takes', headers=get_headers(duty_token))
        assert response.status_code == 200, f'值班员查询列表失败: {response.text}'
        duty_list = response.json()
        
        cancelled_in_list = [st for st in duty_list if st['status'] == 'cancelled']
        confirmed_in_list = [st for st in duty_list if st['status'] == 'confirmed']
        pending_in_list = [st for st in duty_list if st['status'] == 'pending_confirm']
        
        print(f'  - 值班员列表总记录数: {len(duty_list)}')
        print(f'  - 其中已撤销(cancelled): {len(cancelled_in_list)} 条')
        print(f'  - 其中已确认(confirmed): {len(confirmed_in_list)} 条')
        print(f'  - 其中待确认(pending_confirm): {len(pending_in_list)} 条')
        
        assert len(cancelled_in_list) > 0, '值班员列表应该能看到已撤销的盘点单'
        assert len(pending_in_list) == 0, '值班员列表不应该看到待确认的盘点单'
        
        our_cancelled = [st for st in cancelled_in_list if st['id'] == st_id]
        assert len(our_cancelled) == 1, '应该能找到刚才撤销的盘点单'
        assert our_cancelled[0]['status_text'] == '已撤销', '状态文本应为已撤销'
        assert our_cancelled[0]['canceller_name'] == 'admin', '应显示撤销人'
        assert our_cancelled[0]['cancelled_at'] != '', '应显示撤销时间'
        print(f'  ✅ 值班员列表中能看到已撤销盘点单: {our_cancelled[0]["stock_take_no"]}, 状态={our_cancelled[0]["status_text"]}')
        
        # ========== 值班员查看已撤销盘点单详情 ==========
        print('\n--- 步骤5: 值班员查看已撤销盘点单详情 ---')
        response = requests.get(f'{BASE_URL}/stock-takes/{st_id}', headers=get_headers(duty_token))
        assert response.status_code == 200, f'值班员查看已撤销详情失败: {response.text}'
        detail = response.json()
        
        assert detail['stock_take']['status'] == 'cancelled'
        assert detail['stock_take']['status_text'] == '已撤销'
        assert detail['stock_take']['canceller_name'] == 'admin'
        assert detail['stock_take']['cancelled_at'] != ''
        assert len(detail['audit_logs']) > 0, '应包含审计日志'
        
        print(f'  ✅ 值班员能正常打开已撤销盘点单详情')
        print(f'    - 盘点单号: {detail["stock_take"]["stock_take_no"]}')
        print(f'    - 状态: {detail["stock_take"]["status_text"]}')
        print(f'    - 撤销人: {detail["stock_take"]["canceller_name"]}')
        print(f'    - 撤销时间: {detail["stock_take"]["cancelled_at"]}')
        print(f'    - 审计日志: {len(detail["audit_logs"])} 条')
        
        # 验证审计日志包含撤销记录
        cancel_logs = [l for l in detail['audit_logs'] if l['action'] == 'cancel_stock_take']
        assert len(cancel_logs) > 0, '应包含撤销操作的审计日志'
        print(f'    - 撤销审计日志存在，原因: {cancel_logs[0]["reason"]}')
        
        # ========== 值班员尝试写操作被拒绝 ==========
        print('\n--- 步骤6: 验证值班员写操作被拒绝 ---')
        
        # 尝试创建盘点单
        response = requests.post(
            f'{BASE_URL}/stock-takes',
            json={'material_batch_id': batch_id, 'reason': '越权测试'},
            headers=get_headers(duty_token)
        )
        assert response.status_code == 403, f'值班员创建盘点单应返回403'
        print(f'  ✅ 值班员创建盘点单被正确拒绝: 403')
        
        # 尝试撤销（即使是已撤销的也不行）
        response = requests.post(
            f'{BASE_URL}/stock-takes/{st_id}/cancel',
            json={'reason': '越权测试'},
            headers=get_headers(duty_token)
        )
        assert response.status_code == 403, f'值班员撤销盘点单应返回403'
        print(f'  ✅ 值班员撤销盘点单被正确拒绝: 403')
        
        # ========== 同时验证已确认盘点单仍可见 ==========
        print('\n--- 步骤7: 验证已确认盘点单仍可见 ---')
        if len(confirmed_in_list) > 0:
            conf_st = confirmed_in_list[0]
            response = requests.get(f'{BASE_URL}/stock-takes/{conf_st["id"]}', headers=get_headers(duty_token))
            assert response.status_code == 200, f'值班员查看已确认详情失败: {response.text}'
            print(f'  ✅ 值班员仍可查看已确认盘点单: {conf_st["stock_take_no"]}')
        else:
            print(f'  ℹ️  暂无已确认盘点单，跳过此验证')
        
        # ========== 验证待确认盘点单详情值班员不能看 ==========
        print('\n--- 步骤8: 验证值班员不能看待确认盘点单详情 ---')
        # 管理员再创建一个待确认的盘点单
        batch_data2 = {
            'batch_no': f'TEST-PENDING-{int(__import__("time").time())}',
            'material_name': '待确认盘点测试',
            'total_quantity': 100,
            'unit': '个',
            'production_date': '2024-01-01',
            'expiry_date': '2026-12-31',
            'warehouse_location': 'A-01-02',
            'reason': '待确认测试'
        }
        response = requests.post(f'{BASE_URL}/batches', json=batch_data2, headers=get_headers(admin_token))
        batch2 = response.json()
        response = requests.post(
            f'{BASE_URL}/stock-takes',
            json={'material_batch_id': batch2['id'], 'reason': '测试待确认权限'},
            headers=get_headers(admin_token)
        )
        pending_st = response.json()
        
        response = requests.get(f'{BASE_URL}/stock-takes/{pending_st["id"]}', headers=get_headers(duty_token))
        assert response.status_code == 403, f'值班员看待确认详情应返回403'
        print(f'  ✅ 值班员不能看待确认盘点单详情: 403, {response.json()["message"]}')
        
        print('\n' + '=' * 60)
        print('✅ 已撤销盘点单修复验证全部通过！')
        print('=' * 60)
        return True
        
    except Exception as e:
        print(f'\n❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_cancelled_stock_take_visible_to_duty()
    sys.exit(0 if success else 1)
