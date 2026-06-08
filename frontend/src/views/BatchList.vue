<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">物资批次管理</div>
      <div class="header-actions">
        <el-upload
          ref="uploadRef"
          :show-file-list="false"
          :before-upload="beforeImport"
          style="display: inline-block; margin-right: 10px;"
        >
          <el-button type="primary" :icon="Upload">导入批次</el-button>
        </el-upload>
        <el-button type="success" :icon="Download" @click="handleExport">导出批次</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增批次</el-button>
      </div>
    </div>

    <el-card>
      <el-table :data="batches" stripe v-loading="loading">
        <el-table-column prop="batch_no" label="批次号" width="140" />
        <el-table-column prop="material_name" label="物资名称" width="140" />
        <el-table-column prop="specification" label="规格型号" width="120" />
        <el-table-column prop="total_quantity" label="总数量">
          <template #default="{ row }">
            {{ row.total_quantity }}{{ row.unit }}
          </template>
        </el-table-column>
        <el-table-column prop="available_quantity" label="可用数量">
          <template #default="{ row }">
            <span :style="{ color: row.available_quantity === 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
              {{ row.available_quantity }}{{ row.unit }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="production_date" label="生产日期" width="110" />
        <el-table-column prop="expiry_date" label="有效期至" width="110" />
        <el-table-column prop="warehouse_location" label="库位" width="100" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="getBatchTagType(row)">
              {{ getBatchStatusText(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">详情</el-button>
            <el-button 
              link 
              type="warning" 
              @click="openRotateDialog(row)"
              :disabled="row.status !== 'normal' || row.is_expired"
            >轮换</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="新增批次" width="600px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="批次号" required>
          <el-input v-model="createForm.batch_no" placeholder="请输入批次号" />
        </el-form-item>
        <el-form-item label="物资名称" required>
          <el-input v-model="createForm.material_name" placeholder="请输入物资名称" />
        </el-form-item>
        <el-form-item label="规格型号">
          <el-input v-model="createForm.specification" placeholder="请输入规格型号" />
        </el-form-item>
        <el-form-item label="数量" required>
          <el-input-number v-model="createForm.total_quantity" :min="1" />
          <span style="margin-left: 10px;">
            <el-select v-model="createForm.unit" placeholder="单位" style="width: 100px;">
              <el-option label="个" value="个" />
              <el-option label="箱" value="箱" />
              <el-option label="包" value="包" />
              <el-option label="瓶" value="瓶" />
              <el-option label="件" value="件" />
              <el-option label="套" value="套" />
            </el-select>
          </span>
        </el-form-item>
        <el-form-item label="生产日期" required>
          <el-date-picker v-model="createForm.production_date" type="date" value-format="YYYY-MM-DD" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="有效期至" required>
          <el-date-picker v-model="createForm.expiry_date" type="date" value-format="YYYY-MM-DD" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="库位" required>
          <el-input v-model="createForm.warehouse_location" placeholder="如：A-01-01" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="createForm.supplier" placeholder="请输入供应商" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="入库原因" required>
          <el-input v-model="createForm.reason" type="textarea" :rows="2" placeholder="请填写入库原因（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rotateDialogVisible" title="批次轮换" width="600px">
      <el-alert type="info" :closable="false" style="margin-bottom: 20px;">
        轮换后旧批次「{{ currentRotateBatch?.batch_no }}」将标记为已轮换，可用库存清零，新批次继承库存数量。
      </el-alert>
      <el-form :model="rotateForm" label-width="100px">
        <el-form-item label="新批次号" required>
          <el-input v-model="rotateForm.new_batch.batch_no" placeholder="请输入新批次号" />
        </el-form-item>
        <el-form-item label="生产日期" required>
          <el-date-picker v-model="rotateForm.new_batch.production_date" type="date" value-format="YYYY-MM-DD" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="有效期至" required>
          <el-date-picker v-model="rotateForm.new_batch.expiry_date" type="date" value-format="YYYY-MM-DD" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="rotateForm.new_batch.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="轮换原因" required>
          <el-input v-model="rotateForm.reason" type="textarea" :rows="2" placeholder="请填写轮换原因（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rotateDialogVisible = false">取消</el-button>
        <el-button type="warning" :loading="submitting" @click="handleRotate">确定轮换</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importReasonDialog" title="导入原因" width="400px" @close="pendingFile = null">
      <el-form label-width="80px">
        <el-form-item label="导入原因" required>
          <el-input v-model="importReason" type="textarea" :rows="3" placeholder="请填写导入原因（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importReasonDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmImport">确定导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Download } from '@element-plus/icons-vue'
import { getBatches, createBatch, rotateBatch, exportBatches, importBatches } from '../api/batch'

const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const batches = ref([])
const createDialogVisible = ref(false)
const rotateDialogVisible = ref(false)
const importReasonDialog = ref(false)
const currentRotateBatch = ref(null)
const pendingFile = ref(null)
const importReason = ref('')

const createForm = reactive({
  batch_no: '',
  material_name: '',
  specification: '',
  total_quantity: 1,
  unit: '个',
  production_date: '',
  expiry_date: '',
  warehouse_location: '',
  supplier: '',
  remark: '',
  reason: ''
})

const rotateForm = reactive({
  reason: '',
  new_batch: {
    batch_no: '',
    production_date: '',
    expiry_date: '',
    remark: ''
  }
})

function getBatchTagType(row) {
  if (row.status === 'rotated') return 'info'
  if (row.is_expired) return 'danger'
  return 'success'
}

function getBatchStatusText(row) {
  if (row.status === 'rotated') return '已轮换'
  if (row.is_expired) return '已过期'
  return '正常'
}

async function loadData() {
  loading.value = true
  try {
    batches.value = await getBatches()
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  Object.assign(createForm, {
    batch_no: '',
    material_name: '',
    specification: '',
    total_quantity: 1,
    unit: '个',
    production_date: '',
    expiry_date: '',
    warehouse_location: '',
    supplier: '',
    remark: '',
    reason: ''
  })
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!createForm.batch_no || !createForm.material_name || !createForm.total_quantity || 
      !createForm.production_date || !createForm.expiry_date || 
      !createForm.warehouse_location || !createForm.reason) {
    ElMessage.warning('请填写完整信息，入库原因必填')
    return
  }
  submitting.value = true
  try {
    await createBatch(createForm)
    ElMessage.success('创建成功')
    createDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function openRotateDialog(row) {
  currentRotateBatch.value = row
  rotateForm.reason = ''
  rotateForm.new_batch = {
    batch_no: '',
    production_date: '',
    expiry_date: '',
    remark: ''
  }
  rotateDialogVisible.value = true
}

async function handleRotate() {
  if (!rotateForm.new_batch.batch_no || !rotateForm.new_batch.production_date ||
      !rotateForm.new_batch.expiry_date || !rotateForm.reason) {
    ElMessage.warning('请填写完整信息，轮换原因必填')
    return
  }
  submitting.value = true
  try {
    await rotateBatch(currentRotateBatch.value.id, rotateForm)
    ElMessage.success('轮换成功')
    rotateDialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function viewDetail(row) {
  router.push(`/batches/${row.id}`)
}

function beforeImport(file) {
  pendingFile.value = file
  importReason.value = ''
  importReasonDialog.value = true
  return false
}

async function confirmImport() {
  if (!importReason.value.trim()) {
    ElMessage.warning('请填写导入原因')
    return
  }
  try {
    const res = await importBatches(pendingFile.value, importReason.value)
    ElMessage.success(`导入成功：${res.success} 条，跳过：${res.skip} 条`)
    if (res.errors && res.errors.length > 0) {
      ElMessageBox.alert(
        `<div style="max-height: 300px; overflow-y: auto;">${res.errors.join('<br/>')}</div>`,
        '导入详情',
        { dangerouslyUseHTMLString: true }
      )
    }
    importReasonDialog.value = false
    loadData()
  } catch (e) {}
}

async function handleExport() {
  try {
    const blob = await exportBatches()
    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.download = `物资批次_${Date.now()}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {}
}

onMounted(loadData)
</script>
