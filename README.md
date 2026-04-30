# NASTool v4.2

NASTool是一款面向昇腾及边缘AI设备的诊断工具，提供全面的系统检测、网络诊断、硬件诊断和性能评估功能。

## ✨ 主要功能

### 📦 依赖管理优化
- 离线依赖包管理机制，支持跨平台依赖检测和安装
- 统一依赖清单管理，支持核心依赖和可选依赖分离

### 🚀 一键部署
- 支持本地和远程部署
- 自动处理目录结构创建、模块复制、依赖安装
- 生成启动脚本和卸载脚本

### 🔍 环境自检
- Python版本检测
- 系统信息收集
- 兼容性检测
- 网络连接检测
- 依赖完整性检查
- 磁盘空间检测
- AI硬件检测

### 🌐 网络诊断增强
- 网络接口状态检测
- 链路状态检测
- 连接性检测
- ping稳定性检测
- DNS解析诊断
- 网络统计分析
- 带宽测试
- 网络性能指标检测

### 🤖 硬件诊断增强
- 昇腾芯片检测
- CANN版本检测
- 驱动版本检测
- 固件版本检测
- ACL可用性检测
- 设备健康状态检测

### 📊 报告输出优化
- 可视化HTML报告生成
- 诊断摘要统计
- 系统信息展示
- 网络信息展示
- 硬件信息展示
- 依赖信息展示

### ⚡ 测试模式优化
| 模式 | 描述 | 适用场景 |
|------|------|----------|
| `quick` | 快速模式，只运行核心检测项 | 快速获取系统状态 |
| `full` | 完整模式，运行所有检测项 | 全面系统诊断 |
| `network` | 网络专项，专注网络诊断 | 网络问题排查 |
| `hardware` | 硬件专项，专注硬件诊断 | 硬件问题排查 |
| `simulate` | 模拟模式，使用模拟数据 | 功能演示 |

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements-full.txt
```

### 运行快速诊断
```bash
python -c "from nastool_core.quick_diagnose import QuickDiagnose; d = QuickDiagnose('quick'); results = d.run(); print(d.generate_report())"
```

### 使用不同模式
```bash
# 完整模式
python -c "from nastool_core.quick_diagnose import QuickDiagnose; d = QuickDiagnose('full'); d.run()"

# 网络专项
python -c "from nastool_core.quick_diagnose import QuickDiagnose; d = QuickDiagnose('network'); d.run()"

# 硬件专项
python -c "from nastool_core.quick_diagnose import QuickDiagnose; d = QuickDiagnose('hardware'); d.run()"

# 模拟模式
python -c "from nastool_core.quick_diagnose import QuickDiagnose; d = QuickDiagnose('simulate'); d.run()"
```

## 📁 项目结构

```
nastool7/
├── nastool-common/          # 公共工具模块
│   └── nastool_common/
│       └── utils/
│           ├── offline_deps.py    # 离线依赖包管理器
│           ├── env_checker.py     # 环境自检模块
│           └── progress.py        # 进度可视化模块
├── nastool-core/             # 核心检测模块
│   └── nastool_core/
│       ├── checks/
│       │   ├── network/           # 网络诊断模块
│       │   └── ai/ascend_checker.py  # 昇腾芯片检测
│       └── quick_diagnose.py      # 快速诊断模块
├── nastool-reporters/        # 报告输出模块
│   └── nastool_reporters/
│       └── html_reporter.py       # HTML报告生成器
├── deploy_v4.2.py            # 一键部署脚本
└── requirements-full.txt     # 完整依赖清单
```

## 🛠️ 模块说明

### QuickDiagnose (快速诊断)
支持多种诊断模式，提供快速、完整、专项等不同级别的检测能力。

### NetworkStatusChecker (网络状态检测)
检测网络接口、链路状态、连接性、ping稳定性、DNS解析和网络统计。

### NetworkQualityChecker (网络质量检测)
评估网络带宽、稳定性、TCP连接和网络性能指标。

### DNSDiagnostic (DNS诊断)
检测DNS配置、服务器可用性、缓存和解析延迟。

### AscendChecker (昇腾芯片检测)
检测昇腾硬件、CANN版本、驱动版本、固件版本、ACL可用性和设备健康状态。

### HTMLReporter (HTML报告生成)
生成可视化的诊断报告，包含诊断摘要、系统信息、网络信息、硬件信息和依赖信息。

### Progress (进度可视化)
提供美观的进度条显示，支持任务状态跟踪和时间统计。

## 📝 版本历史

### v4.2.0
- ✅ 依赖管理优化：创建离线依赖包机制
- ✅ 部署流程优化：实现一键部署脚本
- ✅ 环境自检：添加设备兼容性检测
- ✅ 网络诊断增强：添加网络断网检测功能
- ✅ 硬件诊断增强：添加昇腾芯片检测模块
- ✅ 报告输出优化：实现可视化HTML报告
- ✅ 测试模式优化：添加快速诊断模式
- ✅ 用户体验优化：添加进度可视化

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

*NASTool - 让AI设备诊断更简单*
