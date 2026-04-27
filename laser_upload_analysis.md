# 激光焊接数据上传接口分析 (PushPackMessageToMes)

该文件对位于 `C:\Users\95403\Desktop\激光焊接.txt` 的数据交互文件进行详细解析，梳理上传到 MES 后端的业务数据结构。

## 1. 接口基础信息
- **请求方法**: POST
- **请求URL**: `http://172.25.57.144:8072/api/ProduceMessage/PushPackMessageToMes`

---

## 2. 报文上传标准格式示例 (JSON)

你可以直接参考、复制以下格式进行对接开发。

```json
[
  {
    "LineLocation": "",
    "ProduceOrderCode": "P0KH202603120001_DJ2529",
    "RouteNo": "DJ2529_0KH_test_1",
    "TechnicsProcessCode": "CTP_P1190",
    "TechnicsProcessName": "激光焊接",
    "TechnicsStepCode": "",
    "TechnicsStepName": "",
    "ProductCode": "03HPB0KH0001TDG4T0000110",
    "ProductCount": 1,
    "ProductQuality": 1,
    "ProduceDate": "2026-04-26",
    "StartTime": "2026/4/26 22:00:37",
    "EndTime": "2026-04-26 22:06:39",
    "UserName": "",
    "UserAccount": "",
    "DeviceCode": "CTP_JGHJ",
    "DeviceName": "激光焊接",
    "Remarks": "",
    "KafkaLineNo": "",
    "FromPrs": "",
    "ProduceInEntityList": [],
    "ProduceParamEntityList": [
      {
        "TechnicsParamName": "离焦量",
        "ProductCode": "03HPB0KH0001TDG4T0000110",
        "TechnicsParamCode": "JGHJ0005",
        "TechnicsParamValue": "2",
        "Desc": "",
        "TechnicsParamQuality": "1"
      },
      {
        "TechnicsParamName": "焊接相对速度",
        "ProductCode": "03HPB0KH0001TDG4T0000110",
        "TechnicsParamCode": "JGHJ0006",
        "TechnicsParamValue": "71.4",
        "Desc": "",
        "TechnicsParamQuality": "1"
      },
      {
        "TechnicsParamName": "抖动直径",
        "ProductCode": "03HPB0KH0001TDG4T0000110",
        "TechnicsParamCode": "JGHJ0007",
        "TechnicsParamValue": "0.6",
        "Desc": "",
        "TechnicsParamQuality": "1"
      },
      {
        "TechnicsParamName": "抖动距离",
        "ProductCode": "03HPB0KH0001TDG4T0000110",
        "TechnicsParamCode": "JGHJ0008",
        "TechnicsParamValue": "0.3",
        "Desc": "",
        "TechnicsParamQuality": "1"
      },
      {
        "TechnicsParamName": "焊接轨迹直径",
        "ProductCode": "03HPB0KH0001TDG4T0000110",
        "TechnicsParamCode": "JGHJ0016",
        "TechnicsParamValue": "14",
        "Desc": "",
        "TechnicsParamQuality": "1"
      },
      {
        "TechnicsParamName": "外环设定功率",
        "ProductCode": "03HPB0KH0001TDG4T0000110",
        "TechnicsParamCode": "JGHJ0018",
        "TechnicsParamValue": "1600",
        "Desc": "",
        "TechnicsParamQuality": "1"
      },
      {
        "TechnicsParamName": "内环设定功率",
        "ProductCode": "03HPB0KH0001TDG4T0000110",
        "TechnicsParamCode": "JGHJ0019",
        "TechnicsParamValue": "1800",
        "Desc": "",
        "TechnicsParamQuality": "1"
      },
      {
        "TechnicsParamName": "焊接时长",
        "ProductCode": "03HPB0KH0001TDG4T0000110",
        "TechnicsParamCode": "JGHJ0022",
        "TechnicsParamValue": "177",
        "Desc": "",
        "TechnicsParamQuality": "1"
      }
    ],
    "NgEntityList": [],
    "CellParamEntityList": [],
    "OtherParamEntityList": [
      {
        "ProductCode": "cell1",
        "OtherInfoList": [
          {
            "TechnicsParamName": "保护气流量",
            "TechnicsParamCode": "JGHJ0002",
            "TechnicsParamValue": "6.87",
            "Desc": "",
            "TechnicsParamQuality": "1"
          },
          {
            "TechnicsParamName": "外环实际功率",
            "TechnicsParamCode": "JGHJ0003",
            "TechnicsParamValue": "1737",
            "Desc": "",
            "TechnicsParamQuality": "1"
          },
          {
            "TechnicsParamName": "内环实际功率",
            "TechnicsParamCode": "JGHJ0004",
            "TechnicsParamValue": "1561",
            "Desc": "",
            "TechnicsParamQuality": "1"
          },
          {
            "TechnicsParamName": "除尘风速",
            "TechnicsParamCode": "JGHJ0009",
            "TechnicsParamValue": "29.89",
            "Desc": "",
            "TechnicsParamQuality": "1"
          },
          {
            "TechnicsParamName": "压头压力",
            "TechnicsParamCode": "JGHJ0010",
            "TechnicsParamValue": "74.89",
            "Desc": "",
            "TechnicsParamQuality": "1"
          },
          {
            "TechnicsParamName": "极柱行号",
            "TechnicsParamCode": "JGHJ0011",
            "TechnicsParamValue": "1",
            "Desc": "",
            "TechnicsParamQuality": "1"
          },
          {
            "TechnicsParamName": "极柱列号",
            "TechnicsParamCode": "JGHJ0012",
            "TechnicsParamValue": "1",
            "Desc": "",
            "TechnicsParamQuality": "1"
          },
          {
            "TechnicsParamName": "伺服X轴坐标",
            "TechnicsParamCode": "JGHJ0013",
            "TechnicsParamValue": "776.75",
            "Desc": "",
            "TechnicsParamQuality": "1"
          },
          {
            "TechnicsParamName": "伺服Y轴坐标",
            "TechnicsParamCode": "JGHJ0014",
            "TechnicsParamValue": "463.12",
            "Desc": "",
            "TechnicsParamQuality": "1"
          },
          {
            "TechnicsParamName": "伺服Z轴坐标",
            "TechnicsParamCode": "JGHJ0015",
            "TechnicsParamValue": "231",
            "Desc": "",
            "TechnicsParamQuality": "1"
          },
          {
            "TechnicsParamName": "实际极柱测距值",
            "TechnicsParamCode": "JGHJ0017",
            "TechnicsParamValue": "0.36",
            "Desc": "",
            "TechnicsParamQuality": "1"
          },
          {
            "TechnicsParamName": "电芯位置顺序",
            "TechnicsParamCode": "JGHJ0001",
            "TechnicsParamValue": "1",
            "Desc": "",
            "TechnicsParamQuality": "1"
          }
        ]
      }
    ]
  }
]
```

---

## 3. 核心字段业务含义参照

### 1) 根节点
| 字段名 | 业务含义 |
| :--- | :--- |
| `ProduceOrderCode` | 生产工单号 |
| `ProductCode` | 模组主条码 (白车身SN/箱码) |
| `ProductQuality` | 合格状态 (1=OK, 0=NG) |

### 2) 全局工艺参数 (`ProduceParamEntityList`)
| 参数编码 | 名称 | 典型值 |
| :--- | :--- | :--- |
| **JGHJ0005** | 离焦量 | `2` |
| **JGHJ0018** | 外环设定功率 | `1600` |
| **JGHJ0022** | 焊接时长 | `177` |

### 3) 独立极柱轨迹采集 (`OtherParamEntityList`)
| 参数编码 | 数据项 | 典型值 |
| :--- | :--- | :--- |
| **JGHJ0011/12** | 行列号 | `1`/`2` |
| **JGHJ0013/14/15**| X/Y/Z坐标 | `776.75` |
