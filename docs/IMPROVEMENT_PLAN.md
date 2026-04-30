# nastool v4.1.0 改进计划

> 制定日期：2026-04-23
> 触发事件：Jetson Xavier NX 真机测试发现 12 个 BUG
> 优先级：P0 阻断 > P1 关键 > P2 次要 > P3 改进

---

## 一、修复 BUG（P0 + P1，1-2天）

### P0-A：评分系统修复（BUG-001）

**问题**：`r.severity` 在某些路径返回 string，评分永远为 0

**修复方案**：在 `nastool-core/nastool_core/checks/__init__.py` 的 `run_all_checks()` 返回结果前，统一做类型归一化：

```python
# 评分前，确保所有 severity 都是 CheckSeverity enum
for r in results:
    if isinstance(r.severity, str):
        # 字符串转 enum（fallback）
        try:
            r.severity = CheckSeverity[r.severity.upper()]
        except KeyError:
            r.severity = CheckSeverity.WARNING

total_score = sum(sev_score.get(r.severity, CheckSeverity.PASSED) for r in results)
```

**验证标准**：Jetson 真实诊断 Score 应在 70-85 范围（非 0）

---

### P0-B：SSL 证书天数 BUG（BUG-002）

**问题**：证书过期天数显示 -1148 天

**修复方案**：检查 `ssl_cert_check.py` 的 openssl 解析逻辑，过期天数 = expiry_timestamp - current_timestamp，应 ≥ 0

**验证标准**：有效证书显示正数，已过期显示负数但绝对值合理（< 3650 = 10年）

---

### P1-A：编码统一处理

**问题**：subprocess 输出乱码（BUG-006/007/008）

**统一修复**：所有 `subprocess.run()` 调用统一添加：
```python
subprocess.run(
    cmd,
    capture_output=True,
    encoding="utf-8",
    errors="replace"  # 关键：替换无法解码的字符
)
```

**影响文件**：
- `cpu_temperature.py`
- `system_uptime.py`
- `nic_speed.py`
- 其他所有用 subprocess 的 check 文件（约 30 个）

**建议**：在 `nastool_core/common/utils.py` 创建统一的 `run_command()` 封装函数

---

### P1-B：Jetson 设备适配

#### BUG-003/004/005/009 统一修复

创建 Jetson 适配器，检测到 aarch64 + NVIDIA GPU 后切换备选工具链：

```python
# nastool_adapters/jetson_adapter.py
def is_jetson():
    """检测是否为 Jetson 设备"""
    return os.path.exists("/proc/driver/nvidia/gpus")

def get_gpu_info():
    """Jetson 专用 GPU 检测（无 nvidia-smi）"""
    if is_jetson():
        # 使用 tegrastats
        result = subprocess.run(
            ["tegrastats", "--interval", "100"],
            capture_output=True, timeout=2
        )
        return parse_tegrastats(result.stdout)
    else:
        # 使用 nvidia-smi
        ...

def get_cuda_version():
    """Jetson 专用 CUDA 检测"""
    # 检查 /usr/local/cuda/bin/nvcc
    cuda_paths = [
        "/usr/local/cuda/bin/nvcc",
        "/usr/bin/nvcc",
        "/opt/cuda/bin/nvcc"
    ]
    for path in cuda_paths:
        if os.path.exists(path):
            result = subprocess.run([path, "--version"], ...)
            return parse_cuda_version(result.stdout)
    return "unknown"
```

---

## 二、增强检测能力

### 2.1 网络隔离场景支持

**现状**：Jetson 无外网，所有网络检测都 FAIL

**改进**：将网络检测分级：
| 场景 | 检测策略 |
|------|---------|
| NAS 服务器 | 必须检测外网连通性 |
| 开发/测试机 | 只测内网，外网 FAIL → INFO |
| AI 推理服务器 | 只测 GPU/存储，外网 INFO |
| Jetson 隔离设备 | 外网检测默认跳过 |

**实现**：`--profile` 参数
```
nastool --profile nas        # 完整网络检测
nastool --profile dev        # 跳过外网检测
nastool --profile jetson      # Jetson 专用（含 tegrastats）
```

---

### 2.2 智能评分权重

**现状**：所有 check 等权重，Score 计算不区分设备类型

**改进**：按设备类型动态权重

```python
WEIGHTS = {
    "default": {"system": 1.0, "network": 1.0, "storage": 1.0, "ai": 0.5, "security": 1.0},
    "nas":     {"system": 0.8, "network": 1.2, "storage": 1.5, "ai": 0.3, "security": 1.2},
    "ai_server": {"system": 0.8, "network": 0.5, "storage": 1.0, "ai": 2.0, "security": 1.0},
    "jetson":  {"system": 1.0, "network": 0.3, "storage": 1.0, "ai": 1.5, "security": 0.8},
}
```

---

### 2.3 报告增强

**JSON 报告**（已实现但未充分测试）：
```json
{
  "device": "jetson-xavier-nx",
  "profile": "jetson",
  "score": 78,
  "grade": "B",
  "timestamp": "2026-04-23T15:36:45+08:00",
  "checks": [...],
  "suggestions": [...],
  "action_plan": [
    {"priority": 1, "fix": "ssh_hardening", "risk": "medium"},
    {"priority": 2, "fix": "cleanup_temp", "risk": "low"}
  ]
}
```

**HTML 报告**：生成带图表的健康仪表盘（温度趋势、存储趋势、CPU 趋势）

---

## 三、安全架构完善

### 3.1 已实现
- ✅ `security.py` 禁止清单
- ✅ `base.py` 备份机制
- ✅ `fix_engine.py` 回滚脚本
- ✅ `registry.py` 前置拦截

### 3.2 待实现

**紧急 fix 执行确认**：
```
$ nastool fix cleanup_temp
⚠️  WARNING: This fix will delete:
  - /tmp/* (excluding hidden dirs)
  - /var/tmp/* (excluding hidden dirs)
  Total: ~45MB to be freed

Backup created: ~/.nastool/backups/20260423_1536/
Type 'yes' to confirm: _
```

**Dry-run 强制化**：所有 `risk >= medium` 必须先 dry-run

**回滚验证**：fix 执行后自动运行验证 check，不通过则自动回滚

---

## 四、测试覆盖率提升

### 4.1 Jetson 真机测试用例

```python
# tests/test_jetson_realtime.py
class TestJetsonRealTime:
    """Jetson Xavier NX 真机测试（非 mock）"""
    
    def test_gpu_detection_no_nvidia_smi(self):
        """Jetson 无 nvidia-smi，必须用 tegrastats"""
        
    def test_tegrastats_parsing(self):
        """tegrastats 输出解析正确"""
        
    def test_cuda_in_non_standard_path(self):
        """CUDA 不在 PATH 时能正确检测"""
        
    def test_memory_check_jetson_8gb(self):
        """8GB 内存正确识别"""
        
    def test_network_isolated_mode(self):
        """无外网环境下不报 FAIL"""
        
    def test_encoding_gb2312_output(self):
        """subprocess 中文输出正确解码"""
```

### 4.2 回归测试套件

当前覆盖率约 60%，目标：
- P0 BUG 修复后：全部 93 项基础冒烟测试
- P1 BUG 修复后：编码兼容性测试 + Jetson 适配测试
- v4.1.0 完成后：端到端报告生成测试

---

## 五、Jetson 专用适配层

### 架构设计

```
nastool/
├── adapters/
│   ├── base.py              # Adapter 基类
│   ├── linux_adapter.py     # 通用 Linux
│   ├── jetson_adapter.py    # Jetson 专用 ⭐ 新增
│   ├── nas_adapter.py       # NAS 专用
│   └── rk_adapter.py        # Rockchip 专用
```

### Jetson Adapter 功能

| 功能 | 当前实现 | Jetson 适配 |
|------|---------|-----------|
| GPU 检测 | nvidia-smi | /proc/driver/nvidia/gpus/ + tegrastats |
| CUDA 检测 | which nvcc | /usr/local/cuda/bin/nvcc + nvcc --version |
| 温度检测 | /sys/class/thermal/ | tegrastats --interval 100 |
| Jetpack 版本 | /etc/nv_tegra_release | cat /etc/nv_tegra_release |
| NPU 检测 | /dev/npu | rknn-toolkit 检测 |
| 内存检测 | free -m | free -m（正常） |
| GPU 温度 | nvidia-smi | tegrastats |

---

## 六、工时估算

| 阶段 | 任务 | 工时 | 优先级 |
|------|------|------|--------|
| **Phase 1：P0 BUG 修复** | | **4-6h** | 🔴 P0 |
| 1.1 | 评分系统 severity 归一化 | 1h | 🔴 |
| 1.2 | SSL 证书天数 BUG | 1h | 🔴 |
| 1.3 | 编码统一处理（run_command 封装） | 2h | 🔴 |
| 1.4 | 回归测试验证 | 1-2h | 🔴 |
| **Phase 2：Jetson 适配** | | **6-8h** | 🟠 P1 |
| 2.1 | Jetson Adapter 基础框架 | 2h | 🟠 |
| 2.2 | GPU/CUDA/Jetpack 检测适配 | 2h | 🟠 |
| 2.3 | tegrastats 解析器 | 1h | 🟠 |
| 2.4 | Jetson 真机验证 | 1-2h | 🟠 |
| **Phase 3：报告增强** | | **4-5h** | 🟡 P2 |
| 3.1 | JSON 报告完整化 | 1h | 🟡 |
| 3.2 | HTML 仪表盘 | 2-3h | 🟡 |
| 3.3 | Action Plan 生成 | 1h | 🟡 |
| **Phase 4：智能评分** | | **3-4h** | 🟡 P2 |
| 4.1 | --profile 参数实现 | 1h | 🟡 |
| 4.2 | 动态权重计算 | 2h | 🟡 |
| 4.3 | 网络隔离场景适配 | 1h | 🟡 |
| **Phase 5：测试覆盖** | | **4-6h** | 🟡 P2 |
| 5.1 | 93 项基础冒烟测试 | 2h | 🟡 |
| 5.2 | 编码兼容性测试 | 1h | 🟡 |
| 5.3 | Jetson 真机测试用例 | 1-2h | 🟡 |
| **Phase 6：安全架构** | | **2-3h** | 🔵 P3 |
| 6.1 | 紧急 fix 交互确认 | 1h | 🔵 |
| 6.2 | 回滚自动验证 | 1h | 🔵 |
| 6.3 | 安全测试用例 | 1h | 🔵 |

**总计：23-32 小时**（约 4-5 个工作日）

---

## 七、版本规划

| 版本 | 目标 | 交付内容 | 预计时间 |
|------|------|---------|---------|
| **v4.0.1** | BUG 紧急修复 | P0 BUG 全部修复，编码问题修复 | 今天 |
| **v4.1.0** | Jetson 适配 | Jetson Adapter，teargrastats，profile 参数 | 2天内 |
| **v4.2.0** | 报告增强 | JSON/HTML 完整报告，智能评分 | 3天内 |
| **v4.3.0** | 测试完备 | 93 项测试覆盖，安全架构完善 | 5天内 |

---

## 八、立即行动（今天）

1. **P0 BUG 修复**：
   - `checks/__init__.py`：severity 归一化
   - `ssl_cert_check.py`：证书天数计算
   - `utils.py`：`run_command()` 封装函数（统一加 encoding）

2. **回归测试**：
   - 本机 mock 模式验证 Score 正常
   - Jetson 真实模式验证修复效果

3. **记录**：
   - 更新 `TEST_BUGS.md` 的修复状态
   - 提交 git commit：`fix: BUG-001~008 in v4.0.1 hotfix`
