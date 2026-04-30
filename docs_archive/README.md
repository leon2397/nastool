# ⚠️ NASTOOL 旧项目已废弃

> **⚠️ 本目录（`C:\tools416\`）中的 nastools 项目已废弃。**
> **当前开发方向请移至：`C:\tools416\nastool-v1.0.0\`（模块化 v1.0.0）**

> 废弃日期：2026-04-18
> 废弃原因：架构升级，以模块化为唯一开发方向

---

## 废弃说明

| 项目 | 路径 | 状态 | 说明 |
|------|------|------|------|
| **nastools（旧）** | `nastool/` | ❌ 已废弃 | 单体架构，历史包袱重 |
| **relay_server** | `relay_server/` | 🔄 独立运行 | ECS上运行，非CLI项目 |
| **nastool-modules（新）** | `nastool-common/` 等 | ✅ **唯一开发方向** | 模块化架构，v1.0.0 MVP |

详细废弃文档：`nastool/DEPRECATED.md`

---

## 快速开始（新项目）

```powershell
# 安装 nastool-modules（模块化版本）
cd C:\tools416\nastool-common && pip install -e .
cd C:\tools416\nastool-core && pip install -e .
cd C:\tools416\nastool-cli && pip install -e .

# 运行
nastool --quick      # 快速检测（89项）
nastool --full       # 完整检测（93项）
nastool --fix-auto   # 自动修复
```

---

## 为什么废弃

| 问题 | 说明 |
|------|------|
| 单体架构 | 所有代码混在一起，无法独立发布单个模块 |
| 技术债务 | 43+ 文件使用旧的 ctx.result() API，质量不一致 |
| 无版本控制 | 没有 Git 仓库，历史修改无法追溯 |
| 定位模糊 | 本地诊断和远程管理混在一起，边界不清 |

---

## 原 nastools v4.2.0 功能回顾（已废弃）

- 35 项硬件检测 + 100+ 健康检测
- 15+ 种自动修复
- SSH / USB / Relay 多种连接方式
- 支持 37+ 款 ARM 设备
- 健康评分 0-100 分
- Windows GUI（nastools_pkg）

---

## 文档

- **新项目说明**：`nastool-v1.0.0/README.md`
- **模块化计划**：`SPLIT-PLAN.md`
- **发布计划**：`MVP-RELEASE-PLAN.md`
- **历史记录**：`MEMO.md`
- **原项目废弃文档**：`nastool/DEPRECATED.md`

---

*废弃日期：2026-04-18*

---

## 一句话介绍

nastools 是一款 Windows 端 ARM NAS 一键检测与部署工具，让普通用户也能轻松了解自己的 NAS 健不健康，并支持一键部署 ARM NAS 管理系统。

---

## 核心功能

### 🛠️ 检测功能（35 项硬件检测 + 100+ 健康检测）

| 类别 | 检测项 |
|------|--------|
| 系统 | Python 版本 / pip / 内存 / 磁盘 / CPU 温度 / 系统库 / Docker / 运行时间 |
| 网络 | DNS 解析 / 互联网 / 端口 / 网卡速率 / DNS 覆盖 / NAS 后端 |
| 存储 | 磁盘空间 / 读写速度 / SMART 健康 / HDD温度 / RAID / Docker镜像 / 路径 / 趋势 |
| AI | GPU / CUDA |
| 安全 | 防火墙 / SELinux / SSH root / 登录失败 / SSL 证书 |
| NAS | DSM/QTS 版本 / 用户账号 / 共享权限 / UPS / 日志磁盘 / 定时任务 |

### 🔧 自动修复（15+ 种）

- Python 3.11 一键安装
- DNS 修复（追加模式，不覆盖）
- 路径环境变量修复
- CUDA / TensorRT 一键安装
- Docker 一键安装
- ...更多

### 📊 健康评分系统

- 综合评分 0-100 分
- 分级显示：健康(80+)/警告(60-79)/问题(<60)
- 自动归类问题项
- 每个问题给出具体修复建议

### 📦 部署能力

- SFTP 上传部署
- 部署后自动验证
- 一键回滚
- 安全卸载

### 🔌 连接方式

| 方式 | 说明 |
|------|------|
| SSH | 传统局域网连接 |
| USB/ADB | 即插即用直连 |
| **Relay** | **跨网远程中继（无需公网IP）** |

---

## 支持设备（37+ 款）

| 品牌 | 数量 | 型号 |
|------|------|------|
| 群晖 Synology | 12 款 | DS220+/DS920+/DS1520+/DS1821+... |
| 威联通 QNAP | 12 款 | TS-251D/TS-453D/TS-464/TS-873A... |
| NVIDIA Jetson | 16 款 | Xavier NX/Orin Nano/Nano/AGX Orin... |
| Rockchip | 5 款 | OrangePi 5/Rock 5B/NanoPi R6S... |
| 树莓派 | 2 款 | Pi 4 / Pi 5 |
| SOPHON | 12 款 | BM1688/BM1684/BM1690/SE5/SE7... |

---

## 版本演进

```
v4.2.0  跨网远程管理 ✅ ← 当前
v4.1.0  部署能力强化 ✅
v4.0.2  工具属性强化 ✅
v4.0.1  代码质量 ✅
v4.0.0  架构重构 ✅
v3.0.0  Relay/Agent 基础 ✅
```

---

## 快速开始

### 1. 下载安装

```bash
# 方式一：直接下载发布包
下载 nastools-v4.2.0.zip 并解压

# 方式二：克隆仓库
git clone https://github.com/your-repo/nastools.git
```

### 2. 运行

```bash
# 方式一：双击运行
nastools.exe

# 方式二：命令行
python -m nastools
```

### 3. 连接 NAS

- 输入 NAS 的 IP、端口、用户名、密码
- 或使用 USB/ADB 直连
- **或通过 Relay 远程连接（无需在同一网络）**

### 4. 一键检测

点击「开始检测」，查看健康报告

### 5. 一键修复

对异常项，点击「一键修复」

---

## 技术栈

- **GUI**: Python + customtkinter
- **诊断引擎**: Python（CLI）
- **Relay Server**: Node.js + WebSocket
- **ARM Agent**: Python + asyncio
- **Web Dashboard**: Vue 3

---

## 项目结构

```
nastools/
├── nastool/           # ARM 端核心库（214 文件）
│   ├── adapters/      # NAS 适配器（14 个）
│   ├── checks/        # 检测模块（35 项）
│   ├── fixes/         # 修复模块（15+ 种）
│   ├── core/          # 核心功能
│   └── utils/         # 工具函数（16 个）
├── nastools_pkg/      # Windows GUI（32 文件）
├── relay_server/      # 中继服务器
│   ├── src/           # Node.js 服务器（4 文件）
│   ├── agent/         # Python Agent（10 文件）
│   └── web_dashboard/ # Vue 3 面板（18 文件）
└── dist/              # 发布包
```

---

## 文档

- [用户手册](nastools_README.md)
- [版本路线图](nastools_ROADMAP.md)
- [更新日志](CHANGELOG.md)
- [技术备忘录](MEMO.md)

---

## 许可证

MIT License

---

*项目版本：v4.2.0*
*更新日期：2026-04-14*
