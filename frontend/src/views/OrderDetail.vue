<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <el-button link @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <span class="page-title" style="margin-left: 10px;">借用单详情</span>
      </div>
    </div>

    <el-card v-loading="loading">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 600;">
            {{ order?.order_no }}
            <el-tag :type="getOrderTagType(order?.status)" style="margin-left: 10px;">
              {{ order?.status_text }}
            </el-tag>
          </span>
          <span style="color: #909399; font-size: 13px;">
            创建时间：{{ order?.created_at }}
          </span>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="申请人">{{ order?.creator_name }}</el-descriptions-item>
        <el-descriptions-item label="审批人">{{ order?.approver_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="领用人">{{ order?.receiver_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="归还人">{{ order?.returner_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="审批时间">{{ order?.approved_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="领用时间">{{ order?.received_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="归还时间">{{ order?.returned_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="借用用途" :span="2">{{ order?.purpose }}</el-descriptions-item>
      </el-descriptions>

      <div style="margin-top: 20px;">
        <h4 style="margin-bottom: 10px;">借用物资明细</h4>
        <el-table :data="order?.items" border>
          <el-table-column prop="batch_no" label="批次号" />
          <el-table-column prop="material_name" label="物资名称" />
          <el-table-column prop="specification" label="规格型号" />
          <el-table-column prop="warehouse_location" label="库位" width="100" />
          <el-table-column label="借用数量">
            <template #default="{ row }">{{ row.quantity }}{{ row.unit }}</template>
          </el-table-column>
          <el-table-column label="已归还">
            <template #default="{ row }">
              <span style="color: #67c23a;">{{ row.returned_quantity }}{{ row.unit }}</span>
            </template>
          </el-table-column>
          <el-table-column label="已报损">
            <template #default="{ row }">
              <span style="color: #f56c6c;">{{ row.damaged_quantity }}{{ row.unit }}</span>
            </template>
          </el-table-column>
          <el-table-column label="未归还">
            <template #default="{ row }">
              <span :style="{ color: row.quantity - row.returned_quantity - row.damaged_quantity > 0 ? '#e6a23c' : '#909399' }">
                {{ row.quantity - row.returned_quantity - row.damaged_quantity }}{{ row.unit }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header>
        <div style="font-weight: 600;">状态流转记录</div>
      </template>
      <el-steps :active="getStepIndex()" finish-status="success" simple>
        <el-step title="创建申请" :description="order?.creator_name" />
        <el-step title="审批" :description="order?.approver_name || '待处理'" />
        <el-step title="领用出库" :description="order?.receiver_name || '待领用'" />
        <el-step title="归还/报损" :description="order?.returner_name || '待归还'" />
      </el-steps>
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header>
        <div style="font-weight: 600;">操作审计日志</div>
      </template>
      <el-timeline>
        <el-timeline-item
          v-for="log in auditLogs"
          :key="log.id"
          :timestamp="log.created_at"
          placement="top"
        >
          <el-card shadow="hover">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <el-tag size="large" :type="getLogTagType(log.action)">{{ log.action_text }}</el-tag>
              <span style="color: #909399; font-size: 13px;">操作人：{{ log.operator_name }}</span>
            </div>
            <div style="margin-bottom: 8px;">
              <strong>原因/备注：</strong>{{ log.reason }}
            </div>
            <div v-if="log.old_status || log.new_status" style="margin-bottom: 8px;">
              <el-tag v-if="log.old_status" size="small" type="info">{{ getStatusText(log.old_status) }}</el-tag>
              <el-icon v-if="log.old_status && log.new_status" style="margin: 0 5px;"><ArrowRight /></el-icon>
              <el-tag v-if="log.new_status" size="small" type="success">{{ getStatusText(log.new_status) }}</el-tag>
            </div>
            <div v-if="log.detail" style="color: #606266; font-size: 13px;">
              {{ log.detail }}
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getOrderDetail } from '../api/order'

const route = useRoute()
const loading = ref(false)
const order = ref(null)
const auditLogs = ref([])

function getOrderTagType(status) {
  const map = {
    'pending_approval': 'warning',
    'approved': 'primary',
    'rejected': 'danger',
    'received': 'success',
    'returned': 'info',
    'damaged': 'danger'
  }
  return map[status] || 'info'
}

function getStepIndex() {
  if (!order.value) return 0
  const status = order.value.status
  if (status === 'pending_approval') return 0
  if (status === 'approved') return 1
  if (status === 'received') return 2
  if (status === 'returned' || status === 'damaged') return 3
  if (status === 'rejected') return 0
  return 0
}

function getLogTagType(action) {
  const map = {
    'create_order': 'primary',
    'approve': 'success',
    'reject': 'danger',
    'receive': 'success',
    'return': 'success',
    'damage': 'danger'
  }
  return map[action] || 'info'
}

function getStatusText(status) {
  const map = {
    'pending_approval': '待审批',
    'approved': '待领用',
    'rejected': '已拒绝',
    'received': '使用中',
    'returned': '已归还',
    'damaged': '已报损'
  }
  return map[status] || status
}

async function loadData() {
  loading.value = true
  try {
    const res = await getOrderDetail(route.params.id)
    order.value = res.order
    auditLogs.value = res.audit_logs
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
