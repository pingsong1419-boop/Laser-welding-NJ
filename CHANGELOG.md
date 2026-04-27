# 变更日志

> 按时间倒序记录所有功能改动与修复。每次提交前更新此文件。

---

## 2026-04-22

### 新增等离子清洗监控模块
- **左侧导航栏**：新增 "🔬 等离子清洗" 按钮，与模块码绑定/模组入箱并列
- **`tabs/plasma_cleaning_tab.py`**：
  - 顶部状态栏：PLC 连接状态 + 清洗运行状态指示（待机/清洗中）
  - 数据表格：`QTableWidget` 7 列展示（参数名称、DB块、偏移、类型、当前值、单位、更新时间），清洗状态 Bool 值自动红/绿色高亮
  - 默认 PLC 地址：`DB100` 区域（可在界面上点击"编辑参数地址"修改）
  - 实时刷新：1 秒轮询，自动根据 `清洗状态` Bool 值切换顶部状态标签颜色
  - 参数持久化：修改后的地址保存到 `config.json` 的 `plasmaMonitorPoints`
- **`main_window.py`**：扩展 `current_mode` 为 `binding | packing | plasma`，`_switch_mode` 同步处理三种模式样式切换

### 界面字体与布局优化
- **全局字体增大**：`styles.py` 全局 `font-size: 12px` → `14px`，各层级统一 +2px
- **控件尺寸同步增大**：`brand_icon` 34→38px、`step_badge` 20→24px、按钮/输入框/表格 padding 等比例增加
- **代码内硬编码字体修正**：`main_window.py` 及所有 `tabs/*.py`、`dialogs/*.py` 中通过 `setStyleSheet` 写死的 `font-size` 统一 +2px，防止运行时覆盖全局样式
- **表格列宽调整**：`material_scanner_tab.py`、`module_packing_tab.py`、`module_generate_tab.py` 中固定列宽从 60px 增大到 70~100px，`setMinimumSectionSize(80)` → `100`

### Bug 修复
- **`main_window.py` `_handle_scan`**：补漏 `self.worker.api_record.connect(self._add_api_record_dict)`，解决获取工单后接口交互记录未显示在"记录"页的问题
- **S7 PLC 自动重连**：新增 `_try_s7_reconnect` + `s7_reconnect_timer`（5秒间隔），连接断开或初始化失败后自动尝试重连，成功自动恢复轮询；失败日志每 30 秒汇总一次，避免刷屏

### PLC 监控模块完善
- **删除默认监控点**：移除硬编码的"启动信号"默认点，改为空列表启动
- **监控点持久化**：新增 `plcMonitorPoints` 配置键，添加/删除后自动保存到 `config.json`，重启自动恢复
- **日志详细化**：写入/读取/添加/删除操作均记录完整地址（如 `DB1.DBW0 (Int)`）
- **写入对话框修复**：补漏 `QInputDialog` 导入，解决点击"写入值"崩溃
- **去掉只读限制**：默认方向改为"读写"，删除只读拦截逻辑

### PLC 启动信号流程重构
- **地址固定化**：移除配置界面中的启动信号设置，改为代码硬编码
- **新触发逻辑**：
  1. 轮询 `DB1.DBW6`（Word），边缘检测（`0→1`）触发
  2. 读取 `DB2.DB 112.0`（String，长度 24）获取模块码
  3. 自动填入扫描框并调用 `_handle_scan()` 启动完整绑定流程
  4. 写回 `0` 复位信号，防止重复触发

### 日志持久化
- `ConfigDialog` 新增"日志配置"区域，支持选择日志保存目录
- `MainWindow` 中操作日志和接口交互记录自动按日期分文件保存：
  - `操作日志_YYYY-MM-DD.txt`
  - `接口交互_YYYY-MM-DD.txt`

### 配置与 Bug 修复
- **配置键名统一**：`ConfigDialog` 保存键从 `"s7"` 改为 `"s7Config"`，兼容旧配置读取
- **snap7 类型修复**：`snap7.type.Areas.DB` → `snap7.types.Areas.DB`（`python-snap7` 1.3 正确模块名）
- **`MainWindow` 初始化顺序修复**：`S7Service` 提前到 `_setup_ui()` 之前初始化，解决 `AttributeError: 'MainWindow' object has no attribute 's7_service'`

---

## 2026-04-22 之前

### S7 通信框架
- 创建 `services/s7_service.py`：封装 `python-snap7`，支持 Bool/Int/DInt/Real/String 读写
- `ConfigDialog` 增加 S7 配置区域（IP、Rack、Slot、轮询间隔）
- `MainWindow` 集成 S7 生命周期：启动自动连接、定时轮询启动信号
- **snap7.dll 架构兼容**：下载并放置 32-bit `snap7.dll`（Python 为 32-bit）

### 配方管理
- `ConfigDialog` 新增配方 CRUD（名称、specsCode、备注）
- `MainWindow` 工具栏新增配方下拉框，支持按 `specsCode` 过滤多工单响应
- 工单不匹配时拦截并提示，避免误绑定

### API 与流程优化
- **ModulePackingTab UI 清理**：移除"PACK 箱信息"冗余卡片，扩大工步列表区域
- **API 日志记录**：`WorkerThread` / `PackingMaterialWorker` 新增 `api_record` 信号，所有 HTTP 交互写入 📋 记录页
- **pack_input 焦点修复**：确认点击区域正常，移除调试背景

---

## 记录规范

| 字段 | 说明 |
|---|---|
| 日期 | 修改当天日期 |
| 模块 | 影响的文件或功能模块 |
| 类型 | `Feature` / `Fix` / `Refactor` / `UI` |
| 描述 | 一句话说明改动点 |
