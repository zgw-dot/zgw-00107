<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <el-button link @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <span class="page-title" style="margin-left: 10px;">盘点单详情</span>
      </div>
    </div>

    <el-card v-loading="loading">
      <template #header>
        <div style="font-weight: 600;">
          {{ stockTake?.stock_take_no }}
          <el-tag :type="getStatusTagType(stockTake?.status)" style="margin-left: 10px;">
            {{ stockTake?.status_text }}
          </el-tag>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="盘点单号">{{ stockTake?.stock_take_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusTagType(stockTake?.status)">{{ stockTake?.status_text }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="批次号">{{ stockTake?.batch_no }}</el-descriptions-item>
        <el-descriptions-item label="物资名称">{{ stockTake?.material_name }}</el-descriptions-item>
        <el-descriptions-item label="规格型号">{{ stockTake?.specification || '-' }}</el-descriptions-item>
        <el-descriptions-item label="单位">{{ stockTake?.unit }}</el-descriptions-item>
        <el-descriptions-item label="账面数量">
          <span style="font-weight: 600;">{{ stockTake?.expected_quantity }}{{ stockTake?.unit }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="实盘数量">
          <span v-if="stockTake?.actual_quantity !== null" style="font-weight: 600;">{{ stockTake?.actual_quantity }}{{ stockTake?.unit }}</span>
          <span v-else style="color: #909399;">待录入</span>
        </el-descriptions-item>
        <el-descriptions-item label="差异数量">
          <span v-if="stockTake?.actual_quantity !== null" :style="{ color: stockTake?.difference_quantity !== 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
            {{ stockTake?.difference_quantity > 0 ? '+' : '' }}{{ stockTake?.difference_quantity }}{{ stockTake?.unit }}
          </span>
          <span v-else style="color: #909399;">-</span>
        </el-descriptions-item>
        <el-descriptions-item label="创建人">{{ stockTake?.creator_name }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ stockTake?.created_at }}</el-descriptions-item>
        <el-descriptions-item v-if="stockTake?.confirmed_by" label="确认人">{{ stockTake?.confirmer_name }}</el-descriptions-item>
        <el-descriptions-item v-if="stockTake?.confirmed_at" label="确认时间">{{ stockTake?.confirmed_at }}</el-descriptions-item>
        <el-descriptions-item v-if="stockTake?.cancelled_by" label="撤销人">{{ stockTake?.canceller_name }}</el-descriptions-item>
        <el-descriptions-item v-if="stockTake?.cancelled_at" label="撤销时间">{{ stockTake?.cancelled_at }}</el-descriptions-item>
        <el-descriptions-item v-if="stockTake?.difference_reason" label="差异原因" :span="2">{{ stockTake?.difference_reason }}</el-descriptions-item>
        <el-descriptions-item v-if="stockTake?.handling_opinion" label="处理意见" :span="2">{{ stockTake?.handling_opinion }}</el-descriptions-item>
      </el-descriptions>

      <div v-if="isKeeper && stockTake?.status === 'pending_confirm'" style="margin-top: 20px;">
        <el-button type="success" @click="openEditDialog">录入实盘数量</el-button>
        <el-button v-if="stockTake?.actual_quantity !== null" type="warning" @click="openConfirmDialog">确认盘点</el-button>
        <el-button type="danger" @click="openCancelDialog">撤销盘点</el-button>
      </div>
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
              <el-tag v-if="log.old_status" size="small" type="info">{{ log.old_status }}</el-tag>
              <el-icon v-if="log.old_status && log.new_status" style="margin: 0 5px;"><ArrowRight /></el-icon>
              <el-tag v-if="log.new_status" size="small" type="success">{{ log.new_status }}</el-tag>
            </div>
            <div v-if="log.old_quantity !== null || log.new_quantity !== null" style="margin-bottom: 8px;">
              <strong>数量变化：</strong>
              <span v-if="log.old_quantity !== null">{{ log.old_quantity }}</span>
              <el-icon v-if="log.old_quantity !== null && log.new_quantity !== null" style="margin: 0 5px;"><ArrowRight /></el-icon>
              <span v-if="log.new_quantity !== null" :style="{ color: log.new_quantity !== log.old_quantity ? '#f56c6c' : '#67c23a', fontWeight: 600 }">{{ log.new_quantity }}</span>
            </div>
            <div v-if="log.detail" style="color: #606266; font-size: 13px;">
              {{ log.detail }}
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-dialog v-model="editDialogVisible" title="录入实盘数量" width="500px">
      <el-alert type="info" :closable="false" style="margin-bottom: 20px;">
        批次：{{ stockTake?.batch_no }} - {{ stockTake?.material_name }}，账面数量：{{ stockTake?.expected_quantity }}{{ stockTake?.unit }}
      </el-alert>
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="实盘数量" required>
          <el-input-number v-model="editForm.actual_quantity" :min="0" :step="1" />
          <span style="margin-left: 10px;">{{ stockTake?.unit }}</span>
        </el-form-item>
        <el-form-item v-if="editForm.actual_quantity !== null && editForm.actual_quantity !== stockTake?.expected_quantity" label="差异">
          <span :style="{ color: (editForm.actual_quantity - stockTake?.expected_quantity) !== 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
            {{ (editForm.actual_quantity - stockTake?.expected_quantity) > 0 ? '+' : '' }}{{ editForm.actual_quantity - stockTake?.expected_quantity }}{{ stockTake?.unit }}
          </span>
        </el-form-item>
        <el-form-item v-if="editForm.actual_quantity !== null && editForm.actual_quantity !== stockTake?.expected_quantity" label="差异原因" required>
          <el-input v-model="editForm.difference_reason" type="textarea" :rows="2" placeholder="请填写差异原因（必填）" />
        </el-form-item>
        <el-form-item label="处理意见">
          <el-input v-model="editForm.handling_opinion" type="textarea" :rows="2" placeholder="请填写处理意见" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleUpdate">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="confirmDialogVisible" title="确认盘点" width="500px">
      <el-alert type="warning" :closable="false" style="margin-bottom: 20px;">
        确认后将调整批次库存到实盘数量，此操作不可撤销，请仔细核对！
      </el-alert>
      <el-descriptions v-if="stockTake" :column="1" border size="small">
        <el-descriptions-item label="盘点单号">{{ stockTake.stock_take_no }}</el-descriptions-item>
        <el-descriptions-item label="批次">{{ stockTake.batch_no }} - {{ stockTake.material_name }}</el-descriptions-item>
        <el-descriptions-item label="账面数量">{{ stockTake.expected_quantity }}{{ stockTake.unit }}</el-descriptions-item>
        <el-descriptions-item label="实盘数量">{{ stockTake.actual_quantity }}{{ stockTake.unit }}</el-descriptions-item>
        <el-descriptions-item label="差异数量">
          <span :style="{ color: stockTake.difference_quantity !== 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
            {{ stockTake.difference_quantity > 0 ? '+' : '' }}{{ stockTake.difference_quantity }}{{ stockTake.unit }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item v-if="stockTake.difference_reason" label="差异原因">{{ stockTake.difference_reason }}</el-descriptions-item>
      </el-descriptions>
      <el-form style="margin-top: 20px;">
        <el-form-item label="处理意见" required>
          <el-input v-model="confirmForm.handling_opinion" type="textarea" :rows="2" placeholder="请填写处理意见（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="confirmDialogVisible = false">取消</el-button>
        <el-button type="warning" :loading="submitting" @click="handleConfirm">确认盘点</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cancelDialogVisible" title="撤销盘点" width="400px">
      <el-alert type="warning" :closable="false" style="margin-bottom: 20px;">
        确定要撤销盘点单 {{ stockTake?.stock_take_no }} 吗？
      </el-alert>
      <el-form>
        <el-form-item label="撤销原因" required>
          <el-input v-model="cancelReason" type="textarea" :rows="2" placeholder="请填写撤销原因（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="handleCancel">确认撤销</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { getStockTakeDetail, updateStockTake, confirmStockTake, cancelStockTake } from '../api/stockTake'
import { useUserStore } from '../store/user'

const route = useRoute()
const userStore = useUserStore()
const isKeeper = userStore.isKeeper
const loading = ref(false)
const submitting = ref(false)
const stockTake = ref(null)
const auditLogs = ref([])
const editDialogVisible = ref(false)
const confirmDialogVisible = ref(false)
const cancelDialogVisible = ref(false)
const cancelReason = ref('')

const editForm = reactive({
  actual_quantity: null,
  difference_reason: '',
  handling_opinion: ''
})

const confirmForm = reactive({
  handling_opinion: ''
})

function getStatusTagType(status) {
  const map = {
    'pending_confirm': 'warning',
    'confirmed': 'success',
    'cancelled': 'info'
  }
  return map[status] || 'primary'
}

function getLogTagType(action) {
  const map = {
    'create_stock_take': 'success',
    'confirm_stock_take': 'warning',
    'cancel_stock_take': 'info',
    'stock_adjust': 'danger'
  }
  return map[action] || 'primary'
}

async function loadData() {
  loading.value = true
  try {
    const res = await getStockTakeDetail(route.params.id)
    stockTake.value = res.stock_take
    auditLogs.value = res.audit_logs
  } finally {
    loading.value = false
  }
}

function openEditDialog() {
  editForm.actual_quantity = stockTake.value.actual_quantity
  editForm.difference_reason = stockTake.value.difference_reason || ''
  editForm.handling_opinion = stockTake.value.handling_opinion || ''
  editDialogVisible.value = true
}

async function handleUpdate() {
  if (editForm.actual_quantity === null || editForm.actual_quantity < 0) {
    ElMessage.warning('请输入有效的实盘数量')
    return
  }
  const diff = editForm.actual_quantity - stockTake.value.expected_quantity
  if (diff !== 0 && !editForm.difference_reason.trim()) {
    ElMessage.warning('存在差异时必须填写差异原因')
    return
  }
  submitting.value = true
  try {
    await updateStockTake(stockTake.value.id, editForm)
    ElMessage.success('实盘信息已保存')
    editDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function openConfirmDialog() {
  confirmForm.handling_opinion = stockTake.value.handling_opinion || ''
  confirmDialogVisible.value = true
}

async function handleConfirm() {
  if (!confirmForm.handling_opinion.trim()) {
    ElMessage.warning('请填写处理意见')
    return
  }
  submitting.value = true
  try {
    await confirmStockTake(stockTake.value.id, confirmForm)
    ElMessage.success('盘点确认成功，库存已调整')
    confirmDialogVisible.value = false
    loadData()
  } catch (e) {
    if (e.response?.data?.conflicts) {
      ElMessageBox.alert(
        `<div style="color: #f56c6c;">${e.response.data.message}<br/><br/>${e.response.data.conflicts.join('<br/>')}</div>`,
        '存在冲突',
        { dangerouslyUseHTMLString: true }
      )
    }
  } finally {
    submitting.value = false
  }
}

function openCancelDialog() {
  cancelReason.value = ''
  cancelDialogVisible.value = true
}

async function handleCancel() {
  if (!cancelReason.value.trim()) {
    ElMessage.warning('请填写撤销原因')
    return
  }
  submitting.value = true
  try {
    await cancelStockTake(stockTake.value.id, cancelReason.value)
    ElMessage.success('盘点单已撤销')
    cancelDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>
