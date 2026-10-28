# nastool

**通用 NAS 设备检测工具** — 一条命令看清一台 NAS 的家底：什么系统、什么硬件、硬盘阵列还健康吗、网络是不是千兆、跑了哪些服务、能不能跑本地 AI，最后给一个 0-100 的健康分。

- 不依赖任何后端，单机独立运行（纯 Python 标准库实现，零第三方依赖）
- 不修改被检测设备（唯一的写入是测速用的临时文件，跑完自动删除）
- 支持成品 NAS、自建 NAS 系统、通用 Linux / Windows / macOS
- 输出终端 / JSON / HTML 三种报告，退出码可直接接定时巡检

```text
  nastool v0.2.0 — 通用 NAS 设备检测

  ▶ 识别系统平台...
  ▶ 采集设备信息...
  ▶ 检测存储（/volume1）...
  ▶ 检查网络...
  ▶ 探测运行中的服务...
  ▶ 检测 AI 算力...

  健康评分  92/100  A 级
  状态良好，可放心使用
```

---

## 1. 它解决什么问题

买了 / 接手了一台 NAS，通常要回答这几个问题：

| 问题 | nastool 的回答 |
|---|---|
| 这是什么机器？装的什么系统？ | 识别群晖 DSM / 威联通 QTS / TrueNAS / unRAID / OMV / CasaOS / 飞牛 / 通用 Linux / Windows，并给出型号、序列号、架构、内核 |
| 硬件够用吗？会不会热？ | CPU 型号核心数、内存占用、温度传感器、是否跑在容器/虚拟机里 |
| 硬盘和阵列还健康吗？ | 物理盘清单、挂载点用量、inode、md/RAID 降级与重建进度、ZFS/Btrfs 状态、SMART 健康与坏道计数、顺序读写速度 |
| 网络是千兆还是百兆？ | 每块网卡的 IP / 速率 / 双工 / MAC，网关、DNS、外网，以及对端端口可达性 |
| 它现在在跑什么？ | SMB/NFS/SSH/Web/Docker/媒体服务等已知服务与端口，Docker 容器清单 |
| 能不能跑本地 AI？ | NVIDIA / AMD / Rockchip / 昇腾 / Intel / 算能 / Coral 加速器识别 + 真实推理测试 |
| 整体到底行不行？ | 0-100 健康分 + A/B/C/D 等级 + 按严重程度排序的问题清单与修复建议 |

---

## 2. 安装

```bash
# 直接运行，无需安装
python3 -m nastool

# 或安装成命令
pip install -e .
nastool --version
```

要求 Python ≥ 3.8。**没有第三方依赖**；`PyYAML` 只在读取可选配置文件时需要。

---

## 3. 快速开始

```bash
nastool                                  # 本机检测，终端报告
nastool -o all --out-dir ./reports       # 终端 + JSON + HTML
nastool --storage-path /volume1          # 指定要体检的数据盘
nastool --no-speed-test                  # 跳过读写测速（更快，适合定时巡检）
nastool --peer 192.168.1.10:445          # 顺手测对端 SMB 是否可达
nastool --push webhook --push-url https://example.com/hook   # 结果推送到自己的接口
```

### 常用参数

| 参数 | 说明 |
|---|---|
| `--storage-path PATH` | 检测哪个数据路径；默认自动挑选（优先 /volume1、/share/… 等 NAS 数据盘，且必须可写） |
| `--peer HOST:PORT` | 对端连通性检查，可重复或逗号分隔 |
| `-o terminal\|json\|html\|all` | 输出格式，默认 `terminal` |
| `--out-dir DIR` | 报告保存目录 |
| `--no-speed-test` | 跳过读写测速 |
| `--no-smart` | 跳过 SMART |
| `--no-ai` | 跳过 AI 算力与推理测试 |
| `--no-internet` | 跳过外网连通检查 |
| `--no-color` / `-q` | 无色输出 / 静默模式 |

### 退出码

| 码 | 含义 |
|---|---|
| `0` | 状态正常，无严重问题 |
| `1` | 存在严重问题（存储不可写、阵列降级、磁盘 SMART 失败、温度过高等） |
| `2` | 参数错误或运行异常 |

> 定时巡检直接看退出码即可：`0 * * * * /usr/local/bin/nastool -q -o json || 告警`

---

## 4. 能检测什么

### 平台识别
成品 NAS：Synology DSM、QNAP QTS、TrueNAS SCALE、unRAID、TerraMaster TOS、绿联 UGOS
自建 NAS 系统：OpenMediaVault、CasaOS、飞牛 fnOS、Proxmox VE、OpenWrt
通用平台：Debian/Ubuntu 等 Linux 发行版、Windows、macOS
同时判断是否运行在 Docker / LXC / Kubernetes / 常见虚拟机内，并提示哪些项会因权限或容器隔离而不可见。

### 存储
- 目标路径存在性与可写性（真实建文件验证，不只看权限位）
- 容量、剩余空间、使用率、inode 使用率、只读挂载检测
- 物理盘清单（型号、容量、HDD/SSD）
- RAID：`/proc/mdstat` 解析（含降级与重建进度）、ZFS `zpool` 状态与成员在线数、Btrfs 设备错误计数
- SMART：健康结论、温度、通电时长、重映射/待定扇区
- 顺序读写速度（50MB 实测，含 `fsync`，可跳过）

### 网络
- 网卡：IP / 掩码 / MAC / 速率 / 双工 / MTU / 是否无线；链路本地地址（169.254）单独标注
- 连通性：网关、DNS（含 DNS 服务器）、外网
- 对端：任意 `host:port` TCP 可达性与 RTT

### 服务
SMB / NFS / SSH / Web / Docker API / Plex / Jellyfin / Emby / Transmission / qBittorrent / 数据库等常见服务的端口对照，Docker 容器清单，以及 Telnet、未加密 Docker API、SMB 全网卡监听等风险提示。

### AI 算力
| 厂商 | 识别方式 |
|---|---|
| NVIDIA | `nvidia-smi`、Jetson `/dev/nvidia0`、CUDA |
| AMD | `/dev/kfd`、`rocm-smi` |
| Rockchip | `/dev/rknpu`、RKNN SDK |
| 华为昇腾 | `/usr/local/Ascend`、`/dev/davinci*` |
| Intel | `/dev/dri/renderD128`、`/dev/intel-npu`、Movidius |
| 算能 Sophgo | `/dev/sophon*` |
| Google | Coral Edge TPU `/dev/apex_*` |
| CPU 兜底 | PyTorch / ONNX Runtime / NumPy 真实跑一次推理 |

> AI 能力是**加分项，不参与合格判定**。一台只做文件存储的 NAS 不应该因为没有 PyTorch 被判为不健康。

---

## 5. 评分规则

总分 100，四个维度加权：

| 维度 | 权重 | 扣分点 |
|---|---|---|
| 存储 | 40 | 路径不可写 / 空间不足 / 阵列异常 / SMART 失败 / 读写异常 |
| 网络 | 25 | 无有效 IP / 百兆链路 / 网关与 DNS / 对端不可达 |
| 系统 | 20 | CPU 内存读不到 / 内存压力 / 温度过高 |
| 服务 | 15 | 无文件共享服务 / Telnet 或未加密 Docker API 暴露 |

等级：`A ≥90`、`B ≥80`、`C ≥60`、`D <60`。
**只要存在严重问题，总分封顶 59（落到 D 级）**——避免出现「A 级但硬盘快挂了」的矛盾结论。

AI 能力单独给一个参考分，不计入总分。

---

## 6. 输出

- **terminal**：按「平台 → 系统 → 存储 → 网络 → 服务 → AI → 结论」排列，直接看
- **JSON**：字段稳定（`report_version: 2.0`），适合流水线消费、入库、对比历史
- **HTML**：单文件、零外部依赖，可离线打开、可打印，适合发给别人或存档

---

## 7. 上报通道（可选，默认关闭）

nastool 默认**不联网**，只输出本地报告。需要把结果送到别处时再加：

```bash
# 通用 webhook：把完整 JSON POST 到你自己的接口
nastool -q -o json --push webhook --push-url https://example.com/hook --push-token xxx

# AINAS 接入：登记设备并归档诊断报告（AINAS 是另一款产品，此处仅为可选连接器）
nastool --push ainas --nas-host 192.168.1.10 --nas-port 8000
```

新增通道只需继承 `nastool/connectors/base.py` 的 `BaseConnector` 并在 `connectors/__init__.py` 注册。

---

## 8. 权限与限制

- **SMART / RAID / 温度**需要 root（Windows 需管理员）。非 root 会跳过并明确提示，不会报错。
- **容器内**（Docker / LXC）看不到宿主机磁盘与传感器，报告会标注 `运行环境: 容器`。要做完整硬件体检请在宿主机上跑。
- 部分检测依赖系统命令，缺少时自动降级：
  `lsblk` `smartctl` `zpool` `btrfs` `ss` `ip`；`nvidia-smi` `rocm-smi` `vainfo`
- RAID 卡（硬件阵列）后面的磁盘，SMART 通常读不到，这是硬件限制，不是工具问题。
- 速度测试会真实写入 50MB 临时文件（跑完删除），在慢盘或机械盘上耗时约数十秒。

---

## 9. 项目结构

```
nastool/
├── __init__.py          版本与公开 API
├── cli.py               命令行入口
├── core/
│   ├── util.py          跨平台执行/读取（编码、降级、默认路径选择）
│   ├── platform_detect.py  NAS 平台识别
│   ├── device.py        CPU / 内存 / 主板 / 温度 / 虚拟化
│   ├── storage.py       容量 / 阵列 / SMART / 测速
│   ├── network.py       网卡 / 连通性 / 对端
│   ├── services.py      服务与端口
│   ├── ai_accel.py      AI 加速器与推理
│   ├── scoring.py       健康评分
│   └── runner.py        编排，产出 DiagnosticResult
├── reporters/           terminal / json / html
├── adapters/            特定硬件平台的专项检查
├── connectors/          webhook / ainas（可选）
docs/                    检测项路线图、设计笔记
reference/               前身项目设计资产（不参与构建）
tests/
```

各报告器只依赖 `DiagnosticResult`，新增输出格式不需要动采集代码。

---

## 10. 开发

```bash
pip install -e ".[dev]"
python -m pytest -q            # 18 项测试，不依赖真实硬件
python -m nastool --no-speed-test -o all
```

设计约定：
- 任何外部命令失败都不得抛异常，采集器一律降级并记录原因
- 判定口径要保守：读不到 ≠ 坏掉。「无法判定」只能算提示，不能算故障
- 报告结论必须与问题清单一致：有严重问题就不允许给 A

---

## 11. 与 AINAS 的关系

nastool 是**独立产品**，与 AINAS（家庭 AI 媒体 NAS）没有任何代码依赖：

- 不接 AINAS 也能完整使用，`connectors/ainas.py` 不启用时根本不会被 import
- AINAS 接入只是一个可选连接器，用于把设备登记进 AINAS 设备列表并归档诊断报告
- 两者的版本线、发布节奏互不影响

---

## 12. 设计参考与前身资产

nastool 有一个前身项目（演进到 v7.1.0-beta，92 个检测器、6 个子包）。它的代码内核已随归档丢失，但**设计文档保留下来了**，已提取到本仓库：

| 文档 | 内容 |
|---|---|
| [`docs/CHECKS-ROADMAP.md`](docs/CHECKS-ROADMAP.md) | 92 项检测清单 + 当前实现状态逐项对照（当前已实现 22%） |
| [`docs/DESIGN-NOTES.md`](docs/DESIGN-NOTES.md) | 准确性保障层、profile 场景化、自适应阈值、行动计划、修复风险模型 |
| [`reference/README.md`](reference/README.md) | 前身项目全貌、可复用资产清单、刻意排除的部分 |

**`reference/` 目录不参与构建**（`pyproject.toml` 只打包 `nastool*`）。里面的代码依赖已丢失的 `nastool_core`，仅作算法与结构参考，**不可直接运行**。

