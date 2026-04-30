# nastools - ARM NAS 一键诊断与部署工具

> **nastools** = nastool + tools，Windows 端 GUI 封装工具
> **当前版本：v4.0.0** | 架构重构完成

## 快速启动

```bash
# 方式1（推荐）：双击
启动 nastools.bat

# 方式2：直接运行（需要 Python 3.8+）
python nastools_pkg/main.py
```

> 首次运行若提示缺少 `paramiko`，请运行：
> `pip install paramiko`

---

## 什么是 nastools？

nastools 是 **Windows 端的 GUI 工具**，通过 SSH 连接 ARM 设备，自动完成：

```
连接 ARM 设备 → 检测 → 查看结果 → 修复问题 → 部署 NAS 系统
```

| 对比项 | nastool | nastools |
|--------|---------|----------|
| 运行平台 | ARM 设备 | Windows 电脑 |
| 交互方式 | 命令行 | 图形界面 |
| 适用场景 | 设备本地诊断 | 远程管理多台设备 |
| 部署功能 | 无 | ✅ 一键部署 NAS |

---

## 功能一览

### ⚡ 连接设备
- 输入 IP / 端口 / 用户名 / 密码
- SSH 自动连接，自动识别设备信息
- 连接状态实时显示

### 🔍 33 项检测

| 分类 | 检测项 |
|------|--------|
| **系统** | Python 版本 / pip / 系统依赖库 / 内存状态 / 磁盘空间 |
| **网络** | 互联网连接 / DNS 解析 / NAS 后端连通 / 端口冲突 |
| **存储** | 存储路径存在 / 写入速度 |
| **AI算力** | GPU 检测 / NVIDIA 驱动 / CUDA / TensorRT / JetPack / RKNN NPU / PyTorch / ONNX Runtime |
| **安全** | 防火墙 / SELinux / SSH Root 登录 |

### ⚙ 5 种自动修复（nastool fixes/）

| 修复项 | 说明 | 风险 |
|--------|------|------|
| ConfigDNS | **追加** nameserver 8.8.8.8 + 223.5.5.5（不覆盖）| ✅ 低 |
| CreatePaths | 自动创建缺失的存储目录 | ✅ 低 |
| InstallPython | 检测版本后安装 Python 3.11 | 🟡 中 |
| InstallCUDA | 检测 Jetson 型号后安装匹配版本 | 🔴 高 |
| InstallDocker | 检测系统后安装 Docker Engine | 🔴 高 |

### 🚀 NAS 部署（v1.1 安全底线）
- 一键在 ARM 设备上部署 NAS 管理系统
- **部署前自动备份**：任何覆盖操作前先备份（时间戳命名，可回滚）
- **DNS 追加模式**：只追加 nameserver，绝不覆盖 /etc/resolv.conf
- 自动创建 systemd 服务 + 设置开机启动
- **一键回滚**：GUI 内可恢复任意备份版本

---

## 使用流程

```
┌─────────────────────────────────────────┐
│  1. 双击「启动 nastools.bat」           │
│  2. 填 IP / 用户名 / 密码               │
│  3. 点「⚡ 连接设备」                    │
│  4. 点「▶ 开始检测」                     │
│  5. 看结果（绿✓ / 黄! / 红✗）           │
│  6. 勾选要修复的 → 点「⚙ 修复选中项」   │
│  7. 点「🚀 部署 NAS」→ 完成！           │
└─────────────────────────────────────────┘
```

---

## 技术特点

| 特点 | 说明 |
|------|------|
| **tkinter** | Python 内置 GUI 库，零额外依赖 |
| **原生 threading** | 无 multiprocessing，无进程爆炸风险 |
| **复用 nastool** | 检测/修复逻辑直接调用 nastool/，零重复维护 |
| **v1.1 安全底线** | DNS 追加模式 / 部署前自动备份 / 一键回滚 |
| **离线可用** | 所有脚本内置，无网络也能运行 |
| **单进程** | 只有 1 个 python.exe，内存 < 70 MB |
| **深色科技风** | #0d1117 深色背景 + 绿/红/黄状态灯 |

---

## 文件结构

```
D:\armtool415\
├── nastool/               ← 诊断引擎（nastool v3.0.7，106文件，16965行）
│   ├── checks/            22 项硬件/网络/存储/AI/安全检测
│   ├── fixes/             5 种自动修复
│   ├── adapters/          4 种 NAS 适配器（已注册）
│   ├── profiles/          设备预配置（YAML）
│   └── reporters/         多格式报告
├── nastools_pkg/          ← Windows GUI 封装层（v1.0.2）
│   ├── gui/               Tkinter 对话框
│   ├── core/              SSH / 健康检测 / UPnP / 配置加载
│   ├── scripts/           部署 / 验证 / 卸载脚本
│   └── config/            checks.yaml 检测配置
├── nastools-v1.0.2/      ← v1.0.2 发布包
├── nastools-v2.0.0/      ← v2.0.0 发布包（含 relay_server / dashboard）
├── relay_server/          ← WebSocket 中继服务端（Node.js）
├── docs/                 ← V3.0 开发文档
├── 启动 nastools.bat      ← 双击启动
├── CHANGELOG.md           更新日志
├── README.md              项目说明
├── nastools_README.md     本文件（用户手册）
└── nastools_ROADMAP.md    版本规划
```

---

## 适用设备

所有支持 SSH 的 ARM 设备：

- 群晖 Synology NAS（ARM 架构）
- 威联通 QNAP NAS（ARM 架构）
- NVIDIA Jetson 系列
- 树莓派 Raspberry Pi
- Rockchip RK3588 开发板
- 华为海思 / 其他 ARM Linux 设备

---

## 版本信息

| 项目 | 内容 |
|------|------|
| nastools 版本 | v1.1 |
| 发布日期 | 2026-04-13 |
| nastools_pkg 大小 | ~42KB（含 8 个模块文件）|
| nastool 检测项 | 22 项（来自 nastool v3.0.7）|
| nastool 修复项 | 4 项 |
| 内存占用 | ~67 MB |
| Python 版本 | Python 3.8+ |
| 依赖 | paramiko + tkinter |

---

## 常见问题

**Q: 提示 "Python 未安装"？**
> 下载 Python 3.8+：https://www.python.org/downloads/

**Q: 提示 "No module named 'paramiko'"？**
> 运行 `pip install paramiko`

**Q: 连接超时？**
> 检查设备 IP 是否正确，设备是否在线，SSH 端口是否默认 22

**Q: 检测失败？**
> 部分检测项（如 NVIDIA 驱动）只在对应设备上有效，属于正常现象

---

## 技术架构（v1.1 重构）

```
原架构：nastools.py (921行巨石文件)
  └─ 内嵌 200行 Python 检测脚本（字符串）
  └─ 内嵌 150行 Bash 修复脚本（字符串）
  └─ 内嵌 100行 Bash 部署脚本（字符串）

重构后（nastools_pkg/）：
  └─ 直接调用 nastool/ 库（22 checks / 4 fixes，零重复）
  └─ integration/remote.py  胶水层，三种执行模式
  └─ scripts/deploy.py       只有部署脚本（v1.1 后由 nastool fixes/ 接管）
  └─ gui/app.py              只有 GUI 逻辑，无嵌入式脚本
```

**与 nastool/ 的关系**：nastools 是 nastool 的 Windows GUI 封装层，检测逻辑和修复逻辑完全复用 nastool v3.0.7，不再重复维护。
