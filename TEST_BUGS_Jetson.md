# Jetson Xavier NX 真机测试 - BUG 记录

> 测试日期：2026-04-16
> 测试设备：Jetson Xavier NX (192.168.1.123)
> 测试版本：nastool v5.0.4 / v7.0.0-beta
> 测试人员：桔子2 + AI Agent

---

## 测试原则

**测试过程中发现 BUG，必须先记录，不得边测边修。**

记录格式：
- BUG-XXX: [标题]
- 发现时间：YYYY-MM-DD HH:MM
- 测试项：xxx
- 现象：xxx
- 预期行为：xxx
- 实际行为：xxx
- 复现步骤：xxx
- 优先级：P0/P1/P2/P3
- 备注：xxx

---

## BUG 列表

### BUG-002: Jetson 部署版本落后（86 vs 93 checks）
- 发现时间：2026-04-16 11:14
- 测试项：T5 AI checks 测试
- 现象：Jetson 上只有 86 checks，本地已 93 checks；`gpu_detected` 无法导入 `check` 函数
- 预期行为：Jetson 应部署最新版本（93 checks，@check() 装饰器形式）
- 实际行为：Jetson 上是 Apr 15 部署的旧版本（86 checks，class 形式）
- 复现步骤：`python3 ~/test_ai.py` 检查 registry
- 优先级：P2（部署同步问题）
- 备注：需要在测试后同步最新代码到 Jetson

### BUG-003: gpu_detected 在 Jetson 上无法导入 check 函数
- 发现时间：2026-04-16 11:14
- 测试项：T5 AI checks 测试
- 现象：`cannot import name 'check' from 'checks.ai.gpu_detected'`
- 预期行为：应能导入 `check` 函数并调用
- 实际行为：ImportError - Jetson 上是旧版 class 形式
- 复现步骤：`from checks.ai.gpu_detected import check`
- 优先级：P2（依赖 BUG-002 修复）
- 备注：同步最新代码后应自动修复

### BUG-004: Jetson 缺少专用检查模块（jetpack_version, tensorrt_version）
- 发现时间：2026-04-16 11:16
- 测试项：T7 CUDA/JetPack/TensorRT 检查
- 现象：Jetson 上没有 `cuda_version`, `jetpack_version`, `tensorrt_version` 模块
- 预期行为：Jetson 应有专用检查模块检测 JetPack、TensorRT 等版本
- 实际行为：`No module named 'checks.ai.cuda_version'` 等错误
- 复现步骤：`from checks.ai.jetpack_version import JetPackVersionCheck`
- 优先级：P1（Jetson 核心功能缺失）
- 备注：本地新版已包含这些模块，需同步到 Jetson

### BUG-005: GPU Detected 检查返回 "No AI accelerator detected"
- 发现时间：2026-04-16 11:16
- 测试项：T7 GPU 检测
- 现象：Jetson 有 GPU（CUDA 11.4 可用），但 gpu_detected 检查返回 "No AI accelerator detected"
- 预期行为：应检测到 Jetson GPU 并返回正确的 GPU 信息
- 实际行为：passed=True 但 message 说没有检测到 AI 加速器
- 复现步骤：GPUDetectedCheck().run()
- 优先级：P1（核心检测功能错误）
- 备注：可能是旧版 gpu_detected 逻辑不支持 Jetson（无 nvidia-smi）

### BUG-006: Jetson 检查模块类名与本地不一致
- 发现时间：2026-04-16 11:18
- 测试项：T9 正确模块名测试
- 现象：`CpuTempCheck`, `SystemDiskCheck`, `StorageDiskCheck` 无法从对应模块导入
- 预期行为：类名应一致，能够正确导入
- 实际行为：ImportError - Jetson 上的类名可能是 `Check` 而不是具体类名
- 复现步骤：`from checks.system.cpu_temp import CpuTempCheck`
- 优先级：P2（命名一致性问题）
- 备注：本地新版使用 @check() 装饰器，Jetson旧版使用 class 形式，命名不同

### BUG-007: HTML 报告未生成
- 发现时间：2026-04-16 11:22
- 测试项：T11 报告生成
- 现象：`--quick --output /tmp/test_report.html --format html` 执行后，文件不存在
- 预期行为：应生成 HTML 报告文件
- 实际行为：`ls: cannot access '/tmp/test_report.html': No such file or directory`
- 复现步骤：`python3 arm_diagnose.py --quick --output /tmp/test_report.html --format html`
- 优先级：P1（报告功能缺失）
- 备注：可能是 reporters 模块问题，或输出路径处理逻辑问题

---

## 测试统计

- 测试时间：2026-04-16 11:04 - 11:22（约18分钟）
- 发现 BUG：7 个
- P1 级别：4 个（BUG-001, BUG-004, BUG-005, BUG-007）
- P2 级别：3 个（BUG-002, BUG-003, BUG-006）
- 发现时间：2026-04-16 11:10
- 测试项：T3 --quick 模式
- 现象：`--quick` 输出显示 "Passed: 0/0" 和 "Score: 0/100"，但应该有 6 个检查
- 预期行为：应显示 "Passed: 6/6" 或正确的检查结果统计
- 实际行为：`Passed: 0/0`, `Score: 0/100`, `OK Status: HEALTHY`
- 复现步骤：`python3 arm_diagnose.py --quick`
- 优先级：P1
- 备注：可能是 quick_diagnose 返回值统计逻辑问题，或 CheckSummary 格式问题