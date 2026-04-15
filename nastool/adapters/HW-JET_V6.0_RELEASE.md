# hw-jet v6.0 - 昇腾 + Jetson AI 边缘诊断专业版

**版本号**: v6.0-hwjet  
**发布日期**: 2026-04-15（计划）  
**真机验证**: 昇腾 ✅ + Jetson Xavier NX ✅

---

## 产品定位

专为华为昇腾和 NVIDIA Jetson 双平台设计的 AI 边缘设备诊断工具，提供：
- **设备自动识别**：支持 10 类设备，覆盖 20+ 主流型号
- **健康状态评分**：0-100 分健康度评估，多维度明细
- **推理性能基准**：真实 MobileNetV2 推理延迟测试
- **统一诊断报告**：Terminal/JSON/HTML/Markdown 多格式输出

---

## 支持设备

### 昇腾（Ascend）- 4 类 10 款

| 系列 | 型号 | 算力 | 典型功耗 |
|------|------|------|---------|
| **Atlas 200系** | 200I A2 | 88 TOPS | 20W |
| | 200DK A2 | 88 TOPS | 20W |
| | 200 一代 | 22 TOPS | 8W |
| **Atlas 300系** | 300I Pro | 256 TOPS | 310W |
| | 300I Duo | 512 TOPS | 350W |
| | 300V 寿光卡 | 256 TOPS | 310W |
| | 300I 寿光卡 | 256 TOPS | 310W |
| **Atlas 500系** | 500 A2 | 88 TOPS | 20W |
| **Atlas A2 Lite** | A2 智能小站 | 88 TOPS | 20W |
| | A2 边缘计算网关 | 88 TOPS | 20W |

### Jetson - 6 类 10 款

| 系列 | 型号 | 算力 | GPU 架构 |
|------|------|------|---------|
| **Orin AGX** | 64GB | 275 TOPS | Ada Lovelace |
| | 32GB | 170 TOPS | Ada Lovelace |
| **Orin NX** | 16GB | 100 TOPS | Ada Lovelace |
| | 8GB | 70 TOPS | Ada Lovelace |
| **Orin Nano** | 8GB | 40 TOPS | Ada Lovelace |
| | 4GB | 20 TOPS | Ada Lovelace |
| **AGX Xavier** | 64GB | 11 TOPS | Volta |
| | 32GB | 11 TOPS | Volta |
| **Xavier NX** | - | 6 TOPS | Volta |
| **Nano/TX2** | Nano 4GB | 1 TOPS | Maxwell |
| | TX2 | 1.3 TOPS | Pascal |

---

## 功能特性

### 1. 设备自动识别

```bash
# 自动检测
python -m adapters.hw_jet

# 强制指定平台
python -m adapters.hw_jet --device ascend
python -m adapters.hw_jet --device jetson
```

### 2. 健康状态评分

评分维度（各 25 分，满分 100）：
- **NPU/GPU 利用率**
- **温度状态**
- **内存使用**
- **工具链完整度**

### 3. 推理性能基准

测试模型：MobileNetV2 (224x224)

| 框架 | 平台 | 典型延迟 |
|------|------|---------|
| TensorRT | Jetson Orin | 5-10 ms |
| ACL | 昇腾 910B | 3-8 ms |
| ONNX Runtime CUDA | Jetson | 10-20 ms |
| ONNX Runtime CPU | 通用 | 50-150 ms |
| Heuristic | 兜底估算 | 基于 CPU 核心数 |

### 4. 报告格式

```bash
# 终端输出
python -m adapters.hw_jet --mock atlas_200i_a2

# JSON 报告
python -m adapters.hw_jet --mock atlas_200i_a2 --json

# HTML 报告
python -m adapters.hw_jet --mock atlas_200i_a2 --output report.html

# Markdown 报告
python -m adapters.hw_jet --mock atlas_200i_a2 --output report.md
```

---

## 专项功能

### 昇腾专项

- **npu-smi 解析**：NPU 利用率/温度/功率/内存
- **CANN 版本检测**：自动识别 CANN 版本
- **ACL 可用性检查**：检测 PyACL 安装状态
- **推理基准**：ACL / MindSpore / ONNX Runtime

### Jetson 专项

- **tegrastats 解析**：GPU/CPU/RAM/温度
- **JetPack 版本映射**：JetPack → CUDA/TensorRT 版本对应
- **功耗模式管理**：nvpmodel 模式检测
- **风扇状态监控**：PWM 值/转速/模式
- **推理基准**：TensorRT / ONNX Runtime CUDA/CPU

---

## 安装

```bash
# PyPI 安装（计划）
pip install nastool

# 开发模式
git clone https://github.com/yourrepo/nastool.git
cd nastool
pip install -e .
```

---

## Python API

```python
from adapters.hw_jet import run_hwjet_diagnosis, generate_report
from adapters.ascend import AscendAdapter
from adapters.jetson import JetsonAdapter

# 方式1: CLI 入口
exit_code = run_hwjet_diagnosis(
    device="auto",
    full=True,
    benchmark=True,
    output="report.json",
)

# 方式2: 直接使用适配器
adapter = AscendAdapter()  # 或 JetsonAdapter()
result = adapter.run()

print(f"设备: {result.device_model}")
print(f"评分: {result.score}/100")
print(f"温度: {result.npu_status.get('temperature_c')}°C")
print(f"基准: {result.benchmark.get('latency_ms')} ms")
```

---

## 错误码体系

| 范围 | 类别 |
|------|------|
| 1000-1099 | 设备识别错误 |
| 1100-1199 | 工具链错误 |
| 1200-1299 | NPU 错误 |
| 1250-1299 | GPU 错误 |
| 1300-1399 | 系统错误 |
| 1400-1499 | 基准测试错误 |
| 1900-1999 | 通用错误 |

---

## 测试覆盖

- **单元测试**: 21 用例
- **集成测试**: 17 用例
- **总测试**: 319 passed

```bash
python -m pytest tests/ -v
```

---

## 开发进度

| Day | 任务 | 状态 |
|-----|------|------|
| Day1 | 昇腾核心适配器（4类） | ✅ |
| Day2 | Mock 数据 + 解析器测试 | ✅ |
| Day3-4 | CLI 整合 | ✅ |
| Day5 | 完整检测流程 | ✅ |
| Day6 | 推理基准 + 报告生成器 | ✅ |
| Day7 | 错误处理增强 | ✅ |
| Day8 | 日志系统 + API 文档 | ✅ |
| Day9-10 | 单元测试 + 集成测试 | ✅ |
| Day11-15 | Jetson 全系专项 + 真机验证 | ✅ |

---

## 许可证

MIT License

---

## 联系方式

- 项目主页: https://github.com/yourrepo/nastool
- 问题反馈: https://github.com/yourrepo/nastool/issues
