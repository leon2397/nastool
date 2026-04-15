# nastool v6.0-hwjet

> 🍓 ARM device diagnostic toolkit for [AI-NAS Media Manager](https://qizhiainas.com)

**华为昇腾 + NVIDIA Jetson 双平台 AI 边缘诊断专业版**

## What's New in v6.0-hwjet

- **双平台支持**：昇腾 10 款 + Jetson 10 款，共 20 款主流 AI 边缘设备
- **健康评分**：0-100 分健康度评估，多维度明细（NPU/GPU 利用率、温度、内存、工具链）
- **推理基准**：MobileNetV2 真实推理延迟测试（ONNX/TensorRT/ACL/MindSpore）
- **统一报告**：Terminal/JSON/HTML/Markdown 多格式输出
- **Jetson 专项**：功耗模式管理、风扇监控、JetPack 版本映射
- **昇腾专项**：npu-smi 详细解析、CANN 版本检测、ACL 可用性检查

## Quick Start

```bash
# 通用诊断（82 项检测）
python3 arm_diagnose.py --quick            # Quick diagnosis (~30s)
python3 arm_diagnose.py --full             # Full diagnosis
python3 arm_diagnose.py --fix              # Interactive fix recommendations

# hw-jet 专项诊断（昇腾/Jetson）
python -m adapters.hw_jet                  # 自动检测设备
python -m adapters.hw_jet --device ascend  # 强制昇腾
python -m adapters.hw_jet --device jetson  # 强制 Jetson
python -m adapters.hw_jet --mock atlas_200i_a2 --json  # Mock 测试
python -m adapters.hw_jet --full --benchmark --output report.html
```

## Supported Devices

### 昇腾（Ascend）- 4 类 10 款

| 系列 | 型号 | 算力 |
|------|------|------|
| Atlas 200系 | 200I A2 / 200DK A2 / 200一代 | 22-88 TOPS |
| Atlas 300系 | 300I Pro / Duo / 300V / 300I 寿光卡 | 256-512 TOPS |
| Atlas 500系 | 500 A2 | 88 TOPS |
| Atlas A2 Lite | A2 智能小站 / A2 边缘计算网关 | 88 TOPS |

### Jetson - 6 类 10 款

| 系列 | 型号 | 算力 | GPU 架构 |
|------|------|------|---------|
| Orin AGX | 64GB / 32GB | 170-275 TOPS | Ada Lovelace |
| Orin NX | 16GB / 8GB | 70-100 TOPS | Ada Lovelace |
| Orin Nano | 8GB / 4GB | 20-40 TOPS | Ada Lovelace |
| AGX Xavier | 64GB / 32GB | 11 TOPS | Volta |
| Xavier NX | - | 6 TOPS | Volta |
| Nano/TX2 | Nano 4GB / TX2 | 1-1.3 TOPS | Maxwell/Pascal |

## Features

| 功能 | 说明 |
|------|------|
| 设备自动识别 | tegrastats / npu-smi 解析，自动识别型号 |
| 健康评分 | NPU/GPU 利用率(25%) + 温度(25%) + 内存(25%) + 工具链(25%) |
| 推理基准 | ONNX Runtime / TensorRT / ACL / MindSpore / Heuristic |
| 报告格式 | Terminal / JSON / HTML / Markdown |
| 错误系统 | 1000-1999 错误码，结构化异常 |

## Test Coverage

```
38 tests passed
├── Unit Tests (21)
│   ├── AdapterResult (5)
│   ├── AdapterError (2)
│   ├── MockAdapter (5)
│   ├── Reporter (5)
│   ├── Benchmark (2)
│   └── ErrorCode (2)
└── Integration Tests (17)
    ├── Ascend Integration (5)
    ├── Jetson Integration (5)
    ├── CLI Integration (2)
    ├── Error Handling (2)
    ├── Benchmark Integration (1)
    └── Report Generation (2)
```

## License

MIT License

## 90 Diagnostic Checks

| Category | Checks | Count |
|----------|--------|-------|
| **System** | Python, pip, system libs, memory, disk, CPU temp, uptime, Docker, cron, process count, kernel, package updates, system logs | 14 |
| **Network** | Internet, DNS, latency, bandwidth, NIC speed, port conflict, proxy, route, MTU, WiFi, NAS backend, DNS cache, DNS coverage | 14 |
| **Storage** | Disk space, write speed, SMART health, HDD temp, RAID, Docker images, IO wait, inodes, path existence, ZFS health, storage trend | 11 |
| **AI/GPU** | GPU detection, memory, utilization, CUDA, cuDNN, TensorFlow, PyTorch, ONNX, OpenVINO, PaddlePaddle, Keras, Triton, TorchServe, TF Serving, KubeFlow, MLflow, NVIDIA container, model format | 18 |
| **Security** | Firewall, SELinux, SSH root, SSH config, SSL cert, OpenSSL, login failures, port scan, fail2ban, clamav | 11 |
| **NAS** | DSM version, user stats, shared perms, UPS, log disk, cron conflicts, SMB/SFTP/FTP/WebDAV/SNMP/NFS/AFP services, media scanner, NAS temp, backup status | 16 |
| **USB** | Device list, storage mount, permissions, power health | 4 |
| **Core** | Registry, base | 2 |

## 18 Auto-Fixes

| Category | Fix | Risk |
|----------|-----|------|
| **System** | `install_python` — Auto-install Python 3.8+ | Low |
| **System** | `install_docker` — Install Docker engine | Low |
| **System** | `check_versions` — Check system package versions | Low |
| **System** | `setup_logrotate` — Configure log rotation | Low |
| **Network** | `config_dns` — Set DNS to 8.8.8.8 + 223.5.5.5 | Low |
| **Storage** | `create_paths` — Create missing directories | Low |
| **Storage** | `cleanup_logs` — Clean old log files | Medium |
| **Storage** | `cleanup_docker_images` — Remove dangling images | Medium |
| **Storage** | `cleanup_tmp_space` — Clean temp files | Medium |
| **Storage** | `config_raid_recovery` — RAID recovery guidance | High |
| **AI** | `install_cuda` — Install/upgrade CUDA | Medium |
| **Security** | `disable_root_login` — Disable SSH root login | Medium |
| **Security** | `enable_fail2ban` — Install fail2ban | Medium |
| **Security** | `enforce_password_policy` — Lock weak passwords | Medium |
| **Security** | `renew_ssl_cert` — Renew SSL certificates | Medium |
| **NAS** | `config_ups_shutdown` — Configure UPS auto-shutdown | Medium |

## Health Score System

```
    🌟 Excellent
    92 /100   Grade: A
    [████████████████░░░░░░░░░░░░░░░░░░░░░░░░░]
      ✅ 85 通过  ⚠️ 4 警告  ❌ 1 严重  ℹ️ 0 信息

  📊 分类评分
    存储     [██████████████░░░░░]  85/100
    系统     [████████████████]  100/100
    网络     [███████████████░░░]   90/100
    安全     [██████░░░░░░░░░░░░]   50/100  ❌1
    AI       [███████████████░░░]   90/100
    NAS      [████████████████░░]   95/100
    USB      [████████████████]  100/100
```

## 7 Reporters

| Reporter | Description |
|----------|-------------|
| `TerminalReporter` | Colored terminal output with progress bars |
| `SummaryReporter` | One-line summary for scripts |
| `HealthDashboard` | Colorful health score dashboard |
| `FriendlyReporter` | Plain-language reports for non-technical users |
| `FileReporter` | Save to JSON / HTML / Markdown / CSV |
| `JSONReporter` | Structured JSON output |
| `HTMLReporter` | Styled HTML report with charts |

## Supported Chips (60+)

NVIDIA Jetson, Rockchip RK3588/3568, Huawei Ascend, Intel NPU,
Sophgo BM1684, Amlogic S905, Realtek RTD1619B, Annapurna Labs AL-314,
Apple Silicon, Qualcomm Snapdragon, MediaTek Dimensity, Phytium, Kunpeng

## Supported Devices (51+)

Synology (13), Jetson (9), SOPHON (12), RK3588 (6),
QNAP (5), Asustor (3), TerraMaster (2), Raspberry Pi, Orange Pi, Rock ITX

## Stats

| Metric | Value |
|--------|-------|
| Version | 5.0.4 |
| Python Files | 223 |
| Lines of Code | 40,087 |
| Checks | 90 |
| Fixes | 18 |
| Reporters | 7 |
| Supported Chips | 60+ |
| Device Profiles | 51+ |

## Requirements

- Python 3.8+
- pyyaml

## Links

- **GitHub**: https://github.com/leon2397/qizhiainas/tree/main/arm/nastool
- **Issues**: https://github.com/leon2397/qizhiainas/issues


---

## nastools — Windows GUI (v2.0)

> nastools = nastool + tools，Windows 端的 GUI 封装工具

### 版本路线图

| 版本 | 状态 | 说明 |
|------|------|------|
| v1.0 | ✅ 已发布 | SSH 检测 + 部署 |
| **v2.0** | **✅ 已发布** | **Relay Server + 跨网远程管理** |
| v2.x | 📋 规划中 | 多设备 + 微信通知 |

### nastools v2.0 架构

```
┌─────────────────────────────────────────────────────────┐
│  nastools GUI (Windows)                                │
│  ├─ 局域网模式：直连 NAS（SSH）                         │
│  └─ 跨网模式：通过 Relay Server 远程管理                │
└─────────────────────────────────────────────────────────┘
           ↕ WebSocket                 ↕ WebSocket
┌──────────────────────┐    ┌──────────────────────────┐
│   Relay Server       │    │   ARM Agent              │
│   (ECS:18888)       │ ←──│   (NAS 守护进程)          │
│   ├─ REST API       │    │   ├─ 检测上报             │
│   ├─ WS Agent 路由  │    │   ├─ 命令执行             │
│   └─ WS GUI 路由    │    │   └─ 文件传输             │
└──────────────────────┘    └──────────────────────────┘
```

### 功能清单

- ✅ SSH 自动连接（IP/用户名/密码）
- ✅ 90 项自动检测（系统/网络/存储/AI/安全/NAS/USB）
- ✅ 18 种一键修复（含智能推荐交互）
- ✅ WebSocket 跨网远程管理
- ✅ 远程命令执行
- ✅ 文件传输（上传/下载）
- ✅ 远程部署 AI-NAS
- ✅ 多设备批量操作
- ✅ 健康趋势图 + CSV 导出
- ✅ 离线可用
- ✅ 深色科技风 UI

### 技术特点

- tkinter（Python 内置，零额外依赖）
- 原生 threading（无 multiprocessing）
- 嵌入式脚本（无外部文件依赖）
- 单进程，内存 < 70 MB
