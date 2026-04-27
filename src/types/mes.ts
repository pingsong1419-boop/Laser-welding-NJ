// MES系统接口类型定义

/** 应用配置 */
export interface AppConfig {
  /** 非首工序获取工单 API 地址 */
  orderApiUrl: string
  /** 工步下发 API 地址 */
  routeApiUrl: string
  /** 单物料校验 API 地址 */
  singleMaterialApiUrl: string
  /** 获取模块码 API 地址 */
  moduleCodeApiUrl?: string
  /** 模块绑定数据上传 API 地址 */
  moduleBindPushUrl?: string
  /** 模组入箱数据上传 API 地址 */
  packingUploadUrl?: string
  /** 模块绑定模组编码 */
  moduleBindProcessCode?: string
  /** 模组入箱编码 */
  packingProcessCode?: string
}

/** 获取工单请求参数 */
export interface GetOrderRequest {
  produce_Type: number
  tenantID: string
}

/**
 * 工单信息（接口一 datas[] 中的单条数据）
 * route_No：工艺路线编码，传给接口二的 routeCode
 */
export interface OrderInfo {
  orderCode: string

  route_No: string       // 注意：实际字段名带下划线
  specsCode?: string
  cell_Level?: string | null
  cell_Batch?: string | null
  productMixCode?: string | null
  projectCode?: string
  productline_no?: string
  polarity?: number
  relateOrderNo?: string
  moduleSort?: string
  orderType?: number
  [key: string]: unknown
}

/**
 * 获取工单响应
 * 实际结构：{ code, message, datas: OrderInfo[] }
 */
export interface GetOrderResponse {
  code: number | string
  message?: string
  msg?: string
  /** 实际返回的是 datas 数组 */
  datas?: OrderInfo[]
  /** 兼容 data 字段 */
  data?: OrderInfo | OrderInfo[] | null
  success?: boolean
}

/** 获取工步列表请求 */
export interface GetRouteRequest {
  routeCode: string   // 来自接口一的 route_No
  workSeqNo?: string  // 工序代码（兼容字段）
  workseqNo: string   // 工序代码（接口要求字段）
}

/** 工步信息（接口二 workSeqList[] 中的数据，字段全小写） */
export interface RouteStep {
  workseqNo?: string      // 工步编码
  workseqName?: string    // 工步名称
  sortCode?: number       // 排序
  routeId?: string
  workseqId?: string
  workSeqParamList?: unknown[]
  workSeqMaterialList?: unknown[]
  workStepList?: WorkStep[]
  [key: string]: unknown
}

/** 工步参数 (workStepParamList 中的单条) */
export interface WorkStepParam {
  paramName?: string          // 参数名称
  minQualityValue?: string | number | null
  maxQualityValue?: string | number | null
  standardValue?: string | number | null
  paramUnit?: string
  [key: string]: unknown
}

/** 工步下的子步骤 (workStepList 中的单条)
 *  对应 LabVIEW DataOut 结构 */
export interface WorkStep {
  workstepNo?: string
  workstepName?: string       // 对应 DataOut.workstepName
  pSetNo?: string | number | null  // 对应 DataOut.pSetNo
  torqueSettingCount?: number | null  // 对应 DataOut.torqueSettingCount
  workstepType?: number       // 对应 DataOut.workstepType
  docUrl?: string | null      // 对应 DataOut.docUrl
  sortCode?: number
  remark?: string | null
  workStepParamList?: WorkStepParam[]   // 对应 DataOut.Paramlist_out
  workStepMaterialList?: unknown[]
  workStepDocList?: unknown[]
  workStepLineList?: unknown[]
  [key: string]: unknown
}

/** 工步列表数据块（接口二 data 内容） */
export interface RouteData {
  workSeqList?: RouteStep[]
  [key: string]: unknown
}

/**
 * 获取工步列表响应
 * 实际结构：{ code, message, data: { workSeqList: RouteStep[] } }
 */
export interface GetRouteResponse {
  code: number | string
  message?: string
  msg?: string
  data?: RouteData | RouteStep[] | null
  success?: boolean
}

/** 测试结果状态 */
export type TestResult = 'IDLE' | 'OK' | 'NG'

/** LabVIEW通信信号内容 */
export interface LabviewSignal {
  result: TestResult
  orderCode: string
  productCode: string
  timestamp: string
  routeNo: string
}

/** 单次定扭尝试的原始数据记录 */
export interface TighteningAttempt {
  torque: string
  angle: string
  result: 'PASS' | 'FAIL'
  timestamp: string
}

/** 单项定扭任务记录（细化到每一颗螺丝） */
export interface TighteningTask {
  id: string              // 唯一标识，格式如：STEP-SCREW
  workstepNo: string      // 所属工步编号
  workstepName: string    // 所属工步名称，如 "M6定扭"
  pSetNo: string          // 程序号/PSet编号
  screwIndex: number      // 螺丝序号，1-N
  itemDisplayName: string // 显示名称，如 "螺丝1"
  
  torqueMin: number
  torqueMax: number
  torqueUnit: string
  actualTorque: string | null

  angleMin: number
  angleMax: number
  angleUnit: string
  actualAngle: string | null

  result: 'PENDING' | 'PASS' | 'FAIL' // 判定结果
  timestamp?: string      // 最后一次采集时间
  retryCount: number      // 已重试次数
  history: TighteningAttempt[] // 所有尝试的历史记录
}

export interface MaterialItem {
  productCode: string
  productCount: number
}

export interface CompleteCheckInputRequest {
  produceOrderCode: string
  routeNo: string
  technicsProcessCode: string
  tenantID: string
  productMixCode: string | null
  productLine: string
  materialList: MaterialItem[]
}

export type UserRole = 'admin' | 'operator'

export interface User {
  username: string
  role: UserRole
}

/** MES 最终报工数据结构 */
export interface MesSubmission {
  produceOrderCode: string
  routeNo: string
  technicsProcessCode: string
  technicsProcessName: string
  technicsStepCode: string
  technicsStepName: string
  productCode: string
  productCount: number
  productQuality: number // 0:OK, 1:NG
  produceDate: string
  startTime: string
  endTime: string
  userName: string
  userAccount: string
  deviceCode: string
  Remarks: string
  ProduceInEntityList: Array<{
    productCode: string
    ProductCount: number
  }>
  produceParamEntityList: any[]
  ngEntityList: any[]
  cellParamEntityList: any[]
  otherParamEntityList: Array<{
    productCode: string // 这里通常存 bolt_1, bolt_2 等
    otherInfoList: Array<{
      technicsParamName: string
      technicsParamCode: string
      technicsParamValue: string
      desc: string
      technicsParamQuality: string // "0":OK, "1":NG
    }>
  }>
  deviceName: string
}

/** 打印条码项 */
export interface PrintLabelItem {
  code: string
  labelType: string
}

/** 打印请求 */
export interface PrintLabelsRequest {
  printerIp: string
  printerPort: number
  labels: PrintLabelItem[]
  copies?: number
}

/** 打印响应 */
export interface PrintLabelsResponse {
  code?: number
  message?: string
  success?: boolean
  printedCount?: number
}
