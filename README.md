# BYD China — Home Assistant 集成

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Version](https://img.shields.io/github/v/release/lejw0925/byd-China)](https://github.com/lejw0925/byd-China/releases)

Home Assistant 自定义集成，用于接入比亚迪（BYD）中国区车辆。通过云端轮询获取车辆遥测数据和 GPS 定位，支持王朝、海洋、腾势、仰望、方程豹全品牌。

## 功能

- **车辆信息**：VIN、车牌、型号、颜色、品牌
- **系统状态**：动力电池、充电系统、ESP、ABS、制动、转向等 12 项
- **车门/车窗**：四门开闭、后备箱、天窗状态
- **门锁**：四门锁定/解锁状态
- **轮胎**：四轮胎压及状态
- **电池/燃油**：电量、油量、纯电续航、燃油续航
- **里程**：总里程、HEV 里程
- **能耗**：本次能耗、累计能耗
- **充电**：充电状态、预约充电时间
- **GPS**：经纬度（GCJ-02 → WGS-84 自动转换）
- **轮询配置**：遥测和 GPS 轮询间隔可调（30–900 秒）

## 安装

### 通过 HACS

1. 在 HACS 中添加自定义仓库：`https://github.com/lejw0925/byd-China`
2. 搜索 "BYD China" 安装
3. 重启 Home Assistant

### 手动安装

将 `custom_components/byd_china/` 复制到 Home Assistant 的 `custom_components/` 目录，重启后在 **设置 → 设备与服务 → 添加集成** 搜索 "BYD China"。

## 配置

| 参数 | 说明 |
|---|---|
| 用户名 | BYD App 登录手机号 |
| 密码 | BYD App 登录密码 |
| 品牌 | 王朝 / 海洋 / 腾势 / 仰望 / 方程豹 |
| Debug Dump | 是否保存 API 原始数据到 `.storage/byd_vehicle_debug/` |

> **注意**：需要使用**车主主账号**登录。授权账户（非车主）无法获取遥测和 GPS 数据（服务端返回 `code=240`）。

## 实体

- **sensor（~52 个）**：车辆信息、系统状态、车门/窗/锁、胎压、电池/燃油、里程、能耗、GPS 经纬度、时间戳
- **device_tracker**：车辆位置（GCJ-02 → WGS-84 转换后显示在地图上）
- **number（2 个）**：遥测轮询间隔、GPS 轮询间隔（30–900 秒可调）

## 服务

| 服务 | 说明 |
|---|---|
| `byd_china.fetch_realtime` | 强制刷新车辆遥测数据 |
| `byd_china.fetch_gps` | 强制刷新 GPS 定位数据 |

两个服务均接受 `device_id` 参数，可选择刷新特定车辆。

## 车辆位置与轨迹

集成创建 `device_tracker` 实体（名称：**位置**），自动在地图上显示车辆图标。启用 HA 的 [`recorder`](https://www.home-assistant.io/integrations/recorder/) 记录历史后即可在地图卡片上查看行驶轨迹。

> 如需更完整的轨迹记录功能，可配合 [Traccar](https://www.traccar.org/) 等专业 GPS 追踪平台使用。

## 致谢

本项目的实现离不开以下开源项目：

- **[pyBYD](https://github.com/nichoti/pyBYD)**（MIT License）— BYD 车辆 API 的 Python 异步客户端库。本项目将其作为 vendored 库内置于 `pybyd_china/`，并扩展了中国区支持（WBSK 加密、CN 端点）。
- **[BYD-re](https://github.com/nichoti/BYD-re)** — BYD App HTTP 加密路径的逆向工程成果，提供了 CN 模式下的 WBSK 白盒 AES 加密表及端点映射。
- **[Home Assistant](https://github.com/home-assistant/core)**（Apache 2.0）— 开源智能家居平台。

## 开源许可

本项目基于 [MIT License](LICENSE) 发布。

Vendored 的 `pybyd_china/` 衍生自 [pyBYD](https://github.com/nichoti/pyBYD)（MIT License），版权归原作者所有。`data/wbsk_tables.json` 提取自 BYD-re 逆向工程成果。
