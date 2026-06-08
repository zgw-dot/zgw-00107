<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">数据概览</div>
    </div>

    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon icon-blue">
              <el-icon><Goods /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalBatches }}</div>
              <div class="stat-label">物资批次总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon icon-green">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.normalBatches }}</div>
              <div class="stat-label">正常可用批次</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon icon-red">
              <el-icon><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.expiredBatches }}</div>
              <div class="stat-label">已过期批次</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon icon-orange">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pendingOrders }}</div>
              <div class="stat-label">待处理单据</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div style="font-weight: 600;">即将过期批次</div>
          </template>
          <el-table :data="expiringBatches" stripe>
            <el-table-column prop="batch_no" label="批次号" width="140" />
            <el-table-column prop="material_name" label="物资名称" />
            <el-table-column prop="available_quantity" label="可用数量">
              <template #default="{ row }">
                {{ row.available_quantity }}{{ row.unit }}
              </template>
            </el-table-column>
            <el-table-column prop="expiry_date" label="有效期至" width="120" />
            <el-table-column label="剩余天数" width="100">
              <template #default="{ row }">
                <el-tag :type="getExpiryTagType(row)">
                  {{ getDaysToExpiry(row) }}天
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <div style="font-weight: 600;">最近操作记录</div>
          </template>
          <el-table :data="recentLogs" stripe>
            <el-table-column prop="action_text" label="操作类型" width="120" />
            <el-table-column prop="operator_name" label="操作人" width="100" />
            <el-table-column prop="reason" label="原因/备注" show-overflow-tooltip />
            <el-table-column prop="created_at" label="操作时间" width="160" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import dayjs from 'dayjs'
import { getBatches } from '../api/batch'
import { getOrders, getAuditLogs } from '../api/order'

const batches = ref([])
const orders = ref([])
const auditLogs = ref([])

const stats = computed(() => {
  const total = batches.value.length
  const normal = batches.value.filter(b => b.status === 'normal' && !b.is_expired).length
  const expired = batches.value.filter(b => b.is_expired).length
  const pending = orders.value.filter(o => ['pending_approval', 'approved'].includes(o.status)).length
  return {
    totalBatches: total,
    normalBatches: normal,
    expiredBatches: expired,
    pendingOrders: pending
  }
})

const expiringBatches = computed(() => {
  const today = dayjs()
  return batches.value
    .filter(b => !b.is_expired && b.status === 'normal')
    .filter(b => {
      const days = dayjs(b.expiry_date).diff(today, 'day')
      return days <= 30 && days >= 0
    })
    .sort((a, b) => dayjs(a.expiry_date).valueOf() - dayjs(b.expiry_date).valueOf())
    .slice(0, 10)
})

const recentLogs = computed(() => auditLogs.value.slice(0, 10))

function getDaysToExpiry(row) {
  return dayjs(row.expiry_date).diff(dayjs(), 'day')
}

function getExpiryTagType(row) {
  const days = getDaysToExpiry(row)
  if (days <= 7) return 'danger'
  if (days <= 15) return 'warning'
  return 'success'
}

async function loadData() {
  const [b, o, l] = await Promise.all([
    getBatches(),
    getOrders(),
    getAuditLogs()
  ])
  batches.value = b
  orders.value = o
  auditLogs.value = l
}

onMounted(loadData)
</script>

<style scoped>
.stat-card {
  margin-bottom: 0;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  color: #fff;
}

.icon-blue { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.icon-green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
.icon-red { background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%); }
.icon-orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}
</style>
