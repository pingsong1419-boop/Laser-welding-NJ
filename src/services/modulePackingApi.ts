// 自动模组入箱（模组-PACK结合）API 服务

import type {
  InputCheckResult,
  PreCheckRequest,
  PreCheckResponse,
  PackingUploadRequest,
  PackingUploadResponse
} from '../types/modulePacking'
import type { AppConfig } from '../types/mes'

/**
 * 通用POST请求
 */
async function postRequest<T>(url: string, body: object): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json'
    },
    body: JSON.stringify(body)
  })

  if (!response.ok) {
    throw new Error(`HTTP错误: ${response.status} ${response.statusText}`)
  }

  const data = await response.json()
  return data as T
}

/**
 * 1. MES参数下发 + 投入校验
 * 扫描PACK箱后，向MES请求该PACK箱的参数并校验是否可投入
 */
export async function dispatchParamsAndCheckInput(
  config: AppConfig,
  packCode: string
): Promise<InputCheckResult> {
  // 使用配置中的参数下发接口，如果没有则使用默认路径
  const url = (config as any).paramDispatchUrl || '/mes-api/api/Packing/DispatchParams'
  
  const params = {
    packCode,
    tenantID: 'FD',
    processCode: config.technicsProcessCode
  }

  try {
    const res = await postRequest<any>(url, params)
    return {
      code: res.code ?? 200,
      message: res.message || res.msg,
      success: res.code === 200 || res.code === '200' || res.success === true,
      allowed: res.code === 200 || res.code === '200' || res.success === true || res.allowed === true,
      details: res.data || res.details
    }
  } catch (err: any) {
    return {
      code: 500,
      message: `请求异常: ${err.message}`,
      success: false,
      allowed: false,
      details: err.message
    }
  }
}

/**
 * 2. 入箱预校验
 * 对整包模组进行预校验（产线逻辑校验 + MES投入校验）
 */
export async function preCheckModules(
  config: AppConfig,
  data: PreCheckRequest
): Promise<PreCheckResponse> {
  const url = (config as any).inputCheckUrl || '/mes-api/api/Packing/PreCheckInput'

  try {
    const res = await postRequest<any>(url, {
      ...data,
      tenantID: 'FD'
    })

    const logicPassed = res.data?.logicCheck?.passed ?? res.logicCheck?.passed ?? (res.code === 200)
    const mesPassed = res.data?.mesCheck?.passed ?? res.mesCheck?.passed ?? (res.code === 200)

    return {
      code: res.code ?? 200,
      message: res.message || res.msg,
      success: res.code === 200 || res.code === '200' || res.success === true,
      logicCheck: {
        passed: logicPassed,
        message: res.data?.logicCheck?.message || res.logicCheck?.message || (logicPassed ? '产线逻辑校验通过' : '产线逻辑校验失败'),
        details: res.data?.logicCheck?.details || res.logicCheck?.details
      },
      mesCheck: {
        passed: mesPassed,
        message: res.data?.mesCheck?.message || res.mesCheck?.message || (mesPassed ? 'MES投入校验通过' : 'MES投入校验失败'),
        details: res.data?.mesCheck?.details || res.mesCheck?.details
      }
    }
  } catch (err: any) {
    return {
      code: 500,
      message: `请求异常: ${err.message}`,
      success: false,
      logicCheck: { passed: false, message: `产线逻辑校验异常: ${err.message}` },
      mesCheck: { passed: false, message: `MES投入校验异常: ${err.message}` }
    }
  }
}

/**
 * 3. 上传模组/模块入箱顺序
 * 调用入箱顺序上传接口
 */
export async function uploadPackingOrder(
  config: AppConfig,
  data: PackingUploadRequest
): Promise<PackingUploadResponse> {
  const url = (config as any).packingUploadUrl || '/mes-api/api/Packing/UploadPackingOrder'

  try {
    const res = await postRequest<any>(url, {
      ...data,
      tenantID: 'FD'
    })

    return {
      code: res.code ?? 200,
      message: res.message || res.msg,
      success: res.code === 200 || res.code === '200' || res.success === true,
      recordId: res.data?.recordId || res.recordId
    }
  } catch (err: any) {
    return {
      code: 500,
      message: `请求异常: ${err.message}`,
      success: false
    }
  }
}

/**
 * 4. 查询入箱记录（用于补录）
 */
export async function queryPackingRecords(
  config: AppConfig,
  params: {
    packCode?: string
    orderCode?: string
    startDate?: string
    endDate?: string
  }
): Promise<any[]> {
  const url = (config as any).packingQueryUrl || '/mes-api/api/Packing/QueryRecords'

  try {
    const res = await postRequest<any>(url, {
      ...params,
      tenantID: 'FD',
      processCode: config.technicsProcessCode
    })
    return Array.isArray(res.data) ? res.data : []
  } catch {
    return []
  }
}

/**
 * 5. 手动补传入箱数据
 */
export async function retryUploadPacking(
  config: AppConfig,
  data: PackingUploadRequest
): Promise<PackingUploadResponse> {
  // 复用上传接口，但增加 retry 标记
  return uploadPackingOrder(config, {
    ...data,
    operator: `${data.operator}(补传)`
  })
}
