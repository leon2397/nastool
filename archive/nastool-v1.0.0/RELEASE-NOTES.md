# NASTool v1.0.0 Release Notes

> 发布日期：2026-04-19

---

## 概述

NASTool v1.0.0 是首个正式版本，提供完整的 ARM/NAS 设备诊断能力。支持 90 项自动化检测、4 种 Mock 模式、交互式修复、多格式报告输出和 GUI 可视化界面。

---

## 新增功能

### 检测引擎
- 90 项自动化检测，覆盖 6 大类别
  - AI 环境（24 项）：NVIDIA 驱动、CUDA、TensorRT、PyTorch、ONNX、GPU 内存等
  - NAS 服务（16 项）：SMB/NFS/FTP/SFTP/WebDAF、UPS、备份、RAID 等
  - 网络（13 项）：互联网、DNS、带宽、延迟、MTU、代理等
  - 安全（11 项）：防火墙、SSH、SSL 证书、Fail2ban、ClamAV 等
  - 存储（11 项）：磁盘空间、SMART、RAID、ZFS、IO 等待等
  - 系统（15 项）：Python、Docker、内存、CPU 温度、内核版本等

### Mock 模式
- `healthy`：健康设备（96 分），89 项通过
- `degraded`：降级设备（87 分），81 项通过
- `critical`：严重故障（58 分），74 项通过
- `mixed`：混合场景（70 分），56 项通过

### 命令行界面（CLI）
- 快速诊断：`nastool`（89 项）
- 完整诊断：`nastool --full`（93 项，含基准测试）
- 交互式修复：`nastool --fix`
- 自动修复：`nastool --fix-auto`
- JSON 输出：`nastool --json`
- 文件导出：`nastool --output report.txt`
- 无颜色输出：`nastool --no-color`

### 图形界面（GUI）
- customtkinter 跨平台 GUI
- 检测结果表格展示
- 设备健康评分面板
- 分类统计面板
- Mock 模式选择
- 报告导出功能

### 适配器
- 11 种设备适配器（Mock/SSH/USB/Synology/QNAP/Jetson/Rockchip/Sophon/ADB/Generic/HTTP）

### 报告格式
- 终端彩色输出（自动处理 Windows GBK 编码）
- JSON 报告
- 文本报告
- HTML 报告
- PDF 报告
- Markdown 报告
- 友好版报告
- 健康仪表盘

---

## 模块化架构

v1.0.0 采用完全模块化设计，6 个独立 Python 包 + 1 个 GUI 包：

| 模块 | 版本 | 说明 |
|------|------|------|
| nastool-common | 1.0.0 | 公共工具（零外部依赖） |
| nastool-core | 1.0.0 | 检测引擎 |
| nastool-adapters | 1.0.0 | 设备适配器 |
| nastool-reporters | 1.0.0 | 报告输出 |
| nastool-fixes | 1.0.0 | 修复模块 |
| nastool-cli | 1.0.0 | 命令行入口 |
| nastool-gui | 1.0.0 | 图形界面 |

单向依赖链：`cli → fixes/reporters/adapters → core → common`

---

## 测试

- 53 项单元测试，100% 通过
- 8 项 CLI 链路测试，全部通过
- 4 种 Mock Profile 验证通过
- GUI 启动和数据填充验证通过

---

## 已知问题

| 问题 | 严重度 | 说明 |
|------|--------|------|
| `--category` 参数无过滤逻辑 | 低 | 参数已声明但未实现过滤，不影响其他功能 |
| 无真机测试验证 | 中 | 93 项检测仅通过 Mock 数据验证，真实设备行为待确认 |
| fix_engine.py / fix_engine_v2.py 遗留 | 低 | 两个文件未被使用，`--fix` 走 interactive_fix.py |
| 无远程 Git 仓库 | 低 | 仅本地版本管理 |
| nastool-meta pip 安装顺序问题 | 中 | `setup.py` 的 `install_requires` 引用本地包名，pip 无法从 PyPI 找到 |

---

## 升级说明

本版本为首个正式版，无需升级。

### 从旧版单体项目迁移

旧版 `nastool/`（v7.1.0-beta）已废弃，详见 `nastool/DEPRECATED.md`。新模块化版本完全替代旧版，API 不兼容。

---

## 致谢

NASTool v1.0.0 由橘子8 指导开发，梨子7 🍐 实现。
