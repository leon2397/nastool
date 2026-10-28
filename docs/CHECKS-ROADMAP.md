# 检测项路线图（92 项对照）

本清单来自前身项目 `docs/devices/CODE_AUDIT_REPORT.md` 里的实际文件清单，已核实为 **92 个检测器**（v4.5 "92 个检测器全部接入"）。每个检测器当时是一个独立文件，同目录还有 `__init__.py`，合计 99 个文件。

下表逐项标注当前 nastool v0.2.0 的实现状态，可直接当补齐路线图用。

图例：`✅` 已实现　`◐` 部分覆盖　`—` 未实现

---

## 覆盖率总览

| 分类 | 原始数量 | 已实现 ✅ | 部分 ◐ | 未实现 — | 已实现率 |
|---|---:|---:|---:|---:|---:|
| system 系统 | 14 | 6 | 0 | 8 | 43% |
| storage 存储 | 11 | 6 | 1 | 4 | 55% |
| network 网络 | 17 | 5 | 3 | 9 | 29% |
| nas 专属 | 16 | 0 | 2 | 14 | 0% |
| security 安全 | 11 | 1 | 0 | 10 | 9% |
| ai 算力 | 19 | 2 | 2 | 15 | 11% |
| usb 外设 | 4 | 0 | 0 | 4 | 0% |
| **合计** | **92** | **20** | **8** | **64** | **22%** |

按"已实现 + 部分算半个"计，覆盖约 **26%**。

**结论：存储是唯一过半的分类（55%），NAS 专属与 USB 完全空白，安全只有 1 项。**

---

## system 系统（6/14）

| 检测项 | 含义 | 状态 | 当前实现位置 |
|---|---|:--:|---|
| `cpu_temp` | CPU / SoC 温度 | ✅ | `core/device.py` thermals |
| `memory_check` | 内存容量与占用 | ✅ | `core/device.py` memory |
| `uptime` | 运行时长 | ✅ | `core/device.py` |
| `system_disk` | 系统盘空间 | ✅ | `core/storage.py` disks |
| `docker_containers` | Docker 容器清单 | ✅ | `core/services.py` |
| `docker_service` | Docker 服务状态 | ✅ | `core/services.py` |
| `kernel_version` | 内核版本 | — | 未做版本判定（只有 `platform.release()` 展示） |
| `python_version` | Python 版本 | — | 待补 |
| `pip_installed` | pip 可用性 | — | 待补 |
| `process_count` | 进程数量异常 | — | 待补 |
| `system_libs` | 关键系统库 | — | 待补 |
| `system_logs` | 系统日志错误 | — | 待补 |
| `package_updates` | 待更新包 | — | 待补（Linux 侧） |
| `cron_jobs` | 定时任务清单 | — | 待补 |

## storage 存储（6/11，最高完成度）

| 检测项 | 含义 | 状态 | 备注 |
|---|---|:--:|---|
| `storage_disk` | 磁盘容量 | ✅ | 含全部挂载点 |
| `raid_status` | RAID 状态 | ✅ | mdstat / zpool / btrfs 三条路都做了 |
| `smart_health` | SMART 健康 | ✅ | 健康结论 + 重映射扇区 |
| `hdd_temp` | 硬盘温度 | ✅ | 走 SMART 温度 |
| `inode_check` | inode 使用率 | ✅ | — |
| `zfs_health` | ZFS 池健康 | ✅ | `zpool status` |
| `write_speed` | 写入速度 | ◐ | 已实现但默认 `--no-speed-test` 跳过 |
| `io_wait` | IO 等待 | — | 待补（`/proc/stat`、`iostat`） |
| `storage_trend` | 存储增长趋势 | — | 依赖历史库，见 `reference/code/compare.py` |
| `docker_images` | Docker 镜像占用 | — | 待补 |
| `path_exists` | 关键路径存在性 | — | 待补 |

## network 网络（5/17）

| 检测项 | 含义 | 状态 | 备注 |
|---|---|:--:|---|
| `network_status_checker` | 网卡状态 | ✅ | 接口 / IP / 状态 |
| `nic_speed` | 网卡速率 | ✅ | 含 ≤100Mbps 告警 |
| `dns_resolve` | DNS 解析 | ✅ | — |
| `internet_access` | 外网连通 | ✅ | 分级为提示而非错误 |
| `route_check` | 路由 / 网关 | ✅ | 仅默认网关 |
| `mtu_check` | MTU 异常 | ◐ | 读到了 MTU 值，但未做异常判定 |
| `wifi_check` | 无线状态 | ◐ | 仅标记 `is_wireless` |
| `nas_backend` | 后端服务连通 | ◐ | 已通用化为"对端 host:port"探测 |
| `latency_check` | 延迟探测 | — | 待补 |
| `network_latency` | 网络延迟统计 | — | 待补 |
| `bandwidth_check` | 带宽实测 | — | 待补 |
| `dns_cache` | DNS 缓存 | — | 待补 |
| `dns_coverage` | DNS 覆盖 | — | 待补 |
| `dns_diagnostic` | DNS 诊断 | — | 待补 |
| `network_quality_checker` | 网络质量综合 | — | 待补 |
| `port_conflict` | 端口冲突 | — | 待补 |
| `proxy_check` | 代理配置 | — | 待补 |

## nas 专属（0/16，最大空白）

这是"通用 NAS 检测工具"最该补、也最能体现差异的一类。原始实现里每个 NAS 服务都是**真实协议探测**，不是只看端口。

| 检测项 | 含义 | 状态 |
|---|---|:--:|
| `smb_service` | SMB / CIFS 服务 | — 仅端口 |
| `nfs_service` | NFS 服务 | — 仅端口 |
| `ftp_service` | FTP 服务 | — 仅端口 |
| `sftp_service` | SFTP 服务 | — 仅端口 |
| `afp_service` | AFP（macOS 共享） | — |
| `webdav_service` | WebDAV | — |
| `snmp_service` | SNMP | — |
| `nas_temp` | NAS 整机温度 | ◐ thermals 间接覆盖 |
| `dsm_version` | 系统版本（群晖等） | ◐ `platform_detect` 有版本，未做判定 |
| `backup_status` | 备份任务状态 | — |
| `shared_perms` | 共享目录权限 | — |
| `ups_status` | UPS 状态 | — |
| `user_stats` | 用户与容量配额 | — |
| `log_disk` | 日志分区空间 | — |
| `media_scanner` | 媒体索引服务 | — |
| `cron_conflicts` | 定时任务冲突 | — |

## security 安全（1/11）

| 检测项 | 含义 | 状态 | 备注 |
|---|---|:--:|---|
| `port_scan` | 危险端口暴露 | ✅ | Telnet / 未加密 Docker API |
| `ssh_root` | 是否允许 root 登录 | — | 待补，高价值 |
| `ssh_config` | SSH 配置审计 | — | 待补 |
| `firewall` | 防火墙状态 | — | 待补 |
| `fail2ban` | 防暴破 | — | 待补 |
| `login_failures` | 登录失败次数 | — | 待补 |
| `ssl_cert` | 证书有效期 | — | 待补 |
| `ssl_cert_check` | 证书链 / 签发者 | — | 原项目在算剩余天数上有过 BUG（显示 -1148 天） |
| `openssl_version` | OpenSSL 版本 | — | 待补 |
| `clamav_check` | 杀毒引擎 | — | 待补 |
| `selinux` | SELinux 状态 | — | 待补 |

## ai 算力（2/19）

| 检测项 | 含义 | 状态 | 备注 |
|---|---|:--:|---|
| `gpu_detected` | AI 加速器识别 | ✅ | 7 类芯片真实探测，强于原实现 |
| `ascend_checker` | 昇腾 | ✅ | `/usr/local/Ascend` + `/dev/davinci*` |
| `gpu_memory_checker` | 显存 | ◐ | 部分读取 |
| `onnx_model_checker` | ONNX 运行时 | ◐ | 有真实推理测试，无模型格式检查 |
| `cudnn_checker` | cuDNN | — | 待补 |
| `gpu_utilization_checker` | 显存/算力利用率 | — | 待补 |
| `tensorflow_checker` | TensorFlow | — | 待补 |
| `keras_checker` | Keras | — | 待补 |
| `paddlepaddle_checker` | PaddlePaddle | — | 待补 |
| `openvino_checker` | OpenVINO | — | 待补 |
| `onednn_checker` | oneDNN | — | 待补 |
| `model_format_checker` | 模型文件格式 | — | 待补 |
| `nvidia_container_checker` | NVIDIA 容器运行时 | — | 待补 |
| `triton_checker` | Triton 推理服务 | — | 待补 |
| `torchserve_checker` | TorchServe | — | 待补 |
| `tensorflow_serving_checker` | TF Serving | — | 待补 |
| `mlflow_checker` | MLflow | — | 待补 |
| `kubeflow_checker` | Kubeflow | — | 待补 |
| `version_checker` | AI 组件版本汇总 | — | 待补 |

## usb 外设（0/4）

`usb_devices`、`usb_permissions`、`usb_power`、`usb_storage` 全部未实现。
NAS 场景实际价值有限（主要在 ARM 盒子的 USB 硬盘位、UPS 串口），优先级最低。

---

## 前身没有、当前独有的能力

对照不是单向下风，下面这些是前身项目**没有**的：

| 能力 | 说明 |
|---|---|
| **13 类 NAS 平台识别** | DSM / QTS / TrueNAS / unRAID / TOS / UGOS / OMV / CasaOS / fnOS / Proxmox / OpenWrt / 通用 Linux / Windows / macOS，含容器与虚拟化判断 |
| **Windows / macOS 采集** | 前身基本只跑 Linux（Jetson + RK），当前三平台可用 |
| **真实推理测试** | 不看参数表，实跑 PyTorch / ONNX / NumPy 看是否能出结果 |
| **零第三方依赖** | 纯标准库单文件，任意机器可跑；前身需要 6 个 pip 包 |
| **判定纪律** | 读不到 ≠ 坏掉；AI 算力是加分项不参与合格判定；严重问题总分封顶 |

---

## 建议的补齐顺序

按"对目标用户价值 / 实现成本"排序，不建议按原分类顺序补：

1. **安全三件套**（`ssh_root`、`firewall`、`ssl_cert`）—— 纯读配置，成本极低，NAS 用户最在意，且是二手验机场景的硬需求。
2. **NAS 服务真实探测**（`smb` / `nfs` / `webdav`）—— 从"端口在听"升级到"协议能握手"，这是通用 NAS 工具的分水岭。
3. **`storage_trend` + 历史库** —— 直接照搬 `reference/code/compare.py` 的 schema，让报告从快照变成趋势。
4. **`io_wait` / `process_count`** —— 排查"NAS 变慢"的根因，成本低。
5. AI 框架（19 项）—— 除非明确面向 AI 服务器用户，否则最后做，且应按 `--profile` 开关而非默认开。

---

*原始来源：`reference/legacy/docs/CODE_AUDIT_REPORT.md`（92 个检测器文件清单）、`BUG_SUMMARY_V4.1.md`（分类统计）、`MEMO.md`（功能矩阵）*
