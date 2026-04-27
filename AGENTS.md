# AGENTS.md — MES 工序执行系统

## 项目概述

桌面端 MES 工序执行客户端，用于产线扫码绑定模组码与箱码，并与后端 MES API 交互。支持三种工作模式：

- **模块码绑定**：PLC 触发模块码 → 获取工单/工步 → 单物料校验（组件物料逐行扫描，模组码自动跳过）→ 生成模组绑定码 → 全物料校验 → 数据暂存
- **模组入箱**：PLC 箱体码请求信号触发 → 读取箱体码 → 获取工单 → 单物料校验（仅限绑定流程生成的模组码白名单）→ 全物料校验 → 统一上传（绑定数据 + 入箱位置）
- **等离子清洗**：PLC 实时监控与参数读取

同时集成西门子 S7 PLC 通讯，支持实时读写和启动信号触发扫描。

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 UI | Python 3.9 (32-bit) + PyQt5 5.15.2 |
| 样式主题 | 深色科幻风（主背景 #0a0e1a） |
| 网络请求 | `requests`（异步通过 `QThread`） |
| PLC 通讯 | `python-snap7` 1.3 + `snap7.dll`（32-bit） |
| 配置持久化 | `config.json`（自动读写） |

> ⚠️ Python 为 32-bit，因此必须使用 32-bit 的 `snap7.dll`。

## 目录结构

```
pyqt_mes_scanner/
├── main.py                 # 应用入口
├── main_window.py          # 主窗口（binding/packing/plasma 三模式 + S7 生命周期）
├── styles.py               # 全局 QSS 样式
├── dialogs/
│   ├── config_dialog.py    # 系统配置（API 地址、工序编码、S7、日志路径、默认规格/特征代码）
│   └── login_dialog.py     # 登录对话框
├── tabs/
│   ├── route_table_tab.py      # 工步下发表格
│   ├── material_scanner_tab.py # 单物料校验（按需求数展开独立行；模组码自动标记已完成）
│   ├── module_generate_tab.py  # 生成模组绑定码（仅对物料名称含"模组码"的物料申请）
│   ├── module_packing_tab.py   # 模组入箱流程（白名单限制、入箱顺序表格、内置全物料校验）
│   ├── full_material_tab.py    # 全物料校验（绑定/入箱流程均自动调用）
│   ├── api_detail_tab.py       # 接口交互详情展示
│   ├── log_tab.py              # 操作日志
│   ├── plc_monitor_tab.py      # PLC 实时监控（读写数据点）
│   └── api_worker.py           # 异步 HTTP Worker（QThread）
└── services/
    └── s7_service.py       # S7 PLC 封装（Bool/Int/DInt/Real/String 读写）
```

## 核心流程

### 绑定流程（模块码绑定）

```
PLC 启动信号触发
    ↓
读取模块码（DB2 偏移112 String）
    ↓
获取工单（orderApiUrl）
    ↓
工步下发（routeApiUrl）
    ↓
单物料校验（逐行扫描组件物料；物料名称含"模组码"自动标记"无需校验"）
    ↓
生成模组绑定码（仅对"模组码"物料申请；dysl/dcbsl = 来源码数量）
    ↓
全物料校验（fullMaterialCheckUrl；模组码使用生成的 bindCode 参与校验）
    ↓
数据暂存（不上传；等待入箱完成后统一上传）
    ↓
自动切换到入箱模式
```

### 入箱流程（模组入箱）

```
PLC 箱体码请求信号触发（DB3.DBX0.0 = 1）
    ↓
自动切换到入箱模式（如不在入箱模式）
    ↓
读取箱体码（DB3 偏移200 String）
    ↓
获取工单（orderApiUrl）
    ↓
工步下发（routeApiUrl）
    ↓
单物料校验（扫描生成的模组码 bindCode；白名单限制；生成多少个校验多少个）
    ↓
全物料校验（fullMaterialCheckUrl）
    ↓
统一上传：
    ① 模块绑定模组数据上传（moduleBindPushUrl）
    ② 模组入箱位置信息上传（packingUploadUrl）
```

## 编码约定

### API 响应判断
后端成功返回 `{"code": 200, ...}`。统一使用辅助函数判断：
```python
def _is_success(resp):
    return resp.get("code") == 200
```

### 异步网络请求
所有 HTTP 请求必须在 `QThread` 中执行，禁止在主线程直接调用 `requests.post`，防止 UI 卡死。Worker 完成后通过 `pyqtSignal` 回传结果。

### 日志与记录
- 操作日志通过 `_add_log(level, msg)` → 写入 UI 的 `log_tab`
- 接口记录通过 `_add_api_record_dict(rec)` → 写入 UI 的 `api_tab`
- 若配置了 `logSavePath`，两者都会自动持久化到本地文本文件（按日期分文件）

### PLC 地址格式
内部统一使用 `DB{db}.DBX{offset}.{bit}` 字符串表示 Bool 地址，解析函数为 `PlcMonitorTab._parse_address`。

### 配置键名
- S7 配置统一使用 `"s7Config"`
- 日志保存路径使用 `"logSavePath"`
- 默认规格代码 `"defaultSpecCode"`（ggdm）
- 默认特征代码 `"defaultFeatureCode"`（tzdm）

### 字段兼容别名
部分字段存在历史别名，需兼容处理：
- `routeCode` ↔ `route_No`
- `datas` ↔ `data`
- `productMixCode` ↔ `specsCode` ↔ `specCode`

## 关键业务规则

### 物料识别规则
| 物料类型 | 识别条件 | 单物料校验 | 生成绑定码 |
|---------|---------|-----------|-----------|
| **模组码** | 物料名称含"模组码" | 入箱流程**需校验**（扫描 bindCode） | 是 |
| **国标码** | 物料名称含"国标码" | **无需校验**，自动标记完成 | 否 |

- 绑定流程中，国标码自动标记为 `completed`
- 入箱流程中，国标码自动标记为 `completed`，模组码需扫描生成的 `bindCode`

### 单物料校验条码匹配
扫描条码必须以物料编号开头匹配（如物料编号 `03HKB33S`，条码 `03HKB33S2026004250000003` 可匹配）。

### 入箱白名单
入箱流程仅允许扫描绑定流程生成的模组码（`bindCode` 列表）。

### 数据上传时机
- 绑定流程完成后**暂存数据**，不立即上传
- 入箱流程完成后**统一执行两个上传**：
  1. 模块绑定模组数据上传
  2. 模组入箱位置信息上传
- 上传接口目前记录日志，待确认真实接口格式后改为真实 HTTP POST

## S7 PLC 信号配置

所有信号地址均在**系统配置 → S7 通讯配置**中配置，不再写死。

| 信号 | 默认地址 | 类型 | 说明 |
|------|---------|------|------|
| 启动信号 | DB1.DBW6 | Int | 绑定模式：读到触发值后读取模块码 |
| 模块码信号 | DB2.DBW112 | String(24) | 绑定流程的产品条码 |
| 箱体码请求信号 | DB3.DBX0.0 | Bool | 入箱模式：读到 1 后自动切换并读取箱体码 |
| 箱体码数据 | DB3.DBW200 | String(24) | 入箱流程的 PACK 箱码 |

### 边缘检测
Bool 类型信号使用边缘检测（上次值 ≠ 触发值 且 本次值 = 触发值），避免持续为 True 时反复触发。

## 构建与运行

```bash
cd pyqt_mes_scanner
python main.py
```

确保项目根目录存在 32-bit `snap7.dll`（约 209KB），否则 `python-snap7` 会报 `can't find snap7 library`。

## 注意事项

1. **snap7.dll 架构**：必须与 Python 解释器位数一致（当前为 32-bit）。
2. **S7 启动信号**：已通过配置界面暴露，不再固定。
3. **日志持久化**：配置 `logSavePath` 后，操作日志和接口交互会自动按日期分文件保存。
4. **python-snap7 1.3 兼容性**：`get_string()` 仅接受 `(buffer, start_index)` 两个参数，调用时不可传第三个参数。
