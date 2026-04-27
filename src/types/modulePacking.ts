// 自动模组入箱（模组-PACK结合）类型定义

/** 模组入箱配置扩展 */
export interface ModulePackingConfig {
  /** MES参数下发接口 */
  paramDispatchUrl: string
  /** MES投入校验接口 */
  inputCheckUrl: string
  /** 入箱顺序上传接口 */
  packingUploadUrl: string
  /** 入箱数据查询接口 */
  packingQueryUrl: string
  /** 模组-PACK结合工序代码 */
  packingProcessCode: string
}

/** PACK箱信息 */
export interface PackBoxInfo {
  /** PACK箱条码 */
  packCode: string
  /** 工单号 */
  orderCode: string
  /** 工艺路线编码 */
  routeNo: string
  /** 模组类型 */
  moduleType: string
  /** 期望模组数量 */
  expectedModuleCount: number
  /** 已扫描模组数量 */
  scannedModuleCount: number
  /** MES下发的参数 */
  mesParams?: Record<string, unknown>
  /** 投入校验结果 */
  inputCheckResult?: InputCheckResult
}

/** 投入校验结果 */
export interface InputCheckResult {
  code: number | string
  message?: string
  success?: boolean
  /** 是否允许投入 */
  allowed: boolean
  /** 校验详情 */
  details?: string
}

/** 单个模组 */
export interface ModuleItem {
  /** 模组条码 */
  moduleCode: string
  /** 扫描顺序 */
  scanOrder: number
  /** 扫描时间 */
  scanTime: string
  /** 产线逻辑校验结果 */
  logicCheckResult: 'pending' | 'pass' | 'fail'
  /** MES投入校验结果 */
  mesCheckResult: 'pending' | 'pass' | 'fail'
  /** 校验失败原因 */
  failReason?: string
  /** 是否已入箱 */
  isPacked: boolean
}

/** 入箱预校验请求 */
export interface PreCheckRequest {
  packCode: string
  orderCode: string
  routeNo: string
  processCode: string
  moduleList: Array<{
    moduleCode: string
    scanOrder: number
  }>
}

/** 入箱预校验响应 */
export interface PreCheckResponse {
  code: number | string
  message?: string
  success?: boolean
  /** 产线逻辑校验结果 */
  logicCheck: {
    passed: boolean
    message: string
    details?: string[]
  }
  /** MES投入校验结果 */
  mesCheck: {
    passed: boolean
    message: string
    details?: string[]
  }
}

/** 入箱顺序上传请求 */
export interface PackingUploadRequest {
  packCode: string
  orderCode: string
  routeNo: string
  processCode: string
  moduleList: Array<{
    moduleCode: string
    scanOrder: number
    scanTime: string
  }>
  /** 操作员 */
  operator: string
  /** 是否人工复判通过 */
  manualReviewPassed: boolean
}

/** 入箱顺序上传响应 */
export interface PackingUploadResponse {
  code: number | string
  message?: string
  success?: boolean
  /** MES返回的入箱记录ID */
  recordId?: string
}

/** 入箱记录（用于补传补录） */
export interface PackingRecord {
  id: string
  packCode: string
  orderCode: string
  routeNo: string
  processCode: string
  moduleCount: number
  moduleList: ModuleItem[]
  operator: string
  manualReviewPassed: boolean
  /** 上传状态 */
  uploadStatus: 'pending' | 'success' | 'fail'
  /** 上传失败原因 */
  failReason?: string
  /** 创建时间 */
  createTime: string
  /** 上传时间 */
  uploadTime?: string
  /** MES记录ID */
  mesRecordId?: string
}

/** 模组入箱整体状态 */
export type PackingStatus = 'idle' | 'scanning_pack' | 'scanning_module' | 'precheck' | 'manual_review' | 'uploading' | 'completed' | 'failed'
