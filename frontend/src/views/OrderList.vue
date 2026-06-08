<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">借用单据管理</div>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="openCreateDialog" v-if="userStore.isDuty || userStore.isKeeper">
          申请借用
        </el-button>
      </div>
    </div>

    <el-card>
      <el-table :data="orders" stripe v-loading="loading">
        <el-table-column prop="order_no" label="单据号" width="160" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getOrderTagType(row.status)">
              {{ row.status_text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="purpose" label="用途" show-overflow-tooltip />
        <el-table-column prop="creator_name" label="申请人" width="100" />
        <el-table-column prop="approver_name" label="审批人" width="100">
          <template #default="{ row }">{{ row.approver_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="借用物资" min-width="200">
          <template #default="{ row }">
            <div v-for="item in row.items" :key="item.id" style="font-size: 13px;">
              {{ item.material_name }} ({{ item.quantity }}{{ item.unit }})
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">详情</el-button>
            <el-button 
              v-if="userStore.isKeeper && row.status === 'pending_approval'" 
              link 
              type="success" 
              @click="openApproveDialog(row)"
            >审批</el-button>
            <el-button 
              v-if="row.status === 'approved'" 
              link 
              type="primary" 
              @click="openReceiveDialog(row)"
            >领用</el-button>
            <el-button 
              v-if="row.status === 'received'" 
              link 
              type="success" 
              @click="openReturnDialog(row)"
            >归还</el-button>
            <el-button 
              v-if="row.status === 'received'" 
              link 
              type="danger" 
              @click="openDamageDialog(row)"
            >报损</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="申请借用" width="700px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="借用用途" required>
          <el-input v-model="createForm.purpose" type="textarea" :rows="2" placeholder="请填写借用用途（必填）" />
        </el-form-item>
        <el-form-item label="借用物资" required>
          <div style="width: 100%;">
            <div v-for="(item, idx) in createForm.items" :key="idx" style="display: flex; gap: 10px; margin-bottom: 10px; align-items: center;">
              <el-select 
                v-model="item.material_batch_id" 
                placeholder="选择批次" 
                style="flex: 2;"
                @change="onBatchChange(idx)"
              >
                <el-option 
                  v-for="b in availableBatches" 
                  :key="b.id" 
                  :label="`${b.material_name} - ${b.batch_no} (${b.available_quantity}${b.unit})`" 
                  :value="b.id" 
                />
              </el-select>
              <el-input-number v-model="item.quantity" :min="1" :max="getMaxQty(item.material_batch_id)" style="flex: 1;" />
              <el-button type="danger" :icon="Delete" circle @click="removeItem(idx)" />
            </div>
            <el-button type="primary" plain :icon="Plus" @click="addItem" style="width: 100%;">添加物资</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">提交申请</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="approveDialogVisible" title="审批借用单" width="500px">
      <div style="margin-bottom: 15px;">
        <strong>单据号：</strong>{{ currentOrder?.order_no }}<br/>
        <strong>申请人：</strong>{{ currentOrder?.creator_name }}<br/>
        <strong>用途：</strong>{{ currentOrder?.purpose }}
      </div>
      <el-form label-width="80px">
        <el-form-item label="审批意见" required>
          <el-input v-model="reason" type="textarea" :rows="3" placeholder="请填写审批意见（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="handleReject">拒绝</el-button>
        <el-button type="success" :loading="submitting" @click="handleApprove">通过</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="receiveDialogVisible" title="领用确认" width="400px">
      <div style="margin-bottom: 15px;">
        <strong>单据号：</strong>{{ currentOrder?.order_no }}<br/>
        <strong>借用物资：</strong>
        <div v-for="item in currentOrder?.items" :key="item.id" style="padding-left: 20px;">
          {{ item.material_name }} - {{ item.quantity }}{{ item.unit }}
        </div>
      </div>
      <el-form label-width="80px">
        <el-form-item label="领用备注" required>
          <el-input v-model="reason" type="textarea" :rows="3" placeholder="请填写领用备注（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="receiveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleReceive">确认领用</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="returnDialogVisible" title="归还物资" width="550px">
      <div style="margin-bottom: 15px;">
        <strong>单据号：</strong>{{ currentOrder?.order_no }}
      </div>
      <el-table :data="returnForm.items" border size="small">
        <el-table-column prop="material_name" label="物资名称" />
        <el-table-column label="应还数量">
          <template #default="{ row }">
            {{ row.quantity - row.returned_quantity - row.damaged_quantity }}{{ row.unit }}
          </template>
        </el-table-column>
        <el-table-column label="归还数量">
          <template #default="{ row }">
            <el-input-number 
              v-model="row.returned_quantity" 
              :min="0" 
              :max="row.quantity - row.returned_quantity - row.damaged_quantity" 
            />
          </template>
        </el-table-column>
      </el-table>
      <el-form label-width="80px" style="margin-top: 15px;">
        <el-form-item label="归还备注" required>
          <el-input v-model="returnForm.reason" type="textarea" :rows="2" placeholder="请填写归还备注（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="returnDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="submitting" @click="handleReturn">确认归还</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="damageDialogVisible" title="物资报损" width="550px">
      <div style="margin-bottom: 15px;">
        <strong>单据号：</strong>{{ currentOrder?.order_no }}
      </div>
      <el-table :data="damageForm.items" border size="small">
        <el-table-column prop="material_name" label="物资名称" />
        <el-table-column label="未还数量">
          <template #default="{ row }">
            {{ row.quantity - row.returned_quantity - row.damaged_quantity }}{{ row.unit }}
          </template>
        </el-table-column>
        <el-table-column label="报损数量">
          <template #default="{ row }">
            <el-input-number 
              v-model="row.damaged_quantity" 
              :min="0" 
              :max="row.quantity - row.returned_quantity - row.damaged_quantity" 
            />
          </template>
        </el-table-column>
      </el-table>
      <el-form label-width="80px" style="margin-top: 15px;">
        <el-form-item label="报损原因" required>
          <el-input v-model="damageForm.reason" type="textarea" :rows="2" placeholder="请填写报损原因（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="damageDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="handleDamage">确认报损</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { useUserStore } from '../store/user'
import { getAvailableBatches } from '../api/batch'
import { 
  getOrders, 
  createOrder, 
  approveOrder, 
  rejectOrder, 
  receiveOrder, 
  returnOrder, 
  damageOrder 
} from '../api/order'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const orders = ref([])
const availableBatches = ref([])
const currentOrder = ref(null)
const reason = ref('')

const createDialogVisible = ref(false)
const approveDialogVisible = ref(false)
const receiveDialogVisible = ref(false)
const returnDialogVisible = ref(false)
const damageDialogVisible = ref(false)

const createForm = reactive({
  purpose: '',
  items: [{ material_batch_id: '', quantity: 1 }]
})

const returnForm = reactive({
  reason: '',
  items: []
})

const damageForm = reactive({
  reason: '',
  items: []
})

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

function getMaxQty(batchId) {
  const b = availableBatches.value.find(x => x.id === batchId)
  return b ? b.available_quantity : 99999
}

function onBatchChange(idx) {
  const item = createForm.items[idx]
  item.quantity = 1
}

function addItem() {
  createForm.items.push({ material_batch_id: '', quantity: 1 })
}

function removeItem(idx) {
  if (createForm.items.length > 1) {
    createForm.items.splice(idx, 1)
  }
}

async function loadData() {
  loading.value = true
  try {
    const [o, b] = await Promise.all([
      getOrders(),
      getAvailableBatches()
    ])
    orders.value = o
    availableBatches.value = b
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  createForm.purpose = ''
  createForm.items = [{ material_batch_id: '', quantity: 1 }]
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!createForm.purpose.trim()) {
    ElMessage.warning('请填写借用用途')
    return
  }
  const validItems = createForm.items.filter(i => i.material_batch_id && i.quantity > 0)
  if (validItems.length === 0) {
    ElMessage.warning('请选择借用物资并填写数量')
    return
  }
  submitting.value = true
  try {
    await createOrder({ purpose: createForm.purpose, items: validItems })
    ElMessage.success('申请提交成功')
    createDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function openApproveDialog(row) {
  currentOrder.value = row
  reason.value = ''
  approveDialogVisible.value = true
}

async function handleApprove() {
  if (!reason.value.trim()) {
    ElMessage.warning('请填写审批意见')
    return
  }
  submitting.value = true
  try {
    await approveOrder(currentOrder.value.id, reason.value)
    ElMessage.success('审批通过')
    approveDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

async function handleReject() {
  if (!reason.value.trim()) {
    ElMessage.warning('请填写拒绝原因')
    return
  }
  submitting.value = true
  try {
    await rejectOrder(currentOrder.value.id, reason.value)
    ElMessage.success('已拒绝')
    approveDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function openReceiveDialog(row) {
  currentOrder.value = row
  reason.value = ''
  receiveDialogVisible.value = true
}

async function handleReceive() {
  if (!reason.value.trim()) {
    ElMessage.warning('请填写领用备注')
    return
  }
  submitting.value = true
  try {
    await receiveOrder(currentOrder.value.id, reason.value)
    ElMessage.success('领用成功')
    receiveDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function openReturnDialog(row) {
  currentOrder.value = row
  returnForm.reason = ''
  returnForm.items = row.items.map(i => ({
    id: i.id,
    material_name: i.material_name,
    unit: i.unit,
    quantity: i.quantity,
    returned_quantity: i.returned_quantity,
    damaged_quantity: i.damaged_quantity,
    returned_quantity_input: 0
  }))
  returnDialogVisible.value = true
}

async function handleReturn() {
  if (!returnForm.reason.trim()) {
    ElMessage.warning('请填写归还备注')
    return
  }
  const items = returnForm.items.map(i => ({
    id: i.id,
    returned_quantity: i.returned_quantity_input || 0
  }))
  if (items.every(i => i.returned_quantity === 0)) {
    ElMessage.warning('请填写归还数量')
    return
  }
  submitting.value = true
  try {
    await returnOrder(currentOrder.value.id, { reason: returnForm.reason, items })
    ElMessage.success('归还成功')
    returnDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function openDamageDialog(row) {
  currentOrder.value = row
  damageForm.reason = ''
  damageForm.items = row.items.map(i => ({
    id: i.id,
    material_name: i.material_name,
    unit: i.unit,
    quantity: i.quantity,
    returned_quantity: i.returned_quantity,
    damaged_quantity: i.damaged_quantity,
    damaged_quantity_input: 0
  }))
  damageDialogVisible.value = true
}

async function handleDamage() {
  if (!damageForm.reason.trim()) {
    ElMessage.warning('请填写报损原因')
    return
  }
  const items = damageForm.items.map(i => ({
    id: i.id,
    damaged_quantity: i.damaged_quantity_input || 0
  }))
  if (items.every(i => i.damaged_quantity === 0)) {
    ElMessage.warning('请填写报损数量')
    return
  }
  submitting.value = true
  try {
    await damageOrder(currentOrder.value.id, { reason: damageForm.reason, items })
    ElMessage.success('报损成功')
    damageDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function viewDetail(row) {
  router.push(`/orders/${row.id}`)
}

onMounted(loadData)
</script>
