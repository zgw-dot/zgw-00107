<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <el-button link @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <span class="page-title" style="margin-left: 10px;">批次详情</span>
      </div>
    </div>

    <el-card v-loading="loading">
      <template #header>
        <div style="font-weight: 600;">
          {{ batch?.material_name }} - {{ batch?.batch_no }}
          <el-tag :type="getBatchTagType(batch)" style="margin-left: 10px;">
            {{ getBatchStatusText(batch) }}
          </el-tag>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="批次号">{{ batch?.batch_no }}</el-descriptions-item>
        <el-descriptions-item label="物资名称">{{ batch?.material_name }}</el-descriptions-item>
        <el-descriptions-item label="规格型号">{{ batch?.specification || '-' }}</el-descriptions-item>
        <el-descriptions-item label="单位">{{ batch?.unit }}</el-descriptions-item>
        <el-descriptions-item label="总数量">{{ batch?.total_quantity }}{{ batch?.unit }}</el-descriptions-item>
        <el-descriptions-item label="可用数量">
          <span :style="{ color: batch?.available_quantity === 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
            {{ batch?.available_quantity }}{{ batch?.unit }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="生产日期">{{ batch?.production_date }}</el-descriptions-item>
        <el-descriptions-item label="有效期至">{{ batch?.expiry_date }}</el-descriptions-item>
        <el-descriptions-item label="库位">{{ batch?.warehouse_location }}</el-descriptions-item>
        <el-descriptions-item label="供应商">{{ batch?.supplier || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建人">{{ batch?.creator_name }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ batch?.created_at }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ batch?.remark || '-' }}</el-descriptions-item>
      </el-descriptions>
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
import { getBatchDetail } from '../api/batch'

const route = useRoute()
const loading = ref(false)
const batch = ref(null)
const auditLogs = ref([])

function getBatchTagType(row) {
  if (!row) return ''
  if (row.status === 'rotated') return 'info'
  if (row.is_expired) return 'danger'
  return 'success'
}

function getBatchStatusText(row) {
  if (!row) return ''
  if (row.status === 'rotated') return '已轮换'
  if (row.is_expired) return '已过期'
  return '正常'
}

function getLogTagType(action) {
  const map = {
    'create_batch': 'success',
    'import_batch': 'success',
    'rotate_out': 'warning',
    'rotate_in': 'warning'
  }
  return map[action] || 'primary'
}

function getStatusText(status) {
  const map = {
    'normal': '正常',
    'rotated': '已轮换',
    'expired': '已过期'
  }
  return map[status] || status
}

async function loadData() {
  loading.value = true
  try {
    const res = await getBatchDetail(route.params.id)
    batch.value = res.batch
    auditLogs.value = res.audit_logs
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
