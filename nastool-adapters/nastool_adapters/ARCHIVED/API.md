# hw-jet v6.0 API 文档

## CLI 入口

```bash
python -m adapters.hw_jet [OPTIONS]
```

### 参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--device` | `-d` | 设备类型 (auto/ascend/jetson) | auto |
| `--full` | `-f` | 完整诊断（含系统检测） | false |
| `--benchmark` | `-b` | 运行推理基准测试 | false |
| `--output` | `-o` | 报告输出路径 | - |
| `--format` | - | 报告格式 (terminal/json/html/md) | terminal |
| `--json` | - | JSON 输出到 stdout | false |
| `--mock` | `-m` | Mock 设备名称 | - |
| `--version` | `-v` | 显示版本号 | - |

### 示例

```bash
# 自动检测
python -m adapters.hw_jet

# 强制昇腾检测
python -m adapters.hw_jet --device ascend

# 完整诊断 + 基准测试 + HTML 报告
python -m adapters.hw_jet --full --benchmark --output report.html

# Mock 测试
python -m adapters.hw_jet --mock atlas_200i_a2 --json
```

---

## Python API

### 检测入口

```python
from adapters.hw_jet import run_hwjet_diagnosis, generate_report, save_report

# 执行诊断
exit_code = run_hwjet_diagnosis(
    device="auto",      # auto/ascend/jetson
    full=True,          # 完整检测
    benchmark=True,     # 基准测试
    output="report.json",
    json_output=False,
    mock=None,          # Mock 设备名
)

# 生成报告
report = generate_report(adapter, format="json")
save_report(adapter, "report.html", format="html")
```

### 适配器 API

```python
from adapters.ascend.common import AscendAdapter
from adapters.jetson.common import JetsonAdapter

# 昇腾检测
adapter = AscendAdapter(device_family="Atlas 200系")
result = adapter.run()

# 结果访问
print(result.device_family)    # "Atlas 200系"
print(result.device_model)     # "Atlas 200I A2"
print(result.score)            # 0-100
print(result.npu_status)       # {"utilization": 45, "temperature": 62, ...}
print(result.benchmark)        # {"latency_ms": 5.2, "throughput_fps": 192.3, ...}
print(result.errors)           # [AdapterError(...), ...]
```

### 报告生成器

```python
from adapters.reporter import Reporter

reporter = Reporter(adapter.result)

# 终端输出
print(reporter.generate_terminal())

# JSON 报告
json_report = reporter.generate_json()

# HTML 报告
html_report = reporter.generate_html()

# Markdown 报告
md_report = reporter.generate_markdown()

# 保存到文件
reporter.save("report.json", format="json")
reporter.save("report.html", format="html")
reporter.save("report.md", format="md")
```

### 基准测试

```python
from adapters.benchmark import (
    run_onnx_benchmark,
    run_tensorrt_benchmark,
    run_acl_benchmark,
    run_mindspore_benchmark,
    run_heuristic_benchmark,
)

# ONNX Runtime
result = run_onnx_benchmark(
    model_name="mobilenetv2",
    warmup=3,
    iterations=10,
    provider="CUDAExecutionProvider",
)

# TensorRT
result = run_tensorrt_benchmark(
    model_name="mobilenetv2",
    warmup=3,
    iterations=10,
)

# ACL（昇腾）
result = run_acl_benchmark(
    model_name="mobilenetv2",
    warmup=3,
    iterations=10,
)

# MindSpore
result = run_mindspore_benchmark(
    model_name="mobilenetv2",
    device_target="Ascend",
)

# 启发式估算
result = run_heuristic_benchmark()
```

---

## 错误码

| 范围 | 类别 |
|------|------|
| 1000-1099 | 设备识别错误 |
| 1100-1199 | 工具链错误 |
| 1200-1299 | NPU 错误 |
| 1250-1299 | GPU 错误 |
| 1300-1399 | 系统错误 |
| 1400-1499 | 基准测试错误 |
| 1900-1999 | 通用错误 |

### 常见错误码

| 错误码 | 名称 | 说明 |
|--------|------|------|
| 1000 | DEVICE_NOT_FOUND | 未检测到设备 |
| 1001 | DEVICE_UNKNOWN | 无法识别设备型号 |
| 1002 | DEVICE_UNSUPPORTED | 设备不受支持 |
| 1100 | TOOL_NOT_FOUND | 工具未安装 |
| 1200 | NPU_NOT_DETECTED | NPU 未检测到 |
| 1250 | GPU_NOT_DETECTED | GPU 未检测到 |
| 1300 | SYSTEM_MEMORY_LOW | 系统内存不足 |
| 1400 | BENCHMARK_MODEL_NOT_FOUND | 基准模型文件不存在 |
| 1900 | UNKNOWN_ERROR | 未知错误 |
| 1901 | PERMISSION_DENIED | 权限不足 |
| 1902 | TIMEOUT | 操作超时 |

---

## 数据结构

### AdapterResult

```python
@dataclass
class AdapterResult:
    device_type: str           # "ascend" / "jetson"
    device_family: str         # "Atlas 200系" / "Orin AGX"
    device_model: str          # "Atlas 200I A2"
    device_id: str             # 唯一标识符
    
    tools: dict[str, bool]     # 工具链状态
    npu_status: dict           # NPU 状态
    gpu_status: dict           # GPU 状态
    system: dict               # 系统状态
    benchmark: dict            # 基准结果
    
    score: int                 # 0-100
    score_breakdown: dict      # 评分明细
    
    errors: list[AdapterError] # 错误列表
    warnings: list[str]        # 警告列表
    elapsed_seconds: float     # 执行时间
```

### AdapterError

```python
@dataclass
class AdapterError:
    code: ErrorCode       # 错误码枚举
    message: str          # 错误消息
    details: str | None   # 详细信息
    timestamp: str        # 时间戳
```

---

## Mock 设备

支持的 Mock 设备名称：

### 昇腾（Ascend）

- `atlas_200i_a2` - Atlas 200I A2
- `atlas_200dk_a2` - Atlas 200DK A2
- `atlas_300i_pro` - Atlas 300I Pro
- `atlas_500_a2` - Atlas 500 A2

### Jetson

- `orin_agx_64gb` - Jetson AGX Orin 64GB
- `orin_agx_32gb` - Jetson AGX Orin 32GB
- `orin_nx_16gb` - Jetson Orin NX 16GB
- `orin_nano_8gb` - Jetson Orin Nano 8GB
- `xavier_nx` - Jetson Xavier NX
- `jetson_nano` - Jetson Nano 4GB
