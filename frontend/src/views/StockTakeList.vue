<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">库存盘点管理</div>
      <div class="header-actions">
        <el-button v-if="isKeeper" type="primary" :icon="Plus" @click="openCreateDialog">发起盘点</el-button>
      </div>
    </div>

    <el-card>
      <el-table :data="stockTakes" stripe v-loading="loading">
        <el-table-column prop="stock_take_no" label="盘点单号" width="140" />
        <el-table-column prop="batch_no" label="批次号" width="140" />
        <el-table-column prop="material_name" label="物资名称" width="140" />
        <el-table-column prop="specification" label="规格型号" width="120" />
        <el-table-column prop="expected_quantity" label="账面数量">
          <template #default="{ row }">
            {{ row.expected_quantity }}{{ row.unit }}
          </template>
        </el-table-column>
        <el-table-column prop="actual_quantity" label="实盘数量">
          <template #default="{ row }">
            <span v-if="row.actual_quantity !== null">{{ row.actual_quantity }}{{ row.unit }}</span>
            <span v-else style="color: #909399;">待录入</span>
          </template>
        </el-table-column>
        <el-table-column prop="difference_quantity" label="差异数量">
          <template #default="{ row }">
            <span v-if="row.actual_quantity !== null" :style="{ color: row.difference_quantity !== 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
              {{ row.difference_quantity > 0 ? '+' : '' }}{{ row.difference_quantity }}{{ row.unit }}
            </span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ row.status_text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="canceller_name" label="撤销人" width="100">
          <template #default="{ row }">
            <span v-if="row.canceller_name">{{ row.canceller_name }}</span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="cancelled_at" label="撤销时间" width="160">
          <template #default="{ row }">
            <span v-if="row.cancelled_at">{{ row.cancelled_at }}</span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建人" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">详情</el-button>
            <el-button 
              v-if="isKeeper && row.status === 'pending_confirm'"
              link 
              type="success" 
              @click="openEditDialog(row)"
            >录入</el-button>
            <el-button 
              v-if="isKeeper && row.status === 'pending_confirm' && row.actual_quantity !== null"
              link 
              type="warning" 
              @click="openConfirmDialog(row)"
            >确认</el-button>
            <el-button 
              v-if="isKeeper && row.status === 'pending_confirm'"
              link 
              type="danger" 
              @click="openCancelDialog(row)"
            >撤销</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="发起盘点" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="选择批次" required>
          <el-select v-model="createForm.material_batch_id" placeholder="请选择要盘点的批次" style="width: 100%;" @change="onBatchChange">
            <el-option 
              v-for="batch in availableBatches" 
              :key="batch.id" 
              :label="`${batch.batch_no} - ${batch.material_name} (可用: ${batch.available_quantity}${batch.unit})`" 
              :value="batch.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="selectedBatch" label="当前库存">
          <span style="font-weight: 600;">{{ selectedBatch.available_quantity }}{{ selectedBatch.unit }}</span>
        </el-form-item>
        <el-form-item label="盘点原因" required>
          <el-input v-model="createForm.reason" type="textarea" :rows="2" placeholder="请填写盘点原因（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">确定发起</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="录入实盘数量" width="500px">
      <el-alert v-if="currentStockTake" type="info" :closable="false" style="margin-bottom: 20px;">
        批次：{{ currentStockTake.batch_no }} - {{ currentStockTake.material_name }}，账面数量：{{ currentStockTake.expected_quantity }}{{ currentStockTake.unit }}
      </el-alert>
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="实盘数量" required>
          <el-input-number v-model="editForm.actual_quantity" :min="0" :step="1" />
          <span style="margin-left: 10px;">{{ currentStockTake?.unit }}</span>
        </el-form-item>
        <el-form-item v-if="editForm.actual_quantity !== null && editForm.actual_quantity !== currentStockTake?.expected_quantity" label="差异">
          <span :style="{ color: (editForm.actual_quantity - currentStockTake?.expected_quantity) !== 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
            {{ (editForm.actual_quantity - currentStockTake?.expected_quantity) > 0 ? '+' : '' }}{{ editForm.actual_quantity - currentStockTake?.expected_quantity }}{{ currentStockTake?.unit }}
          </span>
        </el-form-item>
        <el-form-item v-if="editForm.actual_quantity !== null && editForm.actual_quantity !== currentStockTake?.expected_quantity" label="差异原因" required>
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
      <el-descriptions v-if="currentStockTake" :column="1" border size="small">
        <el-descriptions-item label="盘点单号">{{ currentStockTake.stock_take_no }}</el-descriptions-item>
        <el-descriptions-item label="批次">{{ currentStockTake.batch_no }} - {{ currentStockTake.material_name }}</el-descriptions-item>
        <el-descriptions-item label="账面数量">{{ currentStockTake.expected_quantity }}{{ currentStockTake.unit }}</el-descriptions-item>
        <el-descriptions-item label="实盘数量">{{ currentStockTake.actual_quantity }}{{ currentStockTake.unit }}</el-descriptions-item>
        <el-descriptions-item label="差异数量">
          <span :style="{ color: currentStockTake.difference_quantity !== 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
            {{ currentStockTake.difference_quantity > 0 ? '+' : '' }}{{ currentStockTake.difference_quantity }}{{ currentStockTake.unit }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item v-if="currentStockTake.difference_reason" label="差异原因">{{ currentStockTake.difference_reason }}</el-descriptions-item>
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
        确定要撤销盘点单 {{ currentStockTake?.stock_take_no }} 吗？
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
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getStockTakes, createStockTake, updateStockTake, confirmStockTake, cancelStockTake } from '../api/stockTake'
import { getBatches } from '../api/batch'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()
const isKeeper = userStore.isKeeper
const loading = ref(false)
const submitting = ref(false)
const stockTakes = ref([])
const batches = ref([])
const createDialogVisible = ref(false)
const editDialogVisible = ref(false)
const confirmDialogVisible = ref(false)
const cancelDialogVisible = ref(false)
const currentStockTake = ref(null)
const cancelReason = ref('')

const createForm = reactive({
  material_batch_id: null,
  reason: ''
})

const editForm = reactive({
  actual_quantity: null,
  difference_reason: '',
  handling_opinion: ''
})

const confirmForm = reactive({
  handling_opinion: ''
})

const selectedBatch = computed(() => {
  if (!createForm.material_batch_id) return null
  return batches.value.find(b => b.id === createForm.material_batch_id)
})

const availableBatches = computed(() => {
  return batches.value.filter(b => b.status === 'normal' && !b.is_expired && b.pending_stock_take_count === 0)
})

function getStatusTagType(status) {
  const map = {
    'pending_confirm': 'warning',
    'confirmed': 'success',
    'cancelled': 'info'
  }
  return map[status] || 'primary'
}

async function loadData() {
  loading.value = true
  try {
    stockTakes.value = await getStockTakes()
  } finally {
    loading.value = false
  }
}

async function loadBatches() {
  try {
    batches.value = await getBatches()
  } catch (e) {}
}

function onBatchChange() {
}

function openCreateDialog() {
  createForm.material_batch_id = null
  createForm.reason = ''
  loadBatches()
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!createForm.material_batch_id || !createForm.reason.trim()) {
    ElMessage.warning('请选择批次并填写盘点原因')
    return
  }
  submitting.value = true
  try {
    await createStockTake(createForm)
    ElMessage.success('盘点单创建成功')
    createDialogVisible.value = false
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

function openEditDialog(row) {
  currentStockTake.value = row
  editForm.actual_quantity = row.actual_quantity
  editForm.difference_reason = row.difference_reason || ''
  editForm.handling_opinion = row.handling_opinion || ''
  editDialogVisible.value = true
}

async function handleUpdate() {
  if (editForm.actual_quantity === null || editForm.actual_quantity < 0) {
    ElMessage.warning('请输入有效的实盘数量')
    return
  }
  const diff = editForm.actual_quantity - currentStockTake.value.expected_quantity
  if (diff !== 0 && !editForm.difference_reason.trim()) {
    ElMessage.warning('存在差异时必须填写差异原因')
    return
  }
  submitting.value = true
  try {
    await updateStockTake(currentStockTake.value.id, editForm)
    ElMessage.success('实盘信息已保存')
    editDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function openConfirmDialog(row) {
  currentStockTake.value = row
  confirmForm.handling_opinion = row.handling_opinion || ''
  confirmDialogVisible.value = true
}

async function handleConfirm() {
  if (!confirmForm.handling_opinion.trim()) {
    ElMessage.warning('请填写处理意见')
    return
  }
  submitting.value = true
  try {
    await confirmStockTake(currentStockTake.value.id, confirmForm)
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

function openCancelDialog(row) {
  currentStockTake.value = row
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
    await cancelStockTake(currentStockTake.value.id, cancelReason.value)
    ElMessage.success('盘点单已撤销')
    cancelDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function viewDetail(row) {
  router.push(`/stock-takes/${row.id}`)
}

onMounted(() => {
  loadData()
  loadBatches()
})
</script>
