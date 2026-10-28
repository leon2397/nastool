# nastool

**通用 NAS 设备检测工具** — 一条命令看清一台 NAS 的家底：什么系统、什么硬件、硬盘阵列还健康吗、网络是不是千兆、跑了哪些服务、能不能跑本地 AI，最后给一个 0-100 的健康分。

- 不依赖任何后端，单机独立运行（纯 Python 标准库实现，零第三方依赖）
- 不修改被检测设备（唯一的写入是测速用的临时文件，跑完自动删除）
- 支持成品 NAS、自建 NAS 系统、通用 Linux / Windows / macOS
- 输出终端 / JSON / HTML 三种报告，退出码可直接接定时巡检

```text
  nastool v0.3.0 — 通用 NAS 设备检测（场景 nas）

  ▶ 存储   ▶ 安全   ▶ 系统与硬件   ▶ 网络   ▶ 服务与端口   ▶ 外设

  nastool 0.3.0  ·  场景 nas  ·  2026-10-28 15:24:57

  主机    mynas
  平台    Linux 5.10.60 · aarch64 · 群晖 DSM
  数据盘  /volume1  ·  3.1 TB 可用 / 7.2 TB

  结论    92 分 · A 级 · 状态良好，可放心使用
  覆盖    48/51 项已判定（94.1%），3 项不适用
  置信    0.91

  分项
    存储        ██████████████████░░  91  权重 34  12/13
    安全        ██████████████████░░  90  权重 10  7/8
    系统与硬件  ████████████████████  96  权重 16  10/10
    网络        █████████████████░░░  86  权重 18  9/10
    服务与端口  ███████████████████░  95  权重 16  8/8
    外设        ████████████████████ 100  权重 6   2/2
```

---

## 1. 它解决什么问题

买了 / 接手了一台 NAS，通常要回答这几个问题：

| 问题 | nastool 的回答 |
|---|---|
| 这是什么机器？装的什么系统？ | 识别群晖 DSM / 威联通 QTS / TrueNAS / unRAID / 铁威马 / 绿联 / OMV / CasaOS / 飞牛 / Proxmox / OpenWrt / 通用 Linux / Windows / macOS，并给出型号、架构、内核版本 |
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
nastool -p verify -o all --out-dir ./reports   # 二手验机：三份报告一起出
nastool --list-checks                    # 查看全部检测项（55 项）
nastool --storage-path /volume1          # 指定要体检的数据盘
nastool --only storage.* --only security.*     # 只查存储与安全
nastool --save-history --compare latest  # 存历史并和上次逐项对比
nastool --peer 192.168.1.10:445          # 顺手测对端 SMB 是否可达
nastool --push webhook --push-url https://example.com/hook   # 结果推到自己接口
```

### 常用参数

| 参数 | 说明 |
|---|---|
| `--storage-path PATH` | 检测哪个数据路径；默认自动挑选（优先 /volume1、/share/… 等 NAS 数据盘，且必须可写） |
| `-p, --profile` | 场景：`nas`（默认）/ `verify` 二手验机 / `dev` 开发机 / `ai` 推理设备。**决定权重、阈值与检测范围** |
| `--only PATTERN` | 只跑匹配的检查项，支持通配（`storage.*`、`*.smart_*`） |
| `--skip PATTERN` | 跳过匹配的检查项 |
| `--enable CATEGORY` | 在场景基础上追加分类（如 nas 场景下加 `ai`） |
| `--list-checks` | 列出全部检测项及依赖，不用跑检测 |
| `--peer HOST:PORT` | 对端连通性检查，可重复或逗号分隔 |
| `-o terminal\|json\|html\|all` | 输出格式，默认 `terminal` |
| `--save-history` | 本次结果存入历史库（默认 `~/.nastool/history.db`） |
| `--compare [ID\|latest]` | 与历史记录逐项对比（不只是比总分） |
| `--history [N]` | 列出最近 N 次记录 |
| `--no-speed-test` / `--no-smart` / `--no-ai` / `--no-internet` | 跳过对应耗时项 |
| `-v` | 显示全部检查项与每项证据 |
| `--no-color` / `-q` | 无色输出 / 静默模式 |

### 退出码

| 码 | 含义 |
|---|---|
| `0` | 无严重问题 |
| `1` | 存在严重问题（存储不可写、阵列降级、SMART 失败、温度过高等） |
| `2` | 参数错误或运行异常 |

> 定时巡检直接看退出码即可：`0 * * * * /usr/local/bin/nastool -q -o json || 告警`

---

## 4. 能检测什么

共 **55 个检测项**，分 7 类。`nastool --list-checks` 可查看全部项及其平台/依赖要求。

| 分类 | 项数 | 主要内容 |
|---|---|---|
| 存储 | 13 | 路径存在与可写、容量与 inode、只读挂载、物理盘、阵列健康与重建、SMART 健康/坏道/通电时长/温度、读写速度 |
| 系统与硬件 | 10 | CPU/内存可读性、内存与 swap 压力、温度、负载、运行时长、时间同步、I/O 压力、进程数 |
| 网络 | 10 | 网卡与 IP、链路速率与双工、网关、DNS、外网、对端可达、主链路类型、网卡错误计数 |
| 服务与端口 | 8 | 端口清单、文件共享、管理界面、媒体栈、容器运行时、高风险服务、端口暴露范围、未识别端口 |
| 安全 | 8 | SSH root 登录与密码登录、防火墙、暴力破解防护、TLS 证书有效期与自签、SMB 匿名访问、NFS 权限映射 |
| AI 算力 | 4 | 加速硬件识别、推理运行时、真实推理耗时、厂商运行环境 |
| 外设 | 2 | USB 设备、数据盘连接方式（USB 外接盘降速提示） |

### 平台识别
成品 NAS：Synology DSM、QNAP QTS、TrueNAS SCALE、unRAID、TerraMaster TOS、绿联 UGOS
自建 NAS 系统：OpenMediaVault、CasaOS、飞牛 fnOS、Proxmox VE、OpenWrt
通用平台：Debian/Ubuntu 等 Linux 发行版、Windows、macOS
同时判断是否运行在 Docker / LXC / Kubernetes / 常见虚拟机内，并提示哪些项会因权限或容器隔离而不可见。

### 存储细节
- 目标路径存在性与可写性（真实建文件验证，不只看权限位）
- 容量、剩余空间、使用率、inode 使用率、只读挂载检测
- 物理盘清单（型号、容量、HDD/SSD）
- RAID：`/proc/mdstat` 解析（含降级与重建进度）、ZFS `zpool` 状态与成员在线数、Btrfs 设备错误计数
- SMART：健康结论、温度、通电时长、重映射/待定扇区
- 顺序读写速度（50MB 实测，含 `fsync`，可跳过）

### 网络细节
- 网卡：IP / 掩码 / MAC / 速率 / 双工 / MTU / 是否无线；链路本地地址（169.254）单独标注
- 连通性：网关、DNS（含 DNS 服务器）、外网
- 对端：任意 `host:port` TCP 可达性与 RTT

### 服务与安全细节
SMB / NFS / SSH / Web / Docker API / Plex / Jellyfin / Emby / Transmission / qBittorrent / 数据库等常见服务对照，Docker 容器清单，Telnet、未加密 Docker API、SMB 全网卡监听等风险提示；只读读取 `sshd_config`、`smb.conf`、`/etc/exports`、证书与防火墙规则，判断是否存在 root 直登、SMB 匿名共享、NFS `no_root_squash`、证书过期等典型失配。

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

> 在 `nas` 场景下 AI 默认不启用——一台只做文件存储的 NAS 不应该因为没有 PyTorch 就被判为不健康。`verify` / `dev` / `ai` 场景会自动启用（`verify` 权重为 0，仅作参考展示）；`nas` 下需要时用 `--enable ai` 追加，追加的分类会拿到保底权重 8。

---

## 5. 评分规则

总分 100，按**场景权重**对分类得分加权。分类得分 = 该类已判定项的加权通过率（通过 1.0 / 告警 0.5 / 严重 0）。

| 分类 | `nas` | `verify` | `dev` | `ai` |
|---|---|---|---|---|
| 存储 | 34 | 32 | 20 | 24 |
| 系统与硬件 | 16 | 14 | 20 | 16 |
| 网络 | 18 | 12 | 18 | 14 |
| 服务与端口 | 16 | 14 | 14 | 10 |
| 安全 | 10 | 18 | 18 | 10 |
| 外设 | 6 | 6 | — | — |
| AI 算力 | —（`--enable ai` 时 8） | 0（仅参考） | 10 | 26 |

`—` 表示该场景不启用这个分类，不参与评分。`--enable <分类>` 可以在任意场景追加分类，追加时若原权重为 0 则给保底权重 8。

等级：`A ≥90`、`B ≥80`、`C ≥60`、`D <60`。

**两条封顶规则**——这是报告可信度的关键：

| 触发条件 | 封顶 | 原因 |
|---|---|---|
| 存在任意一项严重问题 | 59（D） | 避免「97 分 A 级」下面挂着一块随时要挂的盘 |
| 适用项中不可判定 ≥ 50% | 74（C） | 一半项目没测到，不能给高等级 |
| 适用项中不可判定 ≥ 30% | 84（B） | 盲区偏大，结论只能算倾向 |

两条规则会在报告里明确写出触发原因（`cap_reason`），不做静默降分。

**不可判定（UNKNOWN）不扣分**：读不到 SMART 既不算「硬盘坏了」也不算「硬盘没事」，它只降低覆盖度。覆盖度分母是**适用项**（`总数 − 不适用`），不是全部项——在 Windows 上不会因为 31 项 Linux 专属检测拿不到数据就把覆盖率算成 39%。

---

## 6. 输出

三种格式共用同一份数据模型（`nastool/model.py` 的 `Report`），因此字段永远一致：

- **terminal**：结论 → 覆盖/置信 → 检测限制 → 分项条形图 → 按分类折叠的明细 → 清单 → 页脚，直接看
- **JSON**：`report_version: 3.0`。顶层 `meta / score / coverage / checks[] / platform / facts`；每个 check 带 `status / summary / detail / suggestion / confidence / evidence[]`
- **HTML**：单文件、零外部资源，含分数环、覆盖条、分项条、可展开的证据、硬件清单，可离线打开、可打印

`checks[]` 是报告的核心——每一行都是一条可追溯的结论：

```json
{
  "id": "storage.smart_bad_sectors",
  "category": "storage",
  "status": "warn",
  "summary": "重映射扇区 8 个",
  "confidence": 0.9,
  "evidence": [
    {"source": "smartctl", "key": "Reallocated_Sector_Ct",
     "value": "8", "num": 8, "trend": "up_bad",
     "note": "非零即为隐患，持续增长说明盘面在退化"}
  ]
}
```

`evidence[].trend` 是给历史对比用的方向语义：`up_bad`（涨了是坏事，如坏道数）、`up_good`（涨了是好事）、空（中性，如通电时长——涨了不代表变差）。没有这个标注，历史 diff 会把「多跑了 0.1 小时」报成「指标恶化」。

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
- **容器内**（Docker / LXC）看不到宿主机磁盘与传感器，报告会在「检测限制」里写明「运行在 X 容器内：SMART / RAID / 温度等项目可能不可见」。要做完整硬件体检请在宿主机上跑。
- 部分检测依赖系统命令，缺少时自动降级：
  `lsblk` `smartctl` `zpool` `btrfs` `ss` `ip`；`nvidia-smi` `rocm-smi` `vainfo`
- RAID 卡（硬件阵列）后面的磁盘，SMART 通常读不到，这是硬件限制，不是工具问题。
- 速度测试会真实写入 50MB 临时文件（跑完删除），在慢盘或机械盘上耗时约数十秒。

---

## 9. 项目结构

四层架构，依赖方向单向：`collect → checks → 聚合 → 呈现`。**新增一项检测 = 新增一个带 `@check` 的函数**，不改其他地方。

```
nastool/
├── model.py        契约层：Status / Evidence / CheckResult / Score / Coverage / Report
├── registry.py     @check 装饰器与注册表（一切扩展的入口）
├── profiles.py     场景定义：权重、阈值、启用的分类
├── context.py      采集上下文（惰性求值 + 能力探测 + 阈值解析）
│
├── collect/        采集层：只拿事实，不做判断
│   ├── platform.py  NAS 平台与虚拟化识别
│   ├── device.py    CPU / 内存 / 温度
│   ├── storage.py   容量 / 阵列 / SMART / 测速
│   ├── network.py   网卡 / 连通性
│   ├── services.py  服务与端口
│   ├── security.py  SSH / 证书 / SMB / NFS / 防火墙（只读）
│   ├── ai_accel.py  加速器与推理
│   └── util.py      跨平台执行 / 编码回退 / 默认路径
│
├── checks/         判定层：一类一个模块，共 55 项
│   ├── _base.py    R() 与 ev() 两个构造助手
│   └── storage.py / system.py / network.py / services.py / security.py / ai.py / usb.py
│
├── engine.py       编排：跑检查、超时、异常收敛为 UNKNOWN、生成设备指纹
├── scoring.py      聚合：分类得分 → 总分 → 两条封顶规则 + 覆盖度 + 置信度
├── history.py      历史库（SQLite，存完整报告 JSON）
├── diff.py         逐项对比：新故障 / 仍故障 / 指标恶化 / 已修复 / 新增 / 移除
│
├── reporters/      terminal / json / html
├── connectors/     webhook / ainas（可选，默认不启用）
└── cli.py          命令行入口
```

几个刻意的设计：

- **采集层不做判断。** `collect/` 里没有 `warnings`、`errors`、`ok` 这类字段——判断只允许出现在 `checks/`。否则同一个结论会在两个地方各写一遍，迟早对不上。
- **上下文惰性求值。** 55 项检查共用一次采集结果，`ctx.storage` 第一次访问才真正执行，避免每项检查各扫一遍磁盘。
- **报告器不碰采集。** 三个报告器只依赖 `Report`，加一种输出格式不需要改检测逻辑。
- **异常不等于故障。** `engine._run_one()` 把检查和系统异常都收敛成 `UNKNOWN` + `error` 字段，而不是 `FAIL`。

---

## 10. 开发

```bash
pip install -e ".[dev]"
python -m pytest -q                          # 30 项测试，不依赖真实硬件
python -m nastool --no-speed-test -o all     # 端到端跑一次
```

加一项检测：

```python
# nastool/checks/storage.py
@check("storage.my_check", "我的检查", category="storage",
       weight=3, platforms=("linux",), requires=("root",))
def my_check(ctx):
    if not ctx.storage.disks:
        return R(Status.UNKNOWN, "没读到磁盘", confidence=0.2)
    return R(Status.PASS, "正常",
             evidence=[ev("lsblk", "disks", len(ctx.storage.disks), num=..., trend="up_bad")])
```

注册即生效：终端、JSON、HTML、评分、历史对比全部自动包含它。

设计约定（这几条是产品的底线，不要为了「好看」而违反）：
- 任何外部命令失败都不得抛异常，采集器一律降级并记录原因
- **读不到 ≠ 坏掉**：拿不到数据用 `Status.UNKNOWN`，它不扣分但降低覆盖度；只有确认异常才用 `FAIL`
- 每条结论都要有 `evidence`，说不清依据的检查不要写
- 数值型证据必须标 `trend`（`up_bad` / `up_good` / 空），否则历史对比会误报
- 报告结论必须与问题清单一致：有严重问题就不允许给 A，盲区过大就不允许给高等级

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
| [`docs/CHECKS-ROADMAP.md`](docs/CHECKS-ROADMAP.md) | 当前 55 项实现清单 + 前身 92 项中尚未覆盖的缺口，按价值排序的补齐顺序 |
| [`docs/DESIGN-NOTES.md`](docs/DESIGN-NOTES.md) | 准确性保障层、profile 场景化、自适应阈值、行动计划、修复风险模型 |
| [`reference/README.md`](reference/README.md) | 前身项目全貌、可复用资产清单、刻意排除的部分 |

> 前身的 92 项清单里，AI 部分（19 项框架级检测器）本项目**刻意不补**——逐个点名 TensorFlow / Triton / MLflow 没有边界，也不能说明设备是否健康。取而代之的是真跑一次推理（`ai.runtime` + `ai.inference_perf`），能同时证明运行时、驱动、算力三件事。理由写在路线图里。

**`reference/` 目录不参与构建**（`pyproject.toml` 只打包 `nastool*`）。里面的代码依赖已丢失的 `nastool_core`，仅作算法与结构参考，**不可直接运行**。

