# Jetson Xavier NX 真机测试 - BUG 记录

> 测试日期：2026-04-16
> 测试设备：Jetson Xavier NX (192.168.1.123)
> 测试版本：nastool v5.0.4 / v7.0.0-beta
> 测试人员：桔子2 + AI Agent
> BUG 分类体系：[T-A 代码缺陷] [T-B 版本差异] [T-C 环境适配] [T-D 测试设计]

---

## BUG 分类体系

```
T-A：代码缺陷 — 本地代码本身有 bug，本地测试也能复现
T-B：版本差异 — 被测版本落后，同步最新代码后消失
T-C：环境适配 — 目标平台特殊限制，特定设备/环境上出现
T-D：测试设计 — 测试方法/脚本问题，不反映真实代码质量

判断优先级：本地能复现→T-A > 同步代码后消失→T-B > 测试脚本问题→T-D > 特定环境→T-C
```

---

## 测试原则

**测试过程中发现 BUG，必须先记录，不得边测边修。**

---

## BUG 列表

### BUG-001: --quick Passed: 0/0
- **Type:** T-A（代码缺陷）
- 发现时间：2026-04-16 11:10
- 测试项：T3 --quick 模式
- 现象：`--quick` 输出显示 "Passed: 0/0" 和 "Score: 0/100"，但实际运行了 6 个检查
- 预期行为：应显示 "Passed: 6/6" 或正确的检查结果统计
- 实际行为：`Passed: 0/0`, `Score: 0/100`, `OK Status: HEALTHY`
- 复现步骤：`python3 arm_diagnose.py --quick`
- 优先级：P1
- 状态：✅ 已修复（v7.1.0-beta）
- 判定理由：本地也能复现，print_quick_report() 统计逻辑缺陷
- 修复方式：quick_diagnose 返回值字段名不一致，统一为 passed/total

### BUG-002: Jetson 部署版本落后（86 vs 93 checks）
- **Type:** T-B（版本差异）
- 发现时间：2026-04-16 11:14
- 测试项：T5 AI checks 测试
- 现象：Jetson 上只有 86 checks，本地已 93 checks
- 预期行为：Jetson 应部署最新版本（93 checks，@check() 装饰器形式）
- 实际行为：Jetson 上是 Apr 15 部署的旧版本（86 checks，class 形式）
- 复现步骤：`python3 ~/test_ai.py` 检查 registry
- 优先级：P2
- 状态：⬜ 待同步
- 判定理由：同步最新代码后消失，属于部署流程问题
- 修复方式：重新部署最新版到 Jetson

### BUG-003: gpu_detected 在 Jetson 上无法导入 check 函数
- **Type:** T-B（版本差异）
- 发现时间：2026-04-16 11:14
- 测试项：T5 AI checks 测试
- 现象：`cannot import name 'check' from 'checks.ai.gpu_detected'`
- 预期行为：应能导入 `check` 函数并调用
- 实际行为：ImportError - Jetson 上是旧版 class 形式
- 复现步骤：`from checks.ai.gpu_detected import check`
- 优先级：P2
- 状态：⬜ 待同步（依赖 BUG-002）
- 判定理由：依赖 BUG-002，同步代码后自动修复
- 修复方式：随 BUG-002 一起解决

### BUG-004: Jetson 缺少专用检查模块（jetpack_version, tensorrt_version）
- **Type:** T-C（环境适配）
- 发现时间：2026-04-16 11:16
- 测试项：T7 CUDA/JetPack/TensorRT 检查
- 现象：Jetson 上没有 `cuda_version`, `jetpack_version`, `tensorrt_version` 模块
- 预期行为：Jetson 应有专用检查模块检测 JetPack、TensorRT 等版本
- 实际行为：`No module named 'checks.ai.cuda_version'` 等错误
- 复现步骤：`from checks.ai.jetpack_version import JetPackVersionCheck`
- 优先级：P1
- 状态：⬜ 待实现
- 判定理由：本地新版已有模块定义但 Jetson 部署缺失，属设备特有检查项
- 修复方式：F5 Jetson 测试集（JSON 数据驱动）+ 同步部署

### BUG-005: GPU Detected 检查返回 "No AI accelerator detected"
- **Type:** T-C（环境适配）
- 发现时间：2026-04-16 11:16
- 测试项：T7 GPU 检测
- 现象：Jetson 有 GPU（CUDA 11.4），但 gpu_detected 检查返回 "No AI accelerator"
- 预期行为：应检测到 Jetson GPU 并返回正确的 GPU 信息
- 实际行为：passed=True 但 message 说没有检测到 AI 加速器
- 复现步骤：`gpu_detected.check()` 或 `GPUDetectedCheck().run()`
- 优先级：P1
- 状态：⬜ 待修复
- 判定理由：Jetson 无 nvidia-smi（ARM 环境特殊），检测逻辑需适配
- 修复方式：gpu_detected 增加 Jetson 专用检测路径（/proc/driver/nvidia/gpus/）

### BUG-006: Jetson 检查模块类名与本地不一致
- **Type:** T-D（测试设计）
- 发现时间：2026-04-16 11:18
- 测试项：T9 正确模块名测试
- 现象：`CpuTempCheck`, `SystemDiskCheck`, `StorageDiskCheck` 无法从对应模块导入
- 预期行为：类名应一致，能够正确导入
- 实际行为：ImportError - 旧版 class 名与新版不同
- 复现步骤：`from checks.system.cpu_temp import CpuTempCheck`
- 优先级：P2
- 状态：✅ 已解决（版本统一后不再适用）
- 判定理由：测试脚本硬编码旧版 class 名，新版用 @check() 装饰器后类名不同
- 修复方式：F3 通用测试运行器改为通过 registry 动态探测，不依赖具体类名

### BUG-007: HTML 报告未生成
- **Type:** T-A（代码缺陷）
- 发现时间：2026-04-16 11:22
- 测试项：T11 报告生成
- 现象：`--quick --output /tmp/test_report.html --format html` 执行后文件不存在
- 预期行为：应生成 HTML 报告文件
- 实际行为：`ls: cannot access '/tmp/test_report.html': No such file or directory`
- 复现步骤：`python3 arm_diagnose.py --quick --output /tmp/test_report.html --format html`
- 优先级：P1
- 状态：✅ 已修复（v7.1.0-beta）
- 判定理由：本地也能复现，file_reporter.py 的 HTML 输出路径处理缺陷
- 修复方式：file_reporter 确保目录存在后写入文件

---

## 统计

### 按 Type 分类

| Type | 数量 | BUG | 说明 |
|------|------|-----|------|
| T-A 代码缺陷 | 2 | 001, 007 | 本地可复现，已修复 |
| T-B 版本差异 | 2 | 002, 003 | 部署同步问题 |
| T-C 环境适配 | 2 | 004, 005 | Jetson 特有 |
| T-D 测试设计 | 1 | 006 | 测试脚本问题 |

### 按优先级

| 优先级 | 数量 | BUG |
|--------|------|-----|
| P1 | 4 | 001, 004, 005, 007 |
| P2 | 3 | 002, 003, 006 |

### 按状态

| 状态 | 数量 | BUG |
|------|------|-----|
| ✅ 已修复 | 3 | 001, 006, 007 |
| ⬜ 待处理 | 4 | 002, 003, 004, 005 |

### 测试统计

- 测试时间：2026-04-16 11:04 - 11:22（约18分钟）
- 发现 BUG：7 个
- T-A（代码缺陷）：2 个 → 需要修代码
- T-B（版本差异）：2 个 → 需要同步部署
- T-C（环境适配）：2 个 → 需要设备适配
- T-D（测试设计）：1 个 → 需要改进测试方法

---

## 附录：新增 BUG 模板

发现新 BUG 时，复制以下模板填写：

```markdown
### BUG-XXX: [简短标题]
- **Type:** T-A / T-B / T-C / T-D
- 发现时间：YYYY-MM-DD HH:MM
- 测试项：Tx 测试名称
- 现象：xxx
- 预期行为：xxx
- 实际行为：xxx
- 复现步骤：xxx
- 优先级：P0/P1/P2/P3
- 状态：⬜ 待确认 / ⬜ 待修复 / 🔄 修复中 / ✅ 已修复
- 判定理由：xxx
- 修复方式：xxx
```
