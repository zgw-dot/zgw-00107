<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">操作审计日志</div>
    </div>

    <el-card>
      <el-table :data="logs" stripe v-loading="loading">
        <el-table-column prop="action_text" label="操作类型" width="140">
          <template #default="{ row }">
            <el-tag :type="getLogTagType(row.action)">{{ row.action_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联单据">
          <template #default="{ row }">
            <el-link v-if="row.stock_take_id" type="primary" @click="goStockTake(row.stock_take_id)">
              盘点单 #{{ row.stock_take_id }}
            </el-link>
            <el-link v-else-if="row.borrow_order_id" type="primary" @click="goOrder(row.borrow_order_id)">
              借用单 #{{ row.borrow_order_id }}
            </el-link>
            <el-link v-else-if="row.material_batch_id" type="primary" @click="goBatch(row.material_batch_id)">
              批次 #{{ row.material_batch_id }}
            </el-link>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="operator_name" label="操作人" width="100" />
        <el-table-column prop="reason" label="原因/备注" show-overflow-tooltip />
        <el-table-column label="数量变化" width="140">
          <template #default="{ row }">
            <template v-if="row.old_quantity !== null || row.new_quantity !== null">
              <span v-if="row.old_quantity !== null">{{ row.old_quantity }}</span>
              <span style="margin: 0 5px;">→</span>
              <span v-if="row.new_quantity !== null" :style="{ color: row.new_quantity !== row.old_quantity ? '#f56c6c' : '#67c23a', fontWeight: 600 }">{{ row.new_quantity }}</span>
            </template>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态变更" width="200">
          <template #default="{ row }">
            <template v-if="row.old_status || row.new_status">
              <el-tag v-if="row.old_status" size="small" type="info">{{ getStatusText(row.old_status) }}</el-tag>
              <span style="margin: 0 5px;">→</span>
              <el-tag v-if="row.new_status" size="small" type="success">{{ getStatusText(row.new_status) }}</el-tag>
            </template>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" show-overflow-tooltip />
        <el-table-column prop="created_at" label="操作时间" width="160" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAuditLogs } from '../api/order'

const router = useRouter()
const loading = ref(false)
const logs = ref([])

function getLogTagType(action) {
  const map = {
    'create_batch': 'success',
    'import_batch': 'success',
    'rotate_out': 'warning',
    'rotate_in': 'warning',
    'create_order': 'primary',
    'approve': 'success',
    'reject': 'danger',
    'receive': 'success',
    'return': 'success',
    'damage': 'danger',
    'create_stock_take': 'success',
    'confirm_stock_take': 'warning',
    'cancel_stock_take': 'info',
    'stock_adjust': 'danger'
  }
  return map[action] || 'info'
}

function getStatusText(status) {
  const map = {
    'normal': '正常',
    'rotated': '已轮换',
    'expired': '已过期',
    'pending_approval': '待审批',
    'approved': '待领用',
    'rejected': '已拒绝',
    'received': '使用中',
    'returned': '已归还',
    'damaged': '已报损',
    'pending_confirm': '待确认',
    'confirmed': '已确认',
    'cancelled': '已撤销'
  }
  return map[status] || status
}

function goOrder(id) {
  router.push(`/orders/${id}`)
}

function goBatch(id) {
  router.push(`/batches/${id}`)
}

function goStockTake(id) {
  router.push(`/stock-takes/${id}`)
}

async function loadData() {
  loading.value = true
  try {
    logs.value = await getAuditLogs()
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
