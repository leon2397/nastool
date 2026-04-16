# nastools 更新日志

## v7.1.0（2026-04-16）

> 主题：测试流程优化 × 诊断体验增强

### Bug 修复

**BUG-FIX-001 — --quick 显示 Passed: 0/0**
- 根因 1：`quick_diagnose.py` 的 `QUICK_CHECKS` 使用旧格式 `system.python_version`，registry 用纯 ID `python_version`，全部匹配失败
- 根因 2：统计用 `r.severity == CheckSeverity.PASSED`，但应改用 `r.passed` 布尔值
- 修复：更新 `QUICK_CHECKS` 为纯 ID；统计改用 `r.passed`
- 修复：批量迁移 43 个检查文件 `ctx.result(passed=X, ...)` → `ctx.passed()/ctx.failed()`

**BUG-FIX-007 — HTML 报告不生成**
- 根因：`--quick` 模式在 `return` 前提前退出，未执行 `--output` 处理逻辑
- 修复：在 `--quick` 分支末尾添加 `--output` 处理（与 full mode 相同的逻辑）
- 修复：`file_reporter.py` 接受字符串 severity（`'INFO'`）而非只接受枚举

### 功能增强

**F1 — --version 输出增强**
- 新增 `--version-json` 输出机器可读 JSON
- 版本信息包含：git hash / branch / date / dirty flag / check count / category 分布
- `nastool/core/version_info.py`：统一版本信息获取模块

**版本号修复**
- `arm_diagnose.py __version__` 从 `"5.0.4"` → `"7.1.0-beta"`（与 CHANGELOG 一致）

## v7.0（2026-04-16）

> 主题：引擎升级 — 并行执行 × 声明式检查 × Pydantic 配置 × 统一修复

### 新增功能

**Task 3.1 — 并行执行引擎**
- `core/executor.py`：L0/L1/L2 三级并行策略
  - L0（系统级并行）：按 category 分组并发
  - L1（依赖级并行）：同一批可并行的检查并发
  - L2（单检查并行）：长检测项内部多线程
- 依赖解析：拓扑排序 DAG，按 `depends_on` 约束执行顺序
- 缓存层：`~/.nastool/check_cache/` JSON 缓存，TTL 可配置
- 性能：38 tests 0.67s（vs 原 91s，加速 136×）

**Task 3.2 — 声明式 @check() 装饰器**
- `checks/decorators.py`：@check() 装饰器
  - `CheckContext`：提供 passed/failed/warning/info/skipped 快捷方法
  - `CheckMeta`：新增 depends_on/timeout/tags/can_parallel 字段
  - 自动类名生成：tensorflow_version → TensorFlowVersionCheck
  - 向后兼容：原有 class 式检查继续工作
- AI checks 迁移 16/17：
  tensorflow, keras, cudnn, openvino, paddlepaddle, gpu_detected, gpu_memory, gpu_utilization, nvidia_container, onnx_model, onednn, triton, mlflow, torchserve, tf_serving, kubeflow, model_format

**Task 3.3 — Pydantic 配置校验**
- `schemas/check_config.py`：checks.yaml 的 Pydantic 模型（CheckConfig + 10 子类）
- `schemas/health_weights.py`：health_weights.yaml 的 Pydantic 模型（135 个权重）
- `core/config_loader.py`：集成校验，graceful fallback（无 pydantic 时警告但不崩）

**Task 3.4 — 统一修复引擎**
- `fixes/fix_engine.py`：单文件统一引擎
  - 合并 fix_engine_v2.py + fix_recommendations.py + interactive_fix.py
  - `FIX_MAP`：21 个 fix 映射到 18 个 check_id
  - `FixRisk`：LOW / MEDIUM / HIGH / DANGER 四级
  - `FixEngine.execute()`：dry-run / force / interactive 模式
  - `FixEngine.execute_auto()`：--fix --auto 全自动模式
  - `FixEngine.interactive_flow()`：完整交互流程（含高风险确认）
  - 快照：`~/.nastool/fix_snapshots/*.json`

---

## v5.0.1（2026-04-15）

> 主题：Mock 数据支持 — 无需真机也能跑全部 82 项检测

### 新增功能

- `python arm_diagnose.py --mock healthy` — 健康设备模拟（评分 96）
- `python arm_diagnose.py --mock degraded` — 降级设备模拟（评分 87）
- `python arm_diagnose.py --mock critical` — 故障设备模拟（评分 58）
- `python arm_diagnose.py --mock mixed` — 随机分布（演示用）

### 新增文件

- `mock_results.py`（根目录）— 82 项检测的 Mock 数据，4 个设备配置
- `data/__init__.py` — Lazy import 解决 ProfileManager 循环依赖

### Bug 修复

- `checks/__init__.py`: `run_mock_checks()` score 计算（CheckSeverity 枚举乘法问题）
- `checks/__init__.py`: `results.results` 迭代
- `arm_diagnose.py`: `TerminalReporter verbose` 参数
- `arm_diagnose.py`: `--skip` 分支 `summary` 未定义
- `data/__init__.py`: 添加 lazy import 解决循环依赖
- `data/mock_results.py`: 语法错误（多余 `]`）

---

## v4.2.1（2026-04-15）

> 主题：全面扩展 — 从 40 项增至 82 项检测

### 新增检测（42 项）

**AI（16）：**
- tensorflow_version: TensorFlow 版本
- keras_version: Keras 版本
- paddlepaddle_version: 百度飞桨
- openvino_version: Intel OpenVINO 推理引擎
- cudnn_version: NVIDIA cuDNN 版本
- onednn_version: Intel OneDNN / MKL-DNN
- triton_server: Triton Inference Server
- torchserve: PyTorch TorchServe
- tensorflow_serving: TensorFlow Serving
- mlflow: MLflow ML 实验跟踪
- kubeflow: Kubernetes Kubeflow
- onnx_model: ONNX 模型验证
- model_format: 模型格式检测 (.onnx/.pt/.h5/.pb)
- gpu_memory: GPU 显存使用率
- gpu_utilization: GPU 计算利用率
- nvidia_container_toolkit: NVIDIA Container Toolkit

**NAS（7）：**
- nfs_service: NFS 服务状态
- smb_service: SMB/CIFS 服务状态
- afp_service: AFP 服务状态（Mac）
- ftp_service: FTP 服务状态
- sftp_service: SFTP 服务状态
- webdav_service: WebDAV 服务
- snmp_service: SNMP 服务状态
- backup_status: 定时备份任务
- media_indexer: 媒体索引服务
- nas_temperature: NAS 设备温度

**安全（6）：**
- openssl_version: OpenSSL 版本（已知漏洞检测）
- ssh_config: SSH 安全配置（密码登录/密钥/端口）
- fail2ban: Fail2ban 防暴力破解
- clamav: ClamAV 杀毒软件
- suspicious_ports: 异常端口检测
- ssl_cert_days: SSL 证书有效期

**网络（6）：**
- network_latency: 网络延迟（多节点测试）
- bandwidth: 网卡协商速率
- mtu_size: MTU 大小检测
- proxy_config: 代理配置
- wifi_status: WiFi 连接状态
- default_route: 默认路由
- dns_cache: DNS 缓存服务

**存储（3）：**
- io_wait: IO Wait 检测（磁盘瓶颈）
- zfs_pool: ZFS 存储池健康
- inode_usage: Inode 使用率

**系统（4）：**
- kernel_version: 内核版本及安全更新
- docker_service: Docker daemon 状态
- cron_jobs: 定时任务统计
- system_logs: 系统日志异常
- process_count: 进程数量（泄露检测）
- package_updates: 系统包更新检测

### Bug 修复

- `arm_diagnose.py`: `len(results)` → `len(results.results)` (TypeError)
- `arm_diagnose.py`: `results` 迭代 CheckSummary 改为 `results.results`
- `history.py`: `CheckSeverity.OK` → `CheckSeverity.PASSED`
- `ssh_config.py`: UnboundLocalError（`warnings` 变量作用域）
- 所有检测器使用标准 CheckResult 模式
- 所有 YAML profile 文件编码声明修复

---

## v4.2.0（2026-04-14 已发布）

> 主题：跨网远程管理 — 无论在哪都能管理你的 NAS

### 新增功能

#### Relay Server v2.0.0
- Node.js + WebSocket 中继服务器
- WebSocket 双通道：Agent ↔ Relay ↔ GUI
- 心跳机制：30s 间隔保活
- 断线重连：指数退避策略（1s → 2s → 4s → 8s → 30s）
- REST API：设备管理、认证、状态查询
- SQLite 持久化：agent_keys / sessions / commands / reports / files

#### 跨网远程管理
- 无需公网 IP / 端口映射
- 支持 NAT / 防火墙后的设备
- 支持多设备同时在线
- 远程执行检测命令
- 实时状态监控

#### Web Dashboard（Vue 3）
- 设备管理面板
- 实时状态显示
- 连接管理

### 技术统计
- relay_server/src: 4 文件
- relay_server/agent: 10 文件  
- relay_server/web_dashboard: 18 文件
- 总计：32 文件

---

## v4.1.0（2026-04-14 已发布）

> 主题：部署能力强化 — ARM Agent 部署

### 新增功能

#### ARM Agent（Python）
- asyncio 守护进程
- WebSocket 协议编解码
- 自动重连机制
- 状态上报（设备信息、运行状态）
- 命令执行与结果回传

#### 部署验证
- 部署后自动检查
- 健康状态验证
- 连接测试

---

## v4.0.2（2026-04-14 已发布）

> 主题：工具属性强化 — 让诊断更专业、更全面、更傻瓜

### 新增功能

#### P0 检测项大扩容（22 → 35 项）

**系统 System (8)**
- Python 版本检测
- pip 可用性检测
- 内存使用率
- 磁盘空间
- CPU 温度
- 系统运行时间
- Docker 状态
- 系统库完整性

**网络 Network (6)**
- 互联网连通性
- DNS 解析
- 端口可用性
- 网卡速率
- DNS 覆盖检测
- NAS 后端检测

**存储 Storage (8)**
- 磁盘空间详情
- 读写速度
- SMART 健康状态
- HDD/SSD 温度
- RAID 阵列状态
- Docker 镜像
- 路径有效性
- 存储趋势分析

**AI 加速 (2)**
- GPU 检测
- CUDA 版本

**安全 Security (5)**
- 防火墙状态
- SELinux 状态
- SSH root 登录
- 登录失败检测
- SSL 证书有效期

**NAS 系统 (6)**
- DSM/QTS 版本
- 用户账号统计
- 共享文件夹权限
- UPS 连接状态
- 日志磁盘空间
- 定时任务冲突

#### P1 健康评分系统
- 综合评分 0-100 分
- 分级显示：健康(80+)/警告(60-79)/问题(<60)
- 自动归类警告项和问题项
- 每个问题给出具体修复建议

#### P2 修复能力扩容
- 从 5 种扩展到 15+ 种
- Python 3.11 一键安装
- DNS 修复（追加模式）
- 路径环境变量修复
- CUDA / TensorRT 安装
- Docker 安装

#### P3 普通人视角优化

**术语翻译（24 KB）**
- 工程师术语 → 普通人易懂
- 70+ 术语映射

**友好错误提示（13 KB）**
- 技术错误 → 用户友好信息
- 故障排查指导

**可视化报告（24 KB）**
- HTML 报告导出
- PDF 报告导出

#### P4 设备覆盖扩容
- 新增 14 个适配器
- 覆盖群晖/威联通/Jetson/RK3588/树莓派/OrangePi/SOPHON 等

### 技术统计
- 检测项：35
- 适配器：14
- 修复模块：3
- 工具函数：16

---

## v4.0.1（2026-04-14 已发布）

> 重要：代码质量提升，架构重构完成

### 新增功能

#### 架构重构
- 目录精简：25 → 12 目录
- 代码重复清理（裸 except 35 → 0）
- 异常处理规范化（137 处 + as e）
- 新增 utils/registry.py 通用注册器

#### 备份管理器
- 新增 core/safety.py（BackupManager + 安全装饰器）
- 新增 gui/local_backup_dialog.py
- 主界面添加「本地备份」按钮

#### 日志系统
- 添加 log() 方法（线程安全）
- 添加 _log_consumer 后台线程
- 添加 _append_log 显示方法

#### 代码质量
- ruff format 130 文件
- 修复 14 个语法错误文件
- 核心模块 docstring 补充

#### 文档更新
- 更新 CHANGELOG.md
- 更新 README.md
- 更新 nastools_README.md
- 更新 MEMO.md
- 更新 nastools_ROADMAP.md

### 发布包

- 版本：v4.0.1
- 发布包：nastools-v4.0.1.zip
- 大小：0.52 MB
- 文件数：237
- SHA256：fd0749803633e869a551b93fa9c75aeab34a3e24312677539ec2f744aab637b9

---

## v4.0.0（2026-04-14 已发布）

> 重要：架构重构，目录结构优化

### 目录结构变化

```
旧结构（25 目录）→ 新结构（12 目录）

删除：
- alerts/, data/, db/, plugins/, reporter/（空目录）
- api/, daemon/, web/（冗余）

合并：
- nas_integration → adapters/
- synology → adapters/
- version_db → core/
- gui → nastools_pkg/

重命名：
- disk_space.py → storage_disk.py / system_disk.py
```

### 代码质量提升

- 新增 71 个 TODO 记录技术债务
- 创建 TECH_DEBT.md 记录
- 硬编码 IP 配置化（network_config.yaml）
- 清理 30 个 .bak 残留文件

---

## v3.0.0（2026-04-13 已发布）

### 新增功能

#### Relay Server（Node.js）
- WebSocket 双通道（Agent ↔ Relay ↔ GUI）
- 心跳机制 + 断线重连
- 指数退避策略
- REST API 管理

#### ARM Agent（Python）
- asyncio 守护进程
- 协议编解码
- 自动重连
- 状态上报

#### Web Dashboard（Vue 3）
- 设备管理面板
- 实时状态
- 连接管理

#### USB/ADB 直连
- ADB over USB 连接
- USB 设备发现
- 一键连接

### 技术债务清理

- 修复 bat 文件 UTF-8 BOM 问题
- 项目统计：106 文件 / 16,965 行 / 22 checks / 5 fixes / 8 adapters

### 发布包

- 版本：v3.0.0
- 发布包：nastools-v3.0.0.zip
- 大小：0.51 MB
- 文件数：236

---

## v2.0.0（2026-04-12 已发布）

### 核心功能

- 多设备管理基础
- 远程中继（Relay）
- 设备状态存储

---

## v1.0.0（2026-04-12 初始版本）

### 基础功能

- SSH 连接
- 设备信息卡
- 16 项检测
- 结果颜色区分
- 实时日志
- 5 种一键修复
- 深色科技风 UI
