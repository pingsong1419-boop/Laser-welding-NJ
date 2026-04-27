<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import type { AppConfig, CompleteCheckInputRequest, OrderInfo, RouteStep, TestResult } from './types/mes'
import { getOrderByProcess, getRouteList, completeCheckInput, pushPackMessageToMes } from './services/mesApi'
import ConfigModal from './components/ConfigModal.vue'
import RouteTable from './components/RouteTable.vue'
import ApiDetail from './components/ApiDetail.vue'
import type { ApiRecord } from './components/ApiDetail.vue'
import MaterialScanner from './components/MaterialScanner.vue'
import ModulePacking from './components/ModulePacking.vue'
import LoginModal from './components/LoginModal.vue'
import type { User } from './types/mes'

const CONFIG_KEY = 'mes_app_config_v2'
const DEFAULT_CONFIG: AppConfig = {
  orderApiUrl: 'http://172.25.57.144:8076/api/OrderInfo/GetOtherOrderInfoByProcess',
  routeApiUrl: 'http://172.25.57.144:8076/api/OrderInfo/GetTechRouteListByCode',
  singleMaterialApiUrl: 'http://172.25.57.144:8076/api/ProduceMessage/MaterialCheckInput',
  moduleCodeApiUrl: 'http://172.25.57.144:8076/api/ProduceMessage/MaterialCheckInput',
  moduleBindPushUrl: 'http://172.25.57.144:8034/api/ProduceMessage/PushMessageToMes',
  packingUploadUrl: '/mes-api/api/Packing/UploadPackingOrder',
  moduleBindProcessCode: 'MODULE_BIND',
  packingProcessCode: 'PACK_MODULE'
}



function loadConfig(): AppConfig {
  try {
    const raw = localStorage.getItem(CONFIG_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      const merged = { ...DEFAULT_CONFIG, ...parsed } as AppConfig

      // 兼容历史配置：旧地址自动迁移为“首工序获取工单”
      if (merged.orderApiUrl === '/mes-api/api/OrderInfo/GetOtherOrderInfoByProcess') {
        merged.orderApiUrl = DEFAULT_CONFIG.orderApiUrl
      }
      return merged
    }
  } catch {}
  return { ...DEFAULT_CONFIG }
}

const config = reactive<AppConfig>(loadConfig())
const showConfig = ref(false)
const showLogin = ref(false)
const currentUser = ref<User | null>(null)
const onConfigSaved = () => localStorage.setItem(CONFIG_KEY, JSON.stringify(config))

const productCode = ref('')
const scanInputRef = ref<HTMLInputElement | null>(null)
const focusScan = () => nextTick(() => scanInputRef.value?.focus())
onMounted(focusScan)

const orderInfo = ref<OrderInfo | null>(null)
const orderLoading = ref(false)
const orderError = ref('')
const routeSteps = ref<RouteStep[]>([])
const routeLoading = ref(false)
const routeError = ref('')

const testResult = ref<TestResult>('IDLE')
const resultMessage = ref('')
const logs = ref<any[]>([])
const apiRecords = ref<ApiRecord[]>([])
const activeTab = ref<'route' | 'api' | 'log' | 'material' | 'packing'>('packing')
const materialVerificationLoading = ref(false)
const materialVerificationSuccess = ref(false)
const verifiedMaterials = ref<any[]>([])
const processStartTime = ref(new Date().toLocaleString())
const latestMesUploadSnapshot = ref<any | null>(null)

function addLog(level: any, msg: string) {
  logs.value.unshift({ time: new Date().toLocaleTimeString(), level, msg })
  if (logs.value.length > 50) logs.value.pop()
}

function safeStringify(data: unknown): string {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

function cloneForLog<T>(data: T): T | string {
  try {
    return JSON.parse(JSON.stringify(data)) as T
  } catch {
    return String(data)
  }
}

function resetAll() {
  orderError.value = ''; routeSteps.value = [];
  routeError.value = ''; testResult.value = 'IDLE'; resultMessage.value = '';
  apiRecords.value = [];
  materialVerificationSuccess.value = false;
  materialVerificationLoading.value = false;
  latestMesUploadSnapshot.value = null;
}

async function handleScan() {
  const code = productCode.value.trim()
  if (!code || !config.moduleBindProcessCode) return
  resetAll()
  addLog('info', `开始查询工单: ${code}`)
  orderLoading.value = true
  const t0 = Date.now()
  const rec = reactive<ApiRecord>({
    title: '获取工单(首工序)',
    url: config.orderApiUrl,
    status: 'pending',
    time: new Date().toLocaleTimeString(),
    reqBody: {
      produce_Type: 3,
      tenantID: 'FD'
    }
  })
  apiRecords.value.unshift(rec)
  activeTab.value = 'api'
  try {
    const res = await getOrderByProcess(config, code)
    rec.duration = Date.now() - t0
    rec.resBody = res
    if (res.datas?.[0]) {
      rec.status = 'success'
      orderInfo.value = res.datas[0]
      addLog('success', '工单获取成功')
      await fetchRouteList(res.datas[0].route_No)
    } else {
      rec.status = 'error'; addLog('error', '未找到工单')
    }
  } catch (err: any) {
    rec.status = 'error'; addLog('error', err.message)
  } finally { orderLoading.value = false }
}

async function fetchRouteList(routeCode: string) {
  routeLoading.value = true
  const t0 = Date.now()
  const rec = reactive<ApiRecord>({
    title: '获取工步',
    url: config.routeApiUrl,
    status: 'pending',
    time: new Date().toLocaleTimeString(),
    reqBody: {
      routeCode,
      workSeqNo: config.moduleBindProcessCode,
      workseqNo: config.moduleBindProcessCode
    }
  })
  apiRecords.value.unshift(rec)
  try {
    const res = await getRouteList(config, routeCode)
    rec.duration = Date.now() - t0
    rec.resBody = res
    const steps = (res.data as any)?.workSeqList || (Array.isArray(res.data) ? res.data : [])
    routeSteps.value = steps
    rec.status = 'success'; addLog('success', `获取到 ${steps.length} 条工步`)
    activeTab.value = 'material'
  } catch (err: any) {
    rec.status = 'error'; addLog('error', err.message)
  } finally { routeLoading.value = false }
}

function handleSingleMaterialScan(material: { productCode: string, productCount: number }) {
  const rec: ApiRecord = {
    title: '单物料验证',
    url: config.singleMaterialApiUrl || 'LOCAL_MATCH',
    status: 'success',
    time: new Date().toLocaleTimeString(),
    reqBody: material,
    resBody: { message: '匹配成功', code: 200 }
  }
  apiRecords.value.unshift(rec)
}

async function handleMaterialComplete(materials: { productCode: string, productCount: number }[]) {
  if (!orderInfo.value || materialVerificationLoading.value || materialVerificationSuccess.value) {
    console.warn('[调试] 验证已在进行中或已成功，跳过重复触发')
    return
  }
  
  materialVerificationLoading.value = true
  materialVerificationSuccess.value = false
  
  addLog('info', '正在提交全物料验证...')
  const t0 = Date.now()

  const reqData: CompleteCheckInputRequest = {
    produceOrderCode: String(orderInfo.value.orderCode || orderInfo.value.order_Code || ''),
    routeNo: String(orderInfo.value.route_No || orderInfo.value.routeNo || ''),
    technicsProcessCode: config.moduleBindProcessCode,
    tenantID: 'FD',
    productMixCode: String(orderInfo.value.productMixCode || orderInfo.value.product_MixCode || 'null'),
    productLine: "",
    materialList: materials
  }
  
  console.log('[调试] 全物料验证请求体:', JSON.stringify(reqData, null, 2))

  const rec = reactive<ApiRecord>({ title: '全物料验证', url: config.singleMaterialApiUrl, status: 'pending', time: new Date().toLocaleTimeString(), reqBody: reqData })
  apiRecords.value.unshift(rec)
  
  testResult.value = 'IDLE'
  resultMessage.value = '正在进行全物料后台验证...'
  
  try {
    addLog('info', `[流程] 正在向后台提交真实物料验证 (条码: ${productCode.value})`)


    addLog('info', `[调试] 进入真实 API 验证逻辑 (条码: ${productCode.value})`)
    const res = await completeCheckInput(config, reqData)
    rec.duration = Date.now() - t0
    rec.resBody = res
    
    addLog('info', `[调试] 收到验证回复: ${JSON.stringify(res)}`)
    
    if (res && (res.code === 200 || res.code === "200" || res.success === true || res.msg === '操作成功')) {
      rec.status = 'success'
      addLog('success', '✅ 全物料验证通过！')
      materialVerificationSuccess.value = true
      verifiedMaterials.value = materials // 保存已验证的物料清单
      testResult.value = 'IDLE'
      resultMessage.value = '物料验证通过，正在自动执行报工...'

      // 取消定扭环节：全物料通过后直接报工
      await submitAllDataToMes()
      await saveAllLogsToLocal()
    } else {
      rec.status = 'error'
      const msg = res?.message || res?.msg || '未知错误'
      addLog('error', `❌ 全物料验证失败: ${msg}`)
      testResult.value = 'NG'
      resultMessage.value = `全物料验证未通过: ${msg}`
      alert(`全物料验证失败！\n原因: ${msg}\n请处理后再继续。`)
    }
  } catch (err: any) {
    rec.status = 'error'
    testResult.value = 'NG'
    resultMessage.value = `请求异常: ${err.message}`
    addLog('error', `❌ 全物料验证请求异常: ${err.message}`)
    alert(`全物料验证接口请求失败，请检查网络或配置。\n${err.message}`)
  } finally {
    materialVerificationLoading.value = false
  }
}

async function submitAllDataToMes() {
  if (!orderInfo.value) return

  const t0 = Date.now()
  const nowStr = new Date().toLocaleDateString()
  const endTimeStr = new Date().toLocaleString()
  
  // 1. 构建物料绑定步 (STEP1)
  const step1Payload = {
    produceOrderCode: orderInfo.value.orderCode || orderInfo.value.order_Code || '',
    routeNo: orderInfo.value.route_No || orderInfo.value.routeNo || '',
    technicsProcessCode: config.moduleBindProcessCode,
    technicsProcessName: "",
    technicsStepCode: "STEP1",
    technicsStepName: "物料绑定",
    productCode: productCode.value,
    productCount: verifiedMaterials.value.length,
    productQuality: 0,
    produceDate: nowStr,
    startTime: processStartTime.value,
    endTime: endTimeStr,
    userName: currentUser.value?.username || "admin",
    userAccount: currentUser.value?.username || "admin",
    deviceCode: "",
    Remarks: "",
    ProduceInEntityList: verifiedMaterials.value.map(m => ({
      productCode: m.productCode,
      ProductCount: m.productCount
    })),
    produceParamEntityList: [],
    ngEntityList: [],
    cellParamEntityList: [],
    otherParamEntityList: [],
    deviceName: ""
  }

  // 无定扭工位：仅上报物料绑定步
  const finalPayload = [step1Payload]
  
  const rec = reactive<ApiRecord>({ 
    title: 'MES 报工上传', 
    url: config.moduleBindPushUrl, 
    status: 'pending', 
    time: new Date().toLocaleTimeString(), 
    reqBody: finalPayload 
  })
  apiRecords.value.unshift(rec)
  addLog('info', `[MES] 开始汇总报工数据 (共 ${finalPayload.length} 个工步)`)
  latestMesUploadSnapshot.value = {
    title: 'MES 报工上传',
    url: config.moduleBindPushUrl,
    status: 'pending',
    duration: 0,
    time: rec.time,
    reqBody: cloneForLog(finalPayload),
    resBody: null
  }

  try {
    const res = await pushPackMessageToMes(config, finalPayload)
    rec.duration = Date.now() - t0
    rec.resBody = res
    if (res && (res.code === 200 || res.success === true)) {
      rec.status = 'success'
      testResult.value = 'OK'
      addLog('success', '✅ MES 报工完成: 结果已成功推送到生产服务器')
      addLog('success', `[MES-上传成功] URL=${config.moduleBindPushUrl} code=${res?.code ?? 'N/A'}`)
      resultMessage.value = '报工已成功，当前流程已全部完成。'
      resultMessage.value = '报工已成功，当前流程已全部完成。'
    } else {
      rec.status = 'error'
      testResult.value = 'NG'
      const failMsg = res?.message || res?.msg || '服务器拒绝'
      addLog('error', `❌ MES 报工失败: ${failMsg}`)
      addLog('error', `[MES-上传失败] URL=${config.moduleBindPushUrl} msg=${failMsg}`)
      resultMessage.value = `报工失败: ${failMsg}`
    }
  } catch (err: any) {
    rec.status = 'error'
    testResult.value = 'NG'
    rec.resBody = err.message
    addLog('error', `❌ MES 报工网络异常: ${err.message}`)
    addLog('error', `[MES-上传异常] URL=${config.moduleBindPushUrl} err=${err.message}`)
    resultMessage.value = `网络异常，报工未完成: ${err.message}`
  } finally {
    latestMesUploadSnapshot.value = {
      title: 'MES 报工上传',
      url: config.moduleBindPushUrl,
      status: rec.status,
      duration: rec.duration,
      time: rec.time,
      reqBody: cloneForLog(finalPayload),
      resBody: cloneForLog(rec.resBody)
    }
  }
}


async function saveAllLogsToLocal() {
  addLog('info', `[System] 正在发起日志备份请求... (条码: ${productCode.value || '无条码'})`)

  const barcode = productCode.value.trim() || 'NoBarcode'

  const now = new Date()
  const timestamp = now.getFullYear().toString() + 
                    (now.getMonth() + 1).toString().padStart(2, '0') + 
                    now.getDate().toString().padStart(2, '0') + "_" +
                    now.getHours().toString().padStart(2, '0') + 
                    now.getMinutes().toString().padStart(2, '0') + 
                    now.getSeconds().toString().padStart(2, '0')
  
  const fileName = `${barcode}_${timestamp}.txt`
  
  // 组合日志内容
  let content = `================================================\n`
  content += `NJ_Torque_MES 生产执行记录\n`
  content += `产品条码: ${barcode}\n`
  content += `保存时间: ${now.toLocaleString()}\n`
  content += `================================================\n\n`
  
  content += `【操作日志】\n`
  logs.value.slice().reverse().forEach(l => {
    content += `[${l.time}] [${l.level.toUpperCase()}] ${l.msg}\n`
  })
  
  content += `\n【接口交互记录】\n`
  let hasMesUploadRecord = false
  apiRecords.value.slice().reverse().forEach(r => {
    if (r.title === 'MES 报工上传') hasMesUploadRecord = true
    content += `------------------------------------------------\n`
    content += `时间: ${r.time} | 状态: ${r.status.toUpperCase()} | 耗时: ${r.duration || 0}ms\n`
    content += `标题: ${r.title}\n`
    content += `请求: ${safeStringify(r.reqBody)}\n`
    content += `响应: ${safeStringify(r.resBody)}\n`
  })

  // 双保险：若接口列表里未包含 MES 报工记录，则写入快照
  if (!hasMesUploadRecord && latestMesUploadSnapshot.value) {
    const r = latestMesUploadSnapshot.value
    content += `------------------------------------------------\n`
    content += `时间: ${r.time} | 状态: ${String(r.status || '').toUpperCase()} | 耗时: ${r.duration || 0}ms\n`
    content += `标题: ${r.title || 'MES 报工上传'}\n`
    content += `URL: ${r.url || config.moduleBindPushUrl}\n`
    content += `请求: ${safeStringify(r.reqBody)}\n`
    content += `响应: ${safeStringify(r.resBody)}\n`
    content += `[补录说明] 本条为 MES 报工上传快照补录。\n`
  }

  // 固定章节：MES 报工结果摘要（独立于接口交互列表）
  content += `\n【MES报工结果】\n`
  if (latestMesUploadSnapshot.value) {
    const m = latestMesUploadSnapshot.value
    content += `时间: ${m.time}\n`
    content += `状态: ${String(m.status || '').toUpperCase()}\n`
    content += `URL: ${m.url || config.moduleBindPushUrl}\n`
    content += `请求: ${safeStringify(m.reqBody)}\n`
    content += `响应: ${safeStringify(m.resBody)}\n`
  } else {
    content += `本次流程未执行 MES 报工上传。\n`
  }
  
  try {
    const response = await fetch('http://127.0.0.1:5246/saveLogs', {


      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        FileName: fileName,
        Content: content,
        Path: 'C:\\NJ_Torque_Logs'
      })
    })
    
    if (response.ok) {
       const text = await response.text();
       try {
         const resData = JSON.parse(text);
         addLog('success', `[System] 日志已自动备份至本地: ${resData.path}`)
       } catch {
         addLog('success', '[System] 日志备份请求已发送，但后台未返回确认信息')
       }
    } else {
       const text = await response.text();
       addLog('error', `[System] 后台保存失败 (HTTP ${response.status}): ${text.substring(0, 100)}`)
    }
  } catch (err) {
    addLog('error', `[System] 通讯异常: ${err}`)
  }

}





async function resetResult() {
  // 核心判定：只要输入了条码，且没有达到最终的“全部完成”状态，就需要管理员授权
  const isFinished = testResult.value === 'OK' && resultMessage.value.includes('已完成')
  const hasStarted = productCode.value.trim() !== ''

  if (hasStarted && !isFinished) {
     showLogin.value = true
     return
  }
  await executeReset()
}


async function handleAuthSuccess(user: User) {
  currentUser.value = user
  addLog('warn', `管理员 [${user.username}] 授权：执行强制复位`)
  await executeReset()
  currentUser.value = null // 授权完重置身份
}

async function executeReset() {
  // 1. 尝试保存日志（不阻塞 UI 复位）
  if (productCode.value) {
    addLog('info', '正在后台备份当前流程日志...')
    saveAllLogsToLocal().catch(err => {
      console.error('备份失败:', err)
      addLog('error', '[System] 自动备份过程发生错误')
    })
  }

  // 2. 彻底清理前端状态，回到初始状态
  productCode.value = ''
  orderInfo.value = null
  routeSteps.value = []
  materialVerificationSuccess.value = false
  testResult.value = 'IDLE'
  resultMessage.value = ''
  latestMesUploadSnapshot.value = null
  activeTab.value = 'route' // 回到第一步标签页

  addLog('info', '----------------------------------------')
  addLog('info', '✅ 系统已全面复位，请开始新任务')
  
  // 重新聚焦扫码框
  focusScan()
}



</script>

<template>
  <div class="app-root">
    <header class="app-header">
      <div class="header-left">
        <div class="brand-icon">MES</div>
        <div class="brand-text">
          <span class="brand-title">模组入箱系统</span>
          <span class="brand-sub">MES Module Packing System v1.0</span>
        </div>
      </div>
      <div class="header-center">
        <span class="process-badge">
          <span class="label">当前工序：</span>
          <span class="value">{{ config.moduleBindProcessCode || '未设置' }}</span>
        </span>
      </div>
      <div class="header-right">
        <button class="icon-btn" title="系统配置" @click="showConfig = true">
          ⚙️ 配置
        </button>
      </div>
    </header>

    <main class="app-main">
      <section class="left-panel">

        <div class="card scan-card">
          <div class="card-title">
            <span class="step-badge">1</span>
            扫描条码
          </div>
          <div class="scan-input-wrap" :class="{ 'scanning': orderLoading }">
            <span class="scan-icon">📷</span>
            <input
              ref="scanInputRef"
              v-model="productCode"
              type="text"
              placeholder="请扫描或输入产品条码..."
              class="scan-input"
              :disabled="orderLoading || routeLoading"
              @keydown.enter="handleScan"
            />
            <button
              class="scan-btn"
              :disabled="orderLoading || !productCode.trim()"
              @click="handleScan"
            >
              {{ orderLoading ? '查询中...' : '查询' }}
            </button>
          </div>
          <p class="scan-hint">扫描后请按 <kbd>Enter</kbd> 提交</p>
        </div>

        <div class="card info-card">
          <div class="card-title">
            <span class="step-badge">2</span>
            工单信息
            <div v-if="orderLoading" class="loading-spin" />
          </div>

          <div v-if="orderError" class="error-box">
            <span>⚠️</span> {{ orderError }}
          </div>

          <div v-else-if="orderInfo" class="info-grid">
            <div class="info-item">
              <span class="info-label">工单号</span>
              <span class="info-value highlight">{{ orderInfo.orderCode }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">工艺路线编码 (route_No)</span>
              <span class="info-value mono">{{ orderInfo.route_No }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">产品条码</span>
              <span class="info-value mono">{{ productCode }}</span>
            </div>
            <template v-for="(val, key) in orderInfo" :key="key">
              <div
                v-if="key !== 'orderCode' && key !== 'route_No'"
                class="info-item"
              >
                <span class="info-label">{{ key }}</span>
                <span class="info-value">{{ val }}</span>
              </div>
            </template>
          </div>

          <div v-else class="empty-hint">等待查询...</div>
        </div>

        <div class="card result-card">
          <div class="card-title">
            <span class="step-badge">3</span>
            总体流程状态
          </div>

          <div class="result-display" :class="testResult.toLowerCase()">
            <span class="result-icon">
              {{ testResult === 'OK' ? '✅' : testResult === 'NG' ? '❌' : '⏳' }}
            </span>
            <span class="result-text">
              {{ testResult === 'IDLE' ? '待执行' : testResult }}
            </span>
            <span v-if="resultMessage" class="result-msg">{{ resultMessage }}</span>
          </div>

          <button
            v-if="productCode.trim() !== ''"
            class="btn-reset"
            @click="resetResult"
          >
            🔄 复位状态 / 准备下一件
          </button>


        </div>
      </section>

      <section class="right-panel">
        <!-- 标签栏 -->
        <div class="tab-bar">
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'route' }"
            @click="activeTab = 'route'"
          >
            <span>📋</span> 工步列表
            <span v-if="routeSteps.length" class="tab-count">{{ routeSteps.length }}</span>
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'material' }"
            @click="activeTab = 'material'"
          >
            <span>📦</span> 物料验证
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'api' }"
            @click="activeTab = 'api'"
          >
            <span>🔌</span> 接口交互
            <span v-if="apiRecords.length" class="tab-count">{{ apiRecords.length }}</span>
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'log' }"
            @click="activeTab = 'log'"
          >
            <span>📄</span> 操作日志
            <span v-if="logs.length" class="tab-count">{{ logs.length }}</span>
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'packing' }"
            @click="activeTab = 'packing'"
          >
            <span>📦</span> 模组入箱
          </button>
        </div>

        <!-- 标签内容区 -->
        <div class="tab-content">
          <!-- 工步列表 -->
          <div v-show="activeTab === 'route'" class="tab-pane">
            <div v-if="routeError" class="error-box">
              <span>⚠️</span> {{ routeError }}
            </div>
            <RouteTable :steps="routeSteps" :loading="routeLoading" />
          </div>

          <!-- 物料验证 -->
          <div v-show="activeTab === 'material'" class="tab-pane flex-column">
            <div v-if="materialVerificationLoading" class="status-banner loading-mini">
              <span class="spinner-icon">⏳</span>
              <span>正在向后台提交全物料验证，请稍候...</span>
            </div>
            <div v-if="materialVerificationSuccess && activeTab === 'material'" class="status-banner success-mini">
              <span class="pulse-icon">✅</span>
              <span>全物料后台验证已通过，正在自动报工...</span>
            </div>
            <div v-if="testResult === 'NG' && activeTab === 'material'" class="status-banner fail-mini">
              <span class="pulse-icon">❌</span>
              <span>物料验证异常: {{ resultMessage }}</span>
            </div>
            <MaterialScanner 
              :steps="routeSteps" 
              @log="addLog"
              @single-complete="handleSingleMaterialScan"
              @complete="handleMaterialComplete"
            />
          </div>

          <!-- 接口交互详情 -->
          <div v-show="activeTab === 'api'" class="tab-pane">
            <ApiDetail :records="apiRecords" />
          </div>

          <!-- 操作日志 -->
          <div v-show="activeTab === 'log'" class="tab-pane log-pane">
            <div class="log-scroll">
              <div
                v-for="(entry, i) in logs"
                :key="i"
                class="log-entry"
                :class="entry.level"
              >
                <span class="log-time">{{ entry.time }}</span>
                <span class="log-msg">{{ entry.msg }}</span>
              </div>
              <div v-if="!logs.length" class="log-empty">暂无日志</div>
            </div>
          </div>

          <!-- 模组入箱 -->
          <div v-show="activeTab === 'packing'" class="tab-pane">
            <ModulePacking
              :config="config"
              @log="addLog"
              @api-record="(rec: any) => apiRecords.unshift(rec)"
            />
          </div>
        </div>
      </section>
    </main>

    <!-- 配置弹窗 -->
    <ConfigModal
      v-model="config"
      v-model:visible="showConfig"
      @save="onConfigSaved"
    />

    <LoginModal
      v-model:visible="showLogin"
      :admin-user="'admin'"
      :admin-pass="'123'"
      @auth-success="handleAuthSuccess"
    />

  </div>
</template>


<style scoped>
/* 鏍瑰鍣?*/
.app-root {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  background: #0a0e1a;
  color: #c8d6e5;
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
  overflow: hidden;
}

/* 椤堕儴鏍囬鏍?*/
.app-header {
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 52px;
  background: linear-gradient(135deg, #0d1b2a 0%, #112240 100%);
  border-bottom: 1px solid rgba(100, 181, 246, 0.2);
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.4);
  flex-shrink: 0;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 34px;
  height: 34px;
  background: linear-gradient(135deg, #1565c0, #0d47a1);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  color: #e3f2fd;
  letter-spacing: -0.5px;
  box-shadow: 0 0 12px rgba(21, 101, 192, 0.5);
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-title {
  font-size: 15px;
  font-weight: 700;
  color: #e3f2fd;
  line-height: 1.2;
}

.brand-sub {
  font-size: 10px;
  color: #546e7a;
  letter-spacing: 0.5px;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.process-badge {
  background: rgba(21, 101, 192, 0.2);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 20px;
  padding: 4px 16px;
  font-size: 12px;
  display: flex;
  gap: 6px;
}

.process-badge .label {
  color: #78909c;
}

.process-badge .value {
  color: #42a5f5;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 8px;
}

.icon-btn {
  background: rgba(21, 101, 192, 0.2);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 6px;
  color: #90caf9;
  padding: 5px 14px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: rgba(21, 101, 192, 0.4);
  border-color: #42a5f5;
  color: #e3f2fd;
}

/* 主体 */
.app-main {
  display: flex;
  gap: 12px;
  padding: 12px;
  flex: 1;
  overflow: hidden;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 360px;
  flex-shrink: 0;
  overflow-y: auto;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  background: #131929;
  border: 1px solid rgba(100, 181, 246, 0.12);
  border-radius: 10px;
}

/* 鏍囩鏍?*/
.tab-bar {
  display: flex;
  gap: 2px;
  padding: 8px 10px 0;
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
  background: linear-gradient(180deg, #0d1525 0%, #131929 100%);
  flex-shrink: 0;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  background: transparent;
  border: 1px solid transparent;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  color: #546e7a;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  bottom: -1px;
}

.tab-btn:hover {
  color: #90caf9;
  background: rgba(100, 181, 246, 0.05);
}
.tab-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  filter: grayscale(0.8);
}
.tab-btn.disabled:hover {
  background: transparent;
  color: inherit;
}


.tab-btn.active {
  color: #42a5f5;
  background: #131929;
  border-color: rgba(100, 181, 246, 0.15);
  font-weight: 600;
}

.tab-count {
  background: rgba(66, 165, 245, 0.2);
  color: #42a5f5;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 600;
}

.tab-btn.active .tab-count {
  background: rgba(66, 165, 245, 0.3);
}

/* 鏍囩鍐呭鍖?*/
.tab-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.tab-pane {
  position: absolute;
  inset: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.log-pane {
  padding: 10px;
}

/* 閫氱敤鍗＄墖 */
.card {
  background: #131929;
  border: 1px solid rgba(100, 181, 246, 0.12);
  border-radius: 10px;
  padding: 14px;
  flex-shrink: 0;
}

.route-card,
.log-card {
  flex-shrink: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.route-card {
  flex: 3;
}

.log-card {
  flex: 2;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #90caf9;
  margin-bottom: 12px;
  letter-spacing: 0.5px;
}

.step-badge {
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
  flex-shrink: 0;
}

.lv-badge {
  margin-left: auto;
  background: rgba(38, 198, 218, 0.1);
  color: #26c6da;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
}

/* 扫码输入 */
.scan-input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #0d1117;
  border: 2px solid rgba(100, 181, 246, 0.2);
  border-radius: 8px;
  padding: 4px 6px 4px 12px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.scan-input-wrap.scanning {
  border-color: #42a5f5;
  box-shadow: 0 0 0 3px rgba(66, 165, 245, 0.1), 0 0 20px rgba(66, 165, 245, 0.2);
}

.scan-input-wrap:focus-within {
  border-color: #42a5f5;
  box-shadow: 0 0 0 3px rgba(66, 165, 245, 0.1);
}

.scan-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.scan-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: #e0e6ed;
  font-size: 14px;
  font-family: 'Consolas', monospace;
  padding: 8px 0;
  min-width: 0;
}

.scan-input::placeholder {
  color: #37474f;
}

.scan-btn {
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

.scan-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #1976d2, #1565c0);
  box-shadow: 0 4px 12px rgba(21, 101, 192, 0.4);
}

.scan-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.scan-hint {
  font-size: 11px;
  color: #37474f;
  margin: 6px 0 0 0;
}

kbd {
  background: rgba(100, 181, 246, 0.1);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 3px;
  padding: 1px 5px;
  font-size: 10px;
  color: #64b5f6;
}

/* 宸ュ崟淇℃伅 */
.info-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 7px 10px;
  background: rgba(21, 101, 192, 0.06);
  border-radius: 6px;
  border: 1px solid rgba(100, 181, 246, 0.08);
  gap: 8px;
}

.info-label {
  font-size: 11px;
  color: #546e7a;
  flex-shrink: 0;
}

.info-value {
  font-size: 12px;
  color: #cfd8dc;
  text-align: right;
  word-break: break-all;
}

.info-value.highlight {
  color: #42a5f5;
  font-weight: 700;
  font-size: 13px;
}

.info-value.mono {
  font-family: 'Consolas', monospace;
}

.empty-hint {
  text-align: center;
  color: #37474f;
  font-size: 12px;
  padding: 16px 0;
}

/* OK/NG 结果 */
.result-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  background: rgba(21, 101, 192, 0.05);
  border: 1px solid rgba(100, 181, 246, 0.1);
  transition: all 0.3s;
}

.result-display.ok {
  background: rgba(0, 230, 118, 0.08);
  border-color: rgba(0, 230, 118, 0.3);
  box-shadow: 0 0 24px rgba(0, 230, 118, 0.15);
}

.result-display.ng {
  background: rgba(255, 82, 82, 0.08);
  border-color: rgba(255, 82, 82, 0.3);
  box-shadow: 0 0 24px rgba(255, 82, 82, 0.15);
}

.result-icon {
  font-size: 28px;
}

.result-text {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #e0e6ed;
}

.result-display.ok .result-text {
  color: #00e676;
}

.result-display.ng .result-text {
  color: #ff5252;
}

.result-msg {
  font-size: 12px;
  color: #78909c;
}

.result-actions {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.btn-ok,
.btn-ng {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.5px;
}

.btn-ok {
  background: linear-gradient(135deg, #00c853, #00897b);
  color: white;
  box-shadow: 0 4px 16px rgba(0, 200, 83, 0.2);
}

.btn-ok:hover:not(:disabled) {
  box-shadow: 0 6px 24px rgba(0, 200, 83, 0.4);
  transform: translateY(-1px);
}

.btn-ng {
  background: linear-gradient(135deg, #f44336, #c62828);
  color: white;
  box-shadow: 0 4px 16px rgba(244, 67, 54, 0.2);
}

.btn-ng:hover:not(:disabled) {
  box-shadow: 0 6px 24px rgba(244, 67, 54, 0.4);
  transform: translateY(-1px);
}

.btn-ok:disabled,
.btn-ng:disabled {
  opacity: 0.3;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
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
}

.btn-reset:hover {
  background: rgba(100, 181, 246, 0.15);
  border-color: #42a5f5;
}

/* 閿欒妗?*/
.error-box {
  background: rgba(244, 67, 54, 0.08);
  border: 1px solid rgba(244, 67, 54, 0.25);
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 12px;
  color: #ef9a9a;
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-bottom: 8px;
}

/* 鍔犺浇鍔ㄧ敾 */
.loading-spin {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(66, 165, 245, 0.2);
  border-top-color: #42a5f5;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-left: auto;
}

/* 鏃ュ織 */
.log-scroll {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-right: 4px;
}

.log-scroll::-webkit-scrollbar {
  width: 4px;
}

.log-scroll::-webkit-scrollbar-thumb {
  background: rgba(100, 181, 246, 0.2);
  border-radius: 2px;
}

.log-entry {
  display: flex;
  gap: 10px;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.02);
}

.log-entry.success { color: #69f0ae; }
.log-entry.error { color: #ff5252; }
.log-entry.warn { color: #ffab40; }
.log-entry.info { color: #78909c; }

.log-time {
  color: #455a64;
  flex-shrink: 0;
  width: 70px;
}

.log-msg {
  word-break: break-all;
  line-height: 1.5;
}

.log-empty {
  text-align: center;
  color: #37474f;
  font-size: 12px;
  padding: 16px;
}

.status-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-weight: 600;
  font-size: 14px;
  animation: slideDown 0.3s ease-out;
}
.success-mini {
  background: rgba(0, 230, 118, 0.1);
  border: 1px solid rgba(0, 230, 118, 0.2);
  color: #00e676;
}
.fail-mini {
  background: rgba(244, 67, 54, 0.1);
  border: 1px solid rgba(244, 67, 54, 0.2);
  color: #f44336;
}
.loading-mini {
  background: rgba(255, 152, 0, 0.1);
  border: 1px solid rgba(255, 152, 0, 0.2);
  color: #ff9800;
}
.pulse-icon {
  font-size: 18px;
  animation: pulse 2s infinite;
}
.spinner-icon {
  font-size: 18px;
  display: inline-block;
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}


@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.8; }
  100% { transform: scale(1); opacity: 1; }
}


/* 定扭判定矩阵 (瀵归綈物料验证 UI) */
.tightening-matrix-card-modern {
  margin-top: 24px;
  border-top: 1px solid rgba(100, 181, 246, 0.1);
}

.matrix-header-modern {
  padding: 12px 14px;
  background: rgba(13, 71, 161, 0.15);
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.matrix-title {
  color: #e3f2fd;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.matrix-table-modern {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.matrix-table-modern th {
  background: rgba(21, 101, 192, 0.2);
  color: #78909c;
  text-align: left;
  padding: 8px 12px;
  font-weight: 600;
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
}

.matrix-table-modern td {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.05);
  color: #cfd8dc;
}

.badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  display: inline-block;
}

.badge.pass { background: rgba(0, 230, 118, 0.15); color: #00e676; }
.badge.fail { background: rgba(244, 67, 54, 0.15); color: #f44336; }
.badge.pending { background: rgba(255, 171, 64, 0.15); color: #ffab40; }

.matrix-mono { font-family: 'Consolas', monospace; color: #64b5f6; }

.btn-reset-light {
  background: #1976d2;
  color: white;
  border: none;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.retry-col {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}
.retry-count {
  background: rgba(255, 171, 64, 0.1);
  color: #ffab40;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: bold;
}
.retry-zero { color: #546e7a; font-size: 10px; }
.history-preview {
  font-size: 12px;
  cursor: help;
  opacity: 0.8;
}
.history-preview:hover { opacity: 1; }


/* 定扭判定矩阵 (对齐物料验证 UI) */
.tightening-matrix-card-modern {
  margin-top: 24px;
  border-top: 1px solid rgba(100, 181, 246, 0.1);
  display: flex;
  flex-direction: column;
}

.matrix-header-modern {
  padding: 12px 14px;
  background: rgba(13, 71, 161, 0.15);
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.matrix-title {
  color: #e3f2fd;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.matrix-table-wrap {
  flex: 1;
  max-height: 500px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(100, 181, 246, 0.2) transparent;
}

.matrix-table-modern {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.matrix-table-modern th {
  background: #0d1117;
  color: #78909c;
  text-align: left;
  padding: 8px 12px;
  font-weight: 600;
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
  position: sticky;
  top: 0;
  z-index: 10;
}

.matrix-table-modern td {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.05);
  color: #cfd8dc;
}

.badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  display: inline-block;
}

.badge.pass { background: rgba(0, 230, 118, 0.15); color: #00e676; }
.badge.fail { background: rgba(244, 67, 54, 0.15); color: #f44336; }
.badge.pending { background: rgba(255, 171, 64, 0.15); color: #ffab40; }

.matrix-mono { font-family: 'Consolas', monospace; color: #64b5f6; }
</style>
