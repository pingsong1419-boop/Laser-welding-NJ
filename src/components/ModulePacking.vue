<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import type { PackBoxInfo, ModuleItem, PackingRecord, PreCheckResponse } from '../types/modulePacking'
import type { AppConfig } from '../types/mes'
import { dispatchParamsAndCheckInput, preCheckModules, uploadPackingOrder, retryUploadPacking } from '../services/modulePackingApi'

const props = defineProps<{
  config: AppConfig
}>()

const emit = defineEmits<{
  (e: 'log', level: 'info' | 'success' | 'warn' | 'error', msg: string): void
  (e: 'api-record', record: any): void
}>()

// ============ 状态 ============
const packCode = ref('')
const packInputRef = ref<HTMLInputElement | null>(null)

const packInfo = ref<PackBoxInfo | null>(null)
const moduleList = ref<ModuleItem[]>([])
const currentStatus = ref<'idle' | 'scanning_pack' | 'ready' | 'prechecking' | 'reviewing' | 'uploading' | 'completed' | 'failed'>('idle')
const statusMessage = ref('')

const preCheckResult = ref<PreCheckResponse | null>(null)
const uploadResult = ref<{ success: boolean; message: string; recordId?: string } | null>(null)

// 历史记录（用于补传）
const historyRecords = ref<PackingRecord[]>([])
const showHistory = ref(false)

// 当前操作员
const operator = ref('operator')

// ============ 计算属性 ============
const isPackScanned = computed(() => packInfo.value !== null)
const moduleCount = computed(() => moduleList.value.length)
const completedCount = computed(() => moduleList.value.filter(m => m.isPacked).length)

const canPreCheck = computed(() => {
  return packInfo.value !== null && moduleList.value.length > 0 && currentStatus.value === 'ready'
})

const failedRecords = computed(() => {
  return historyRecords.value.filter(r => r.uploadStatus === 'fail')
})

// ============ 方法 ============
function focusPackInput() {
  nextTick(() => packInputRef.value?.focus())
}

function resetAll() {
  packCode.value = ''
  packInfo.value = null
  moduleList.value = []
  currentStatus.value = 'idle'
  statusMessage.value = ''
  preCheckResult.value = null
  uploadResult.value = null
  focusPackInput()
  emit('log', 'info', '模组入箱流程已复位')
}

// 1. 扫描PACK箱 → MES自动下发参数+模组清单
async function handlePackScan() {
  const code = packCode.value.trim()
  if (!code) return

  currentStatus.value = 'scanning_pack'
  statusMessage.value = '正在获取MES参数及模组清单...'
  emit('log', 'info', `[模组入箱] 扫描PACK箱: ${code}`)

  const apiRec: any = {
    title: 'MES参数下发/投入校验',
    url: props.config.paramDispatchUrl || '/mes-api/api/Packing/DispatchParams',
    status: 'pending',
    time: new Date().toLocaleTimeString(),
    reqBody: { packCode: code, processCode: props.config.technicsProcessCode },
    resBody: null
  }
  emit('api-record', apiRec)

  try {
    const res = await dispatchParamsAndCheckInput(props.config, code)
    apiRec.status = res.allowed ? 'success' : 'error'
    apiRec.resBody = res

    if (res.allowed) {
      const details = res.details as any
      packInfo.value = {
        packCode: code,
        orderCode: details?.orderCode || code,
        routeNo: details?.routeNo || '',
        moduleType: details?.moduleType || '未知类型',
        expectedModuleCount: Number(details?.expectedModuleCount) || 0,
        scannedModuleCount: 0,
        mesParams: details,
        inputCheckResult: res
      }

      // 自动解析MES下发的模组清单
      const autoModules: ModuleItem[] = []
      const mesModuleList = details?.moduleList || details?.modules || []
      if (Array.isArray(mesModuleList) && mesModuleList.length > 0) {
        mesModuleList.forEach((m: any, idx: number) => {
          autoModules.push({
            moduleCode: String(m.moduleCode || m.code || m.barcode || ''),
            scanOrder: idx + 1,
            scanTime: new Date().toLocaleString(),
            logicCheckResult: 'pending',
            mesCheckResult: 'pending',
            isPacked: false
          })
        })
      }
      moduleList.value = autoModules
      if (packInfo.value) {
        packInfo.value.scannedModuleCount = autoModules.length
      }

      currentStatus.value = 'ready'
      const autoMsg = autoModules.length > 0
        ? `PACK箱校验通过，MES自动下发 ${autoModules.length} 个模组`
        : 'PACK箱校验通过（未获取到模组清单，请确认MES参数）'
      statusMessage.value = autoMsg
      emit('log', 'success', `[模组入箱] ${autoMsg}`)
    } else {
      currentStatus.value = 'failed'
      statusMessage.value = `PACK箱校验失败: ${res.message || '未知错误'}`
      emit('log', 'error', `[模组入箱] PACK箱 ${code} 投入校验失败: ${res.message}`)
      alert(`PACK箱投入校验失败！\n${res.message}`)
    }
  } catch (err: any) {
    apiRec.status = 'error'
    apiRec.resBody = err.message
    currentStatus.value = 'failed'
    statusMessage.value = `请求异常: ${err.message}`
    emit('log', 'error', `[模组入箱] PACK箱校验异常: ${err.message}`)
  }
}

// 2. 入箱预校验
async function handlePreCheck() {
  if (!packInfo.value || moduleList.value.length === 0) return

  currentStatus.value = 'prechecking'
  statusMessage.value = '正在进行入箱预校验...'
  emit('log', 'info', `[模组入箱] 开始预校验，共 ${moduleList.value.length} 个模组`)

  const apiRec: any = {
    title: '入箱预校验',
    url: props.config.inputCheckUrl || '/mes-api/api/Packing/PreCheckInput',
    status: 'pending',
    time: new Date().toLocaleTimeString(),
    reqBody: {
      packCode: packInfo.value!.packCode,
      orderCode: packInfo.value!.orderCode,
      routeNo: packInfo.value!.routeNo,
      processCode: props.config.technicsProcessCode,
      moduleList: moduleList.value.map(m => ({ moduleCode: m.moduleCode, scanOrder: m.scanOrder }))
    },
    resBody: null
  }
  emit('api-record', apiRec)

  try {
    const res = await preCheckModules(props.config, {
      packCode: packInfo.value!.packCode,
      orderCode: packInfo.value!.orderCode,
      routeNo: packInfo.value!.routeNo,
      processCode: props.config.technicsProcessCode,
      moduleList: moduleList.value.map(m => ({ moduleCode: m.moduleCode, scanOrder: m.scanOrder }))
    })

    apiRec.status = res.success ? 'success' : 'error'
    apiRec.resBody = res
    preCheckResult.value = res

    if (res.success && res.logicCheck.passed && res.mesCheck.passed) {
      currentStatus.value = 'reviewing'
      statusMessage.value = '预校验通过，请进行人工复判'
      moduleList.value.forEach(m => {
        m.logicCheckResult = 'pass'
        m.mesCheckResult = 'pass'
      })
      emit('log', 'success', `[模组入箱] 预校验通过: 产线逻辑✅ MES投入✅`)
    } else {
      currentStatus.value = 'failed'
      const failMsg = `${res.logicCheck.passed ? '' : '产线逻辑校验失败; '}${res.mesCheck.passed ? '' : 'MES投入校验失败'}`
      statusMessage.value = `预校验未通过: ${failMsg}`
      moduleList.value.forEach(m => {
        m.logicCheckResult = res.logicCheck.passed ? 'pass' : 'fail'
        m.mesCheckResult = res.mesCheck.passed ? 'pass' : 'fail'
      })
      emit('log', 'error', `[模组入箱] 预校验失败: ${failMsg}`)
      alert(`入箱预校验未通过！\n产线逻辑: ${res.logicCheck.message}\nMES投入: ${res.mesCheck.message}`)
    }
  } catch (err: any) {
    apiRec.status = 'error'
    apiRec.resBody = err.message
    currentStatus.value = 'failed'
    statusMessage.value = `预校验异常: ${err.message}`
    emit('log', 'error', `[模组入箱] 预校验异常: ${err.message}`)
  }
}

// 3. 人工复判
function handleManualReview(passed: boolean) {
  if (!preCheckResult.value) return

  if (passed) {
    currentStatus.value = 'reviewing'
    statusMessage.value = '人工复判通过，准备上传入箱顺序'
    emit('log', 'info', `[模组入箱] 人工复判: 通过`)
    handleUpload()
  } else {
    currentStatus.value = 'failed'
    statusMessage.value = '人工复判: 拒绝入箱'
    emit('log', 'warn', `[模组入箱] 人工复判: 拒绝入箱`)
    alert('已拒绝入箱，流程终止。')
  }
}

// 4. 上传入箱顺序
async function handleUpload() {
  if (!packInfo.value || moduleList.value.length === 0) return

  currentStatus.value = 'uploading'
  statusMessage.value = '正在上传入箱顺序到MES...'
  emit('log', 'info', `[模组入箱] 开始上传入箱顺序`)

  const apiRec: any = {
    title: '入箱顺序上传',
    url: props.config.packingUploadUrl || '/mes-api/api/Packing/UploadPackingOrder',
    status: 'pending',
    time: new Date().toLocaleTimeString(),
    reqBody: {
      packCode: packInfo.value!.packCode,
      orderCode: packInfo.value!.orderCode,
      moduleCount: moduleList.value.length
    },
    resBody: null
  }
  emit('api-record', apiRec)

  try {
    const res = await uploadPackingOrder(props.config, {
      packCode: packInfo.value!.packCode,
      orderCode: packInfo.value!.orderCode,
      routeNo: packInfo.value!.routeNo,
      processCode: props.config.technicsProcessCode,
      moduleList: moduleList.value.map(m => ({
        moduleCode: m.moduleCode,
        scanOrder: m.scanOrder,
        scanTime: m.scanTime
      })),
      operator: operator.value,
      manualReviewPassed: true
    })

    apiRec.status = res.success ? 'success' : 'error'
    apiRec.resBody = res
    uploadResult.value = { success: res.success ?? false, message: res.message || '', recordId: res.recordId }

    // 保存历史记录
    const record: PackingRecord = {
      id: `pack_${Date.now()}`,
      packCode: packInfo.value!.packCode,
      orderCode: packInfo.value!.orderCode,
      routeNo: packInfo.value!.routeNo,
      processCode: props.config.technicsProcessCode,
      moduleCount: moduleList.value.length,
      moduleList: [...moduleList.value],
      operator: operator.value,
      manualReviewPassed: true,
      uploadStatus: res.success ? 'success' : 'fail',
      failReason: res.success ? undefined : res.message,
      createTime: new Date().toLocaleString(),
      uploadTime: res.success ? new Date().toLocaleString() : undefined,
      mesRecordId: res.recordId
    }
    historyRecords.value.unshift(record)

    if (res.success) {
      currentStatus.value = 'completed'
      statusMessage.value = `入箱顺序上传成功！MES记录ID: ${res.recordId || 'N/A'}`
      moduleList.value.forEach(m => m.isPacked = true)
      emit('log', 'success', `[模组入箱] 上传成功！记录ID: ${res.recordId || 'N/A'}`)
    } else {
      currentStatus.value = 'failed'
      statusMessage.value = `上传失败: ${res.message || '未知错误'}`
      emit('log', 'error', `[模组入箱] 上传失败: ${res.message}`)
      alert(`入箱顺序上传失败！\n${res.message}`)
    }
  } catch (err: any) {
    apiRec.status = 'error'
    apiRec.resBody = err.message
    currentStatus.value = 'failed'
    statusMessage.value = `上传异常: ${err.message}`
    emit('log', 'error', `[模组入箱] 上传异常: ${err.message}`)

    // 保存失败记录
    const record: PackingRecord = {
      id: `pack_${Date.now()}`,
      packCode: packInfo.value!.packCode,
      orderCode: packInfo.value!.orderCode,
      routeNo: packInfo.value!.routeNo,
      processCode: props.config.technicsProcessCode,
      moduleCount: moduleList.value.length,
      moduleList: [...moduleList.value],
      operator: operator.value,
      manualReviewPassed: true,
      uploadStatus: 'fail',
      failReason: err.message,
      createTime: new Date().toLocaleString()
    }
    historyRecords.value.unshift(record)
  }
}

// 5. 手动补传
async function handleRetryUpload(record: PackingRecord) {
  emit('log', 'info', `[模组入箱] 开始补传记录: ${record.packCode}`)

  const res = await retryUploadPacking(props.config, {
    packCode: record.packCode,
    orderCode: record.orderCode,
    routeNo: record.routeNo,
    processCode: record.processCode,
    moduleList: record.moduleList.map(m => ({
      moduleCode: m.moduleCode,
      scanOrder: m.scanOrder,
      scanTime: m.scanTime
    })),
    operator: operator.value,
    manualReviewPassed: record.manualReviewPassed
  })

  if (res.success) {
    record.uploadStatus = 'success'
    record.uploadTime = new Date().toLocaleString()
    record.mesRecordId = res.recordId
    emit('log', 'success', `[模组入箱] 补传成功！记录ID: ${res.recordId || 'N/A'}`)
    alert('补传成功！')
  } else {
    emit('log', 'error', `[模组入箱] 补传失败: ${res.message}`)
    alert(`补传失败！\n${res.message}`)
  }
}

focusPackInput()
</script>

<template>
  <div class="packing-root">
    <!-- 顶部状态栏 -->
    <div class="packing-header" :class="currentStatus">
      <div class="status-icon">
        {{ currentStatus === 'completed' ? '✅' : currentStatus === 'failed' ? '❌' : currentStatus === 'uploading' ? '⏳' : currentStatus === 'prechecking' ? '🔍' : currentStatus === 'reviewing' ? '👤' : currentStatus === 'ready' ? '📋' : '📦' }}
      </div>
      <div class="status-info">
        <div class="status-title">{{ 
          currentStatus === 'idle' ? '等待扫描PACK箱' :
          currentStatus === 'scanning_pack' ? '正在获取MES参数...' :
          currentStatus === 'ready' ? '已获取模组清单，请执行预校验' :
          currentStatus === 'prechecking' ? '正在预校验...' :
          currentStatus === 'reviewing' ? '等待人工复判' :
          currentStatus === 'uploading' ? '正在上传...' :
          currentStatus === 'completed' ? '入箱完成' :
          '入箱失败'
        }}</div>
        <div v-if="statusMessage" class="status-desc">{{ statusMessage }}</div>
      </div>
      <div v-if="packInfo" class="pack-stats">
        <span class="stat-item">
          <span class="stat-label">PACK</span>
          <span class="stat-value">{{ packInfo.packCode }}</span>
        </span>
        <span class="stat-item">
          <span class="stat-label">模组</span>
          <span class="stat-value">{{ moduleCount }}</span>
        </span>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="packing-body">
      <!-- 左侧面板 -->
      <div class="packing-left">
        <!-- PACK箱扫描 -->
        <div class="pack-card" :class="{ active: !isPackScanned, completed: isPackScanned }">
          <div class="pack-card-title">
            <span class="step-num">1</span>
            扫描PACK箱条码
          </div>
          <div class="pack-input-wrap" :class="{ scanning: currentStatus === 'scanning_pack' }">
            <input
              ref="packInputRef"
              v-model="packCode"
              type="text"
              placeholder="请扫描PACK箱条码..."
              class="pack-input"
              :disabled="isPackScanned || currentStatus === 'scanning_pack'"
              @keydown.enter="handlePackScan"
            />
            <button
              class="pack-action-btn"
              :disabled="!packCode.trim() || currentStatus === 'scanning_pack' || isPackScanned"
              @click="handlePackScan"
            >
              {{ currentStatus === 'scanning_pack' ? '获取中...' : '获取参数' }}
            </button>
          </div>
          <div v-if="packInfo" class="pack-detail">
            <div class="detail-row">
              <span class="detail-label">工单号</span>
              <span class="detail-value">{{ packInfo.orderCode }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">工艺路线</span>
              <span class="detail-value">{{ packInfo.routeNo }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">模组类型</span>
              <span class="detail-value highlight">{{ packInfo.moduleType }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">MES下发模组</span>
              <span class="detail-value">{{ moduleCount }} 个</span>
            </div>
          </div>
        </div>

        <!-- 操作按钮区 -->
        <div class="action-panel">
          <button
            class="btn-precheck"
            :disabled="!canPreCheck"
            @click="handlePreCheck"
          >
            <span>🔍</span> 入箱预校验
          </button>

          <template v-if="currentStatus === 'reviewing' || currentStatus === 'completed' || currentStatus === 'failed'">
            <div class="review-section" v-if="currentStatus === 'reviewing'">
              <div class="review-title">人工复判：是否允许入箱？</div>
              <div class="review-btns">
                <button class="btn-ok-review" @click="handleManualReview(true)">
                  <span>✅</span> 允许入箱
                </button>
                <button class="btn-ng-review" @click="handleManualReview(false)">
                  <span>❌</span> 拒绝入箱
                </button>
              </div>
            </div>
          </template>

          <button class="btn-reset" @click="resetAll">
            <span>🔄</span> 复位 / 下一箱
          </button>
        </div>
      </div>

      <!-- 右侧面板：模组清单（MES自动下发） -->
      <div class="packing-right">
        <div class="module-list-header">
          <span class="list-title">📋 MES自动下发模组清单</span>
          <span class="list-count">
            共 <strong>{{ moduleCount }}</strong> 个
            <span v-if="completedCount > 0"> | 已入箱 <strong class="success-text">{{ completedCount }}</strong> 个</span>
          </span>
        </div>

        <div class="module-list-body">
          <div v-if="moduleList.length === 0" class="module-empty">
            <div class="empty-icon">📦</div>
            <div class="empty-text">请扫描PACK箱条码<br/>MES将自动下发模组清单</div>
          </div>

          <div
            v-for="(module, index) in moduleList"
            :key="module.moduleCode + index"
            class="module-item"
            :class="{ 
              packed: module.isPacked,
              fail: module.logicCheckResult === 'fail' || module.mesCheckResult === 'fail'
            }"
          >
            <div class="module-order">{{ module.scanOrder }}</div>
            <div class="module-code">{{ module.moduleCode }}</div>
            <div class="module-status">
              <span v-if="module.isPacked" class="badge pass">已入箱</span>
              <span v-else-if="module.logicCheckResult === 'fail' || module.mesCheckResult === 'fail'" class="badge fail">校验失败</span>
              <span v-else-if="module.logicCheckResult === 'pass' && module.mesCheckResult === 'pass'" class="badge pass">校验通过</span>
              <span v-else class="badge pending">待校验</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：预校验结果 + 历史记录 -->
    <div v-if="preCheckResult" class="precheck-result">
      <div class="result-title">预校验结果</div>
      <div class="result-items">
        <div class="result-item" :class="preCheckResult.logicCheck.passed ? 'pass' : 'fail'">
          <span class="result-icon">{{ preCheckResult.logicCheck.passed ? '✅' : '❌' }}</span>
          <span class="result-label">产线逻辑校验</span>
          <span class="result-msg">{{ preCheckResult.logicCheck.message }}</span>
        </div>
        <div class="result-item" :class="preCheckResult.mesCheck.passed ? 'pass' : 'fail'">
          <span class="result-icon">{{ preCheckResult.mesCheck.passed ? '✅' : '❌' }}</span>
          <span class="result-label">MES投入校验</span>
          <span class="result-msg">{{ preCheckResult.mesCheck.message }}</span>
        </div>
      </div>
    </div>

    <!-- 补传补录面板 -->
    <div class="history-section">
      <div class="history-toggle" @click="showHistory = !showHistory">
        <span>{{ showHistory ? '▼' : '▶' }}</span>
        <span>入箱记录 / 补传补录</span>
        <span v-if="failedRecords.length > 0" class="history-badge">{{ failedRecords.length }} 条待补传</span>
      </div>

      <div v-show="showHistory" class="history-panel">
        <div v-if="historyRecords.length === 0" class="history-empty">暂无入箱记录</div>
        <div v-else class="history-list">
          <div
            v-for="record in historyRecords"
            :key="record.id"
            class="history-item"
            :class="record.uploadStatus"
          >
            <div class="history-main">
              <span class="history-pack">{{ record.packCode }}</span>
              <span class="history-count">{{ record.moduleCount }}个模组</span>
              <span class="history-time">{{ record.createTime }}</span>
              <span class="history-status">
                <span v-if="record.uploadStatus === 'success'" class="badge pass">上传成功</span>
                <span v-else class="badge fail">上传失败</span>
              </span>
            </div>
            <div class="history-detail">
              <span>工单: {{ record.orderCode }}</span>
              <span>操作员: {{ record.operator }}</span>
              <span v-if="record.mesRecordId">MES记录: {{ record.mesRecordId }}</span>
              <span v-if="record.failReason" class="fail-reason">原因: {{ record.failReason }}</span>
            </div>
            <div v-if="record.uploadStatus === 'fail'" class="history-actions">
              <button class="btn-retry" @click="handleRetryUpload(record)">
                <span>🔄</span> 补传
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.packing-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* 顶部状态栏 */
.packing-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #0d1b2a 0%, #112240 100%);
  border-bottom: 1px solid rgba(100, 181, 246, 0.15);
  flex-shrink: 0;
}

.packing-header.scanning_pack,
.packing-header.uploading,
.packing-header.prechecking {
  background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
}

.packing-header.completed {
  background: linear-gradient(135deg, #0d3328 0%, #1b5e20 100%);
  border-color: rgba(0, 230, 118, 0.2);
}

.packing-header.failed {
  background: linear-gradient(135deg, #3e0e0e 0%, #5c1212 100%);
  border-color: rgba(244, 67, 54, 0.2);
}

.packing-header.reviewing {
  background: linear-gradient(135deg, #3d2c00 0%, #5d4400 100%);
  border-color: rgba(255, 171, 64, 0.2);
}

.status-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.status-info {
  flex: 1;
}

.status-title {
  font-size: 14px;
  font-weight: 700;
  color: #e3f2fd;
}

.status-desc {
  font-size: 11px;
  color: #78909c;
  margin-top: 2px;
}

.pack-stats {
  display: flex;
  gap: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-label {
  font-size: 10px;
  color: #546e7a;
}

.stat-value {
  font-size: 13px;
  font-weight: 700;
  color: #42a5f5;
  font-family: 'Consolas', monospace;
}

/* 主内容区 */
.packing-body {
  display: flex;
  gap: 12px;
  padding: 12px;
  flex: 1;
  overflow: hidden;
}

.packing-left {
  width: 360px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
}

.packing-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #131929;
  border: 1px solid rgba(100, 181, 246, 0.12);
  border-radius: 10px;
  overflow: hidden;
}

/* 卡片 */
.pack-card {
  background: #131929;
  border: 1px solid rgba(100, 181, 246, 0.12);
  border-radius: 10px;
  padding: 14px;
  transition: all 0.2s;
}

.pack-card.active {
  border-color: rgba(100, 181, 246, 0.3);
  box-shadow: 0 0 16px rgba(66, 165, 245, 0.08);
}

.pack-card.completed {
  border-color: rgba(0, 230, 118, 0.2);
  background: rgba(0, 230, 118, 0.03);
}

.pack-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #90caf9;
  margin-bottom: 12px;
}

.step-num {
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, #1565c0, #0d47a1);
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: white;
  font-weight: 700;
}

.pack-input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #0d1117;
  border: 2px solid rgba(100, 181, 246, 0.2);
  border-radius: 8px;
  padding: 4px 6px 4px 12px;
  transition: border-color 0.2s;
}

.pack-input-wrap.scanning {
  border-color: #42a5f5;
  box-shadow: 0 0 0 3px rgba(66, 165, 245, 0.1);
}

.pack-input-wrap:focus-within {
  border-color: #42a5f5;
}

.pack-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: #e0e6ed;
  font-size: 14px;
  font-family: 'Consolas', monospace;
  padding: 8px 0;
}

.pack-input::placeholder {
  color: #37474f;
}

.pack-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pack-action-btn {
  background: linear-gradient(135deg, #1565c0, #0d47a1);
  border: none;
  border-radius: 6px;
  color: #e3f2fd;
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  flex-shrink: 0;
}

.pack-action-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #1976d2, #1565c0);
}

.pack-action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pack-detail {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 8px;
  background: rgba(21, 101, 192, 0.06);
  border-radius: 4px;
}

.detail-label {
  font-size: 11px;
  color: #546e7a;
}

.detail-value {
  font-size: 12px;
  color: #cfd8dc;
  font-family: 'Consolas', monospace;
}

.detail-value.highlight {
  color: #42a5f5;
  font-weight: 600;
}

/* 操作面板 */
.action-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.btn-precheck {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #1565c0, #0d47a1);
  border: none;
  border-radius: 8px;
  color: #e3f2fd;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-precheck:hover:not(:disabled) {
  background: linear-gradient(135deg, #1976d2, #1565c0);
  box-shadow: 0 4px 16px rgba(21, 101, 192, 0.4);
}

.btn-precheck:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.review-section {
  background: rgba(255, 171, 64, 0.05);
  border: 1px solid rgba(255, 171, 64, 0.15);
  border-radius: 8px;
  padding: 12px;
}

.review-title {
  font-size: 12px;
  font-weight: 600;
  color: #ffab40;
  text-align: center;
  margin-bottom: 10px;
}

.review-btns {
  display: flex;
  gap: 8px;
}

.btn-ok-review,
.btn-ng-review {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.btn-ok-review {
  background: linear-gradient(135deg, #00c853, #00897b);
  color: white;
}

.btn-ok-review:hover {
  box-shadow: 0 4px 16px rgba(0, 200, 83, 0.3);
}

.btn-ng-review {
  background: linear-gradient(135deg, #f44336, #c62828);
  color: white;
}

.btn-ng-review:hover {
  box-shadow: 0 4px 16px rgba(244, 67, 54, 0.3);
}

/* 模组列表 */
.module-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: linear-gradient(180deg, #0d1525 0%, #131929 100%);
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
  flex-shrink: 0;
}

.list-title {
  font-size: 13px;
  font-weight: 600;
  color: #90caf9;
}

.list-count {
  font-size: 11px;
  color: #546e7a;
}

.list-count strong {
  color: #42a5f5;
}

.success-text {
  color: #00e676 !important;
}

.module-list-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.module-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #37474f;
  gap: 8px;
}

.empty-icon {
  font-size: 32px;
  opacity: 0.5;
}

.empty-text {
  font-size: 12px;
  text-align: center;
}

.module-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: rgba(21, 101, 192, 0.04);
  border: 1px solid rgba(100, 181, 246, 0.08);
  border-radius: 6px;
  transition: all 0.2s;
}

.module-item:hover {
  background: rgba(21, 101, 192, 0.08);
}

.module-item.packed {
  background: rgba(0, 230, 118, 0.06);
  border-color: rgba(0, 230, 118, 0.15);
}

.module-item.fail {
  background: rgba(244, 67, 54, 0.06);
  border-color: rgba(244, 67, 54, 0.15);
}

.module-order {
  width: 24px;
  height: 24px;
  background: linear-gradient(135deg, #1565c0, #0d47a1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: white;
  font-weight: 700;
  flex-shrink: 0;
}

.module-code {
  flex: 1;
  font-family: 'Consolas', monospace;
  font-size: 13px;
  color: #e0e6ed;
}

.module-status {
  flex-shrink: 0;
}

/* Badge */
.badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  display: inline-block;
}

.badge.pass {
  background: rgba(0, 230, 118, 0.15);
  color: #00e676;
}

.badge.fail {
  background: rgba(244, 67, 54, 0.15);
  color: #f44336;
}

.badge.pending {
  background: rgba(255, 171, 64, 0.15);
  color: #ffab40;
}

/* 预校验结果 */
.precheck-result {
  padding: 10px 16px;
  background: rgba(13, 71, 161, 0.08);
  border-top: 1px solid rgba(100, 181, 246, 0.1);
  flex-shrink: 0;
}

.result-title {
  font-size: 12px;
  font-weight: 700;
  color: #90caf9;
  margin-bottom: 8px;
}

.result-items {
  display: flex;
  gap: 12px;
}

.result-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
}

.result-item.pass {
  background: rgba(0, 230, 118, 0.08);
  border: 1px solid rgba(0, 230, 118, 0.15);
}

.result-item.fail {
  background: rgba(244, 67, 54, 0.08);
  border: 1px solid rgba(244, 67, 54, 0.15);
}

.result-icon {
  font-size: 16px;
}

.result-label {
  font-weight: 600;
  color: #e0e6ed;
}

.result-msg {
  color: #78909c;
  font-size: 11px;
}

/* 历史记录 */
.history-section {
  flex-shrink: 0;
  border-top: 1px solid rgba(100, 181, 246, 0.1);
}

.history-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(13, 71, 161, 0.08);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: #90caf9;
  transition: background 0.2s;
}

.history-toggle:hover {
  background: rgba(13, 71, 161, 0.15);
}

.history-badge {
  background: rgba(244, 67, 54, 0.2);
  color: #ff5252;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  margin-left: auto;
}

.history-panel {
  max-height: 200px;
  overflow-y: auto;
  padding: 8px;
}

.history-empty {
  text-align: center;
  padding: 16px;
  color: #37474f;
  font-size: 12px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  padding: 8px 12px;
  background: rgba(21, 101, 192, 0.04);
  border: 1px solid rgba(100, 181, 246, 0.08);
  border-radius: 6px;
}

.history-item.success {
  border-color: rgba(0, 230, 118, 0.1);
}

.history-item.fail {
  border-color: rgba(244, 67, 54, 0.1);
}

.history-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.history-pack {
  font-family: 'Consolas', monospace;
  font-size: 12px;
  color: #42a5f5;
  font-weight: 600;
}

.history-count {
  font-size: 11px;
  color: #78909c;
}

.history-time {
  font-size: 11px;
  color: #546e7a;
}

.history-detail {
  margin-top: 4px;
  font-size: 11px;
  color: #546e7a;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.fail-reason {
  color: #ef9a9a;
}

.history-actions {
  margin-top: 6px;
}

.btn-retry {
  background: rgba(255, 171, 64, 0.1);
  border: 1px solid rgba(255, 171, 64, 0.2);
  border-radius: 4px;
  color: #ffab40;
  font-size: 11px;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-retry:hover {
  background: rgba(255, 171, 64, 0.2);
}

.btn-reset {
  width: 100%;
  padding: 9px;
  background: rgba(100, 181, 246, 0.08);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 6px;
  color: #90caf9;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.btn-reset:hover {
  background: rgba(100, 181, 246, 0.15);
  border-color: #42a5f5;
}

/* 滚动条 */
.module-list-body::-webkit-scrollbar,
.history-panel::-webkit-scrollbar,
.packing-left::-webkit-scrollbar {
  width: 4px;
}

.module-list-body::-webkit-scrollbar-thumb,
.history-panel::-webkit-scrollbar-thumb,
.packing-left::-webkit-scrollbar-thumb {
  background: rgba(100, 181, 246, 0.2);
  border-radius: 2px;
}
</style>
