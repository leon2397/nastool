# TEST_BUGS.md - v4.0.0 Jetson Xavier NX 真实诊断 BUG 记录

> 更新日期：2026-04-23
> 测试环境：Jetson Xavier NX, Ubuntu 20.04, aarch64, Python 3.8.10
> 测试路径：/home/nvidia/nastool-v4.0.0/

---

## 🐛 BUG 清单（按严重程度）

### P0 - 阻断性（导致结果错误）

#### BUG-001：Score = 0（评分系统失效）
- **文件**：`nastool-core/nastool_core/checks/__init__.py` 第 156-169 行
- **现象**：总分 0，Grade D（实际应该是 75分左右）
- **原因**：`r.severity` 在某些路径返回 string 而非 CheckSeverity enum，导致 `sev_score.get(r.severity, 0)` 永远返回默认值 0
- **修复方向**：在 `run_all_checks()` 返回结果前，确保所有 severity 都是 CheckSeverity enum；或加防御代码 `r.severity.value if hasattr(r.severity, 'value') else r.severity`
- **影响**：用户完全无法信任评分

#### BUG-002：SSL 证书天数显示负数
- **文件**：`checks/security/ssl_cert_check.py`
- **现象**：显示 `certs: -1148 days; certs: -1075 days; certs: -346 days; certs: -937 days`
- **原因**：证书过期日期计算逻辑 BUG，或读取了错误的日期字段
- **修复方向**：检查 openssl 命令输出解析逻辑，过期天数 = expiry_date - today，不应出现 -900+ 这种值

---

### P1 - 关键（信息错误/缺失）

#### BUG-003：Jetpack 版本检测失败
- **文件**：`checks/ai/jetpack_version.py`
- **现象**：`jetpack_version: Not a Jetson device`（但这是 Xavier NX！）
- **原因**：检测逻辑依赖 `/etc/nv_tegra_release`，文件不存在或路径错误
- **Jetson 实际情况**：有 NVIDIA GPU（通过 `/proc/driver/nvidia/gpus/` 可检测）、TensorRT 8.5.2 已安装、CUDA 11.4 已安装（PATH 中有 nvcc）
- **修复方向**：检测 `/proc/driver/nvidia/gpus/` 或 `tegrastats --query` 作为 Jetson 识别依据

#### BUG-004：GPU 检测误报 "No AI accelerator detected"
- **文件**：`checks/ai/gpu_detected.py`
- **现象**：Jetson Xavier NX 有 GPU（ARM G52），但检测返回 "No AI accelerator detected, will use CPU fallback"
- **原因**：只检测 `nvidia-smi`，Jetson 无 nvidia-smi
- **修复方向**：Jetson 专用 GPU 检测：检查 `/proc/driver/nvidia/gpus/`, `tegrastats --query`, 或 `/dev/nvhost-gpu`

#### BUG-005：CUDA 版本检测失败
- **文件**：`checks/ai/cuda_version.py`
- **现象**：`cuda_version: CUDA unknown installed (version DB unavailable)`，但实际 `nvcc --version` 输出 CUDA 11.4
- **原因**：`nvcc --version` 可能不在 PATH，或输出解析 BUG
- **修复方向**：添加 `which nvcc` 和 `tegrastats` 备选路径

#### BUG-006：CPU 温度输出乱码
- **文件**：`checks/system/cpu_temperature.py`
- **现象**：`CPU )n�^ck8^�gؚ 50.0�C`
- **原因**：终端编码问题（UTF-16），或 subprocess 输出未正确解码
- **修复方向**：subprocess.run 输出加 `.decode("utf-8", errors="replace")`

#### BUG-007：系统运行时间输出乱码
- **文件**：`checks/system/system_uptime.py`
- **现象**：`uptime: �|�~ЏL�ck8^�1 )Y 2 �e�s^3z`
- **原因**：同 BUG-006
- **修复方向**：同上

#### BUG-008：网卡速度输出乱码
- **文件**：`checks/network/nic_speed.py`
- **现象**：`eth1 �N 10 Mbps�ǏNO`
- **原因**：同上
- **修复方向**：同上

---

### P2 - 次要（检测不准确）

#### BUG-009：nvidia-smi 失败但 GPU 实际存在
- **现象**：`nvidia_driver_version: NVIDIA driver installed but version undetermined`，`gpu_memory: nvidia-smi ��S(u���Ǐ`，`gpu_utilization: nvidia-smi ��S(u���Ǐ`
- **原因**：nvidia-smi 在 Jetson 上不存在，应使用 tegrastats 或 /proc/driver/nvidia/gpus/
- **修复方向**：为 Jetson 添加 tegrastats 分支

#### BUG-010：内存显示异常（6846.0GB available）
- **文件**：`checks/system/memory_check.py`
- **现象**：显示 `Memory 6846.0GB available`（Xavier NX 只有 8GB LPDDR4x）
- **原因**：可能解析了错误文件（如 /proc/meminfo 的 swap 行）
- **修复方向**：检查 free/parse_meminfo 输出

#### BUG-011：NAS 后端检测超时
- **文件**：`checks/nas/nas_backend.py`
- **现象**：`NAS backend 120.77.249.3:8000 not reachable`
- **原因**：120.77.249.3 是公网 IP，Jetson 无外网连接
- **修复方向**：检测超时时间需缩短（当前可能过长），或检测前先确认外网连通性

#### BUG-012：写入速度偏低（108.7 MB/s）
- **文件**：`checks/storage/write_speed.py`
- **现象**：108.7 MB/s，对于 NVMe SSD 偏低（正常应 >500 MB/s）
- **原因**：可能是测试文件过小，或测试路径在机械硬盘
- **修复方向**：增加测试文件大小，确认测试路径

---

### P3 - 改进建议（不影响正确性）

#### IMP-001：网络连通性分级
- DNS 解析 `baidu.com` 失败 → Warning（可能是隔离网络）
- DNS 解析 `google.com` 失败 → Info（国内正常现象）
- 建议：按设备用途（NAS/开发机/AI服务器）给出不同网络要求

#### IMP-002：AI 框架未安装不一定是 Warning
- TensorFlow/Keras/OpenVINO 等未安装 → Warning
- 如果设备不是 AI 推理服务器，这应该是 Info
- 建议：按 `ai_focus` 配置决定严重程度

#### IMP-003：缺少 tegrastats 检测适配
- Jetson 专用工具 `tegrastats` 完全未使用
- 应作为 CPU/GPU 温度和内存的备选数据源

---

## 根因分析

### 编码问题（BUG-006/007/008）
- 所有乱码输出都是 subprocess 输出未正确处理编码
- Jetson 终端可能默认 UTF-16，Python subprocess 若不指定 encoding 则用系统默认
- **统一修复**：所有 `subprocess.run` 加 `encoding="utf-8", errors="replace"`

### Jetson 适配问题（BUG-003/004/005/009）
- 代码假设 x86_64 Linux 环境（有 nvidia-smi）
- Jetson 是 aarch64 + 无 nvidia-smi + 专用工具链
- **统一修复**：在 adapter 层添加 Jetson 设备识别和备选工具链

### 评分系统（BUG-001）
- `r.severity` 类型不一致的根本原因需要进一步调试
- 可能与 Python 3.8 的 dataclass enum 行为有关
- **统一修复**：在 CheckResult 构造时强制类型，或在评分时做类型兼容处理
