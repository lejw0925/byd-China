# BYD China - Home Assistant Integration

Home Assistant 自定义集成，用于接入比亚迪（BYD）中国区车辆。通过云端轮询获取车辆遥测数据和 GPS 定位。

## 功能

- 车辆信息：VIN、车牌、型号、颜色、品牌
- 系统状态：电池、充电、ESP、ABS、制动、转向、动力等 12 项
- 车门/车窗/天窗/后备箱状态
- 四门门锁状态
- 四轮胎压及状态
- 电量/油量/续航里程/总里程/HEV 里程
- 能耗统计
- GPS 定位（GCJ-02 → WGS-84 自动转换）
- 充电状态与预约充电信息
- 可配置的遥测和 GPS 轮询间隔

## 安装

将 `custom_components/byd_china/` 复制到 Home Assistant 的 `custom_components/` 目录：

```
custom_components/
└── byd_china/
    ├── __init__.py
    ├── config_flow.py
    ├── coordinator.py
    ├── sensor.py
    ├── device_tracker.py
    ├── number.py
    ├── pybyd_china/
    └── ...
```

重启 Home Assistant 后，在 **设置 → 设备与服务 → 添加集成** 中搜索 "BYD China"。

## 配置

| 参数 | 说明 |
|---|---|
| 用户名 | BYD App 手机号 |
| 密码 | BYD App 登录密码 |
| 品牌 | 王朝 / 海洋 / 腾势 / 仰望 / 方程豹 |
| Debug dump | 是否保存 API 原始数据到 `.storage/byd_vehicle_debug/` |

> **注意**：需要使用**车主主账号**登录，授权账户无法获取遥测和 GPS 数据。

## 服务

- `byd_china.fetch_realtime` — 强制刷新车辆遥测数据
- `byd_china.fetch_gps` — 强制刷新 GPS 定位数据

## 依赖

Home Assistant 会自动安装以下依赖：

- `aiohttp >= 3.9`
- `pydantic >= 2.6`
- `paho-mqtt >= 2.1`
- `cryptography >= 42.0`

## 致谢

- [pyBYD](https://github.com/nichoti/pyBYD) — 底层 BYD API 客户端库
- [BYD-re](https://github.com/nichoti/BYD-re) — API 逆向工程参考
