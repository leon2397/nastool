# 检测项路线图

本文档有两个部分，用途完全不同：

- **第一部分：当前实现了什么** —— 直接从 `nastool --list-checks` 生成，以代码为准。想知道「这次体检覆盖了哪些方面」看这里。
- **第二部分：前身项目有、当前还没有的** —— 来自前身 v7.1.0-beta 的 92 个检测器清单，作为补齐路线图。想知道「下一步该做什么」看这里。

> 0.3.0 起判定逻辑从 `core/` 拆到 `checks/`，采集留 `collect/`。旧版本文档中形如 `core/storage.py` 的实现位置已失效；凡是「已实现」的项，代码位置统一在 `nastool/checks/<分类>.py`，采集在 `nastool/collect/<分类>.py`。

---

## 第一部分：当前实现（55 项）

`weight` 是该检查在分类内的相对重要性（1-6），决定它影响分类得分的力度；`依赖` 表示需要特定数据源（`smart_data` / `ssh_config` / `certs` / `smb_config` / `nfs_config`），拿不到时该项为「不适用」而不是失败。

### 存储（13）

| ID | 检查 | weight | 平台 | 依赖 |
|---|---|:--:|---|---|
| `storage.path_exists` | 数据路径存在 | 5 | any | |
| `storage.writable` | 数据路径可写 | 5 | any | |
| `storage.capacity` | 数据盘容量 | 4 | any | |
| `storage.inode` | inode 使用率 | 2 | linux | |
| `storage.readonly_mount` | 挂载只读 | 4 | linux | |
| `storage.physical_disks` | 物理磁盘识别 | 2 | linux | |
| `storage.raid_state` | 阵列健康 | 5 | linux | |
| `storage.raid_rebuild` | 阵列重建 | 3 | linux | |
| `storage.smart_health` | 硬盘 SMART 健康 | 6 | linux | smart_data |
| `storage.smart_bad_sectors` | 坏道计数 | 5 | linux | smart_data |
| `storage.smart_temperature` | 硬盘温度 | 2 | linux | smart_data |
| `storage.smart_age` | 硬盘通电时长 | 2 | linux | smart_data |
| `storage.speed` | 读写速度 | 2 | any | |

### 系统与硬件（10）

| ID | 检查 | weight | 平台 | 依赖 |
|---|---|:--:|---|---|
| `system.cpu_visible` | CPU 信息可读 | 1 | any | |
| `system.memory_readable` | 内存信息可读 | 1 | any | |
| `system.memory_pressure` | 内存压力 | 3 | any | |
| `system.swap_pressure` | 交换分区压力 | 1 | linux | |
| `system.thermal` | 温度 | 3 | linux | |
| `system.load_average` | 负载 | 2 | linux,macos | |
| `system.uptime` | 运行时长 | 1 | any | |
| `system.clock_sync` | 时间同步 | 2 | linux,windows | |
| `system.io_pressure` | 磁盘 I/O 压力 | 2 | linux | |
| `system.process_count` | 进程数量 | 1 | linux | |

### 网络（10）

| ID | 检查 | weight | 平台 | 依赖 |
|---|---|:--:|---|---|
| `network.interface_present` | 网络接口 | 3 | any | |
| `network.ip_assigned` | IP 地址 | 5 | any | |
| `network.link_speed` | 链路速率 | 3 | linux | |
| `network.duplex` | 双工模式 | 2 | linux | |
| `network.gateway` | 默认网关 | 2 | any | |
| `network.dns` | DNS 解析 | 2 | any | |
| `network.internet` | 外网连通 | 1 | any | |
| `network.peer_reach` | 对端可达性 | 2 | any | |
| `network.wireless_primary` | 主链路类型 | 3 | any | |
| `network.interface_errors` | 网卡错误计数 | 2 | linux | |

### 服务与端口（8）

| ID | 检查 | weight | 平台 | 依赖 |
|---|---|:--:|---|---|
| `services.port_inventory` | 端口清单 | 1 | any | |
| `services.file_sharing` | 文件共享服务 | 3 | any | |
| `services.web_ui` | 管理界面 | 1 | any | |
| `services.media_stack` | 媒体服务 | 1 | any | |
| `services.docker` | 容器运行时 | 2 | any | |
| `services.risky_ports` | 高风险服务 | 4 | any | |
| `services.exposed_bind` | 端口暴露范围 | 3 | any | |
| `services.unknown_services` | 未识别端口 | 1 | any | |

### 安全（8）

只读读取配置，不改动任何东西。

| ID | 检查 | weight | 平台 | 依赖 |
|---|---|:--:|---|---|
| `security.ssh_root_login` | SSH 允许 root 登录 | 4 | any | ssh_config |
| `security.ssh_password_auth` | SSH 密码登录 | 3 | any | ssh_config |
| `security.firewall` | 防火墙 | 4 | any | |
| `security.fail2ban` | 暴力破解防护 | 1 | linux | |
| `security.tls_cert` | 证书有效期 | 4 | any | certs |
| `security.self_signed` | 证书类型 | 2 | any | certs |
| `security.smb_guest` | SMB 匿名访问 | 3 | linux | smb_config |
| `security.nfs_root_squash` | NFS 权限映射 | 3 | linux | nfs_config |

### AI 算力（4）

| ID | 检查 | weight | 平台 | 依赖 |
|---|---|:--:|---|---|
| `ai.hardware` | AI 加速硬件 | 3 | any | |
| `ai.runtime` | 推理运行时 | 2 | any | |
| `ai.inference_perf` | 推理性能 | 2 | any | |
| `ai.vendor_env` | 厂商运行环境 | 1 | linux | |

> `ai` 分类在 `nas` 场景下**不启用**——只做文件存储的 NAS 不该因为没有 PyTorch 被判为不健康。`verify` / `dev` / `ai` 场景自动启用（`verify` 权重为 0，仅展示不评分）；`nas` 下需要时用 `--enable ai`，追加的分类拿保底权重 8。

### 外设（2）

| ID | 检查 | weight | 平台 | 依赖 |
|---|---|:--:|---|---|
| `usb.devices` | USB 设备 | 1 | linux | |
| `usb.storage_media` | 数据盘连接方式 | 4 | linux | |

---

## 第二部分：前身项目清单中的缺口

前身 v7.1.0-beta 有 **92 个检测器**（v4.5 "92 个检测器全部接入"），每个当时是独立文件。下表只列**当前仍未覆盖或只是部分覆盖**的部分，已完整实现的项不再重复。

原始分类与本项目分类不完全对齐（例如前身把 Docker 归在 system，本项目归在 services），所以下表按**前身原分类**组织，方便和归档文档对照。

### nas 专属（0/16，最大空白）

这是「通用 NAS 检测工具」最该补、也最能体现差异的一类。前身的实现是**真实协议探测**，不是只看端口——这是当前与它差距最大的一处。

| 检测项 | 含义 | 当前状态 |
|---|---|:--:|
| `smb_service` | SMB / CIFS 服务 | ◐ 仅端口（`services.file_sharing`），未做协议握手 |
| `nfs_service` | NFS 服务 | ◐ 仅端口 |
| `ftp_service` | FTP 服务 | ◐ 仅端口 |
| `sftp_service` | SFTP 服务 | ◐ 仅端口 |
| `webdav_service` | WebDAV | — |
| `afp_service` | AFP（macOS 共享） | — |
| `snmp_service` | SNMP | — |
| `ups_status` | UPS 状态 | — |
| `backup_status` | 备份任务状态 | — |
| `shared_perms` | 共享目录权限 | — 但有 `security.smb_guest` 覆盖匿名访问 |
| `user_stats` | 用户与容量配额 | — |
| `log_disk` | 日志分区空间 | — |
| `media_scanner` | 媒体索引服务 | — |
| `cron_conflicts` | 定时任务冲突 | — |
| `nas_temp` | NAS 整机温度 | ◐ `system.thermal` 间接覆盖 |
| `dsm_version` | 系统版本判定 | ◐ `collect/platform.py` 有版本字符串，未做判定 |

### 网络（缺 9 项）

| 检测项 | 含义 | 当前状态 |
|---|---|:--:|
| `latency_check` | 延迟探测 | ◐ `network.peer_reach` 带 RTT，无专项阈值 |
| `network_latency` | 网络延迟统计 | — |
| `bandwidth_check` | 带宽实测 | — |
| `mtu_check` | MTU 异常 | ◐ 读到了 MTU，未做异常判定 |
| `dns_cache` | DNS 缓存 | — |
| `dns_coverage` | DNS 覆盖 | — |
| `dns_diagnostic` | DNS 诊断 | — |
| `network_quality_checker` | 网络质量综合 | — |
| `port_conflict` | 端口冲突 | — |
| `proxy_check` | 代理配置 | — |

### 系统（缺 8 项）

| 检测项 | 含义 | 当前状态 |
|---|---|:--:|
| `system_disk` | 系统盘（根分区）空间 | ◐ 只测了数据盘 |
| `kernel_version` | 内核版本判定 | ◐ 有版本号，无判定 |
| `system_logs` | 系统日志错误 | — |
| `package_updates` | 待更新包 | — |
| `cron_jobs` | 定时任务清单 | — |
| `system_libs` | 关键系统库 | — |
| `python_version` | Python 版本 | — |
| `pip_installed` | pip 可用性 | — |

### 存储（缺 2 项）

| 检测项 | 含义 | 当前状态 |
|---|---|:--:|
| `io_wait` | IO 等待 | ◐ `system.io_pressure` 覆盖了 PSI，未看 `iostat` 明细 |
| `docker_images` | Docker 镜像占用 | — |

> `storage_trend`（存储增长趋势）已由历史库 + 逐项 diff 实现，见 `nastool/history.py`、`nastool/diff.py`。

### 安全（缺 4 项）

| 检测项 | 含义 | 当前状态 |
|---|---|:--:|
| `login_failures` | 登录失败次数 | — |
| `openssl_version` | OpenSSL 版本 | — |
| `clamav_check` | 杀毒引擎 | — |
| `selinux` | SELinux / AppArmor 状态 | — |

> `port_scan` / `ssh_root` / `ssh_config` / `firewall` / `fail2ban` / `ssl_cert` / `ssl_cert_check` 均已实现，见第一部分。前身 `ssl_cert_check` 曾有过「剩余天数显示 -1148 天」的 BUG，本项目在 `security.tls_cert` 里对已过期证书单独走 FAIL，不显示负天数。

### AI 算力（缺 15 项）

前身把 AI 拆成 19 个框架级检测器（cuDNN / TensorFlow / Keras / PaddlePaddle / OpenVINO / oneDNN / Triton / TorchServe / TF Serving / MLflow / Kubeflow …）。本项目的取舍是：**不逐个框架点名，而是验「这台机器能不能真跑起来推理」**（`ai.runtime` + `ai.inference_perf`）。

理由：框架清单是无限长的，而且用户装哪个框架与设备是否健康无关。真跑一次推理能同时证明运行时、驱动、算力三件事。

| 检测项 | 当前状态 |
|---|:--:|
| `gpu_memory_checker`（显存容量） | ◐ 部分读取 |
| `onnx_model_checker` | ◐ 有真实推理，无模型格式检查 |
| cuDNN / TensorFlow / Keras / PaddlePaddle / OpenVINO / oneDNN / 模型格式 / NVIDIA 容器运行时 / Triton / TorchServe / TF Serving / MLflow / Kubeflow / 组件版本汇总 | — 刻意不做 |

### USB 外设（缺 2 项）

`usb_devices`、`usb_storage` 已实现；`usb_permissions`、`usb_power` 未做。NAS 场景实际价值有限，优先级最低。

---

## 前身没有、当前独有的能力

对照不是单向下风，下面这些是前身项目**没有**的：

| 能力 | 说明 |
|---|---|
| **55 项检查的注册表架构** | `@check` 装饰器注册，新增一项只写一个函数，报告/评分/历史全部自动包含 |
| **不可判定状态（UNKNOWN）** | 读不到 SMART ≠ 硬盘坏了。UNKNOWN 不扣分但降低覆盖度，报告里明确显示盲区比例 |
| **覆盖度与置信度** | 覆盖度分母是「适用项」，Windows 上不会因为 31 项 Linux 专属检测拿不到数据就算成 39% 覆盖 |
| **两条封顶规则** | 存在严重问题封顶 59；盲区 ≥50% 封顶 74、≥30% 封顶 84。避免「A 级但硬盘快挂了」 |
| **场景化权重（`--profile`）** | nas / verify / dev / ai 四套权重与阈值，一套标准不再套所有设备 |
| **按芯片自适应温度阈值** | RK3588 走 70/82，Jetson 走 75/88，其余走场景默认 |
| **逐项历史对比** | 不只比总分，而是比每一条证据：新故障 / 仍故障 / 指标恶化 / 已修复。证据带 `trend` 方向语义，避免「多跑 0.1 小时」被报成恶化 |
| **13 类 NAS 平台识别 + 虚拟化判断** | DSM / QTS / TrueNAS / unRAID / TOS / UGOS / OMV / CasaOS / fnOS / Proxmox / OpenWrt / 通用 Linux / Windows / macOS |
| **Windows / macOS 采集** | 前身基本只跑 Linux（Jetson + RK），当前三平台可用 |
| **零第三方依赖** | 纯标准库，任意机器可跑；前身需要 6 个 pip 包 |

---

## 建议的补齐顺序

按「对目标用户价值 / 实现成本」排序：

1. **NAS 服务真实协议探测**（`smb` / `nfs` / `webdav`）—— 从「端口在听」升级到「协议能握手」。这是当前与通用 NAS 工具的分水岭，也是二手验机场景最缺的一环。改造点在 `collect/services.py`，只加采集、判定留在 `checks/services.py`。
2. **NAS 平台专属项**（DSM/QTS 的系统版本判定、UPS 状态、备份任务）—— 已有平台识别做底座，按平台分支实现成本低，且是与其他检测工具差异化的地方。
3. **登录失败次数 / 系统日志错误** —— 排查「有没有人在试密码」「夜里谁崩了」，成本低。
4. **`system_disk` 根分区空间** —— NAS 系统盘满了会整机异常，目前只测数据盘，是个实际盲点。
5. AI 框架清单（前身的 15 项）—— **不建议按原样补**。框架点名没有边界也没业务意义；如果确有需求，按 `--profile ai` 增加「某框架是否可用」的可选探测即可。
