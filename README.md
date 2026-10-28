# nastool

**通用 NAS 设备检测工具** — 一条命令看清一台 NAS 的家底，给一个**可以被信任**的健康评分。

```text
  nastool 0.3.1  ·  场景 nas  ·  2026-10-28 15:24:57

  主机    mynas
  平台    群晖 DSM 7.2  ·  aarch64  ·  内核 4.4.180（DS920+）
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

- **零第三方依赖**，纯标准库：任意有 Python 3.8+ 的机器直接跑，包括离线设备
- **只读检测**，唯一写入是测速用的临时文件（跑完删除）
- **支持成品 NAS、自建 NAS 系统、通用 Linux / Windows / macOS**
- 输出终端 / JSON / HTML，退出码可直接接定时巡检

---

## 它和别的检测工具差在哪

绝大多数体检工具会给你一个漂亮的总分，下面挂着一堆需要处理的问题。**用户学会的第一件事是别看那个分数。**

这个项目在三个地方做了不同的选择：

### 1. 「读不到」是独立状态，不是结论

```
✗ 硬盘 SMART 健康    1 块硬盘 SMART 未通过          ← 测了，确实有问题
? 硬盘 SMART 健康    缺少依赖：smartctl，本次未检测   ← 没测成，不知道
```

非 root、容器内、硬件 RAID 卡后面、USB 硬盘盒——这些情况下 SMART 全都读不到。把它记成「正常」是掩盖问题，记成「故障」是制造假故障。所以它是第五种状态 `UNKNOWN`：**不扣分，但拉低覆盖度**。

报告会明确告诉你 `覆盖 20/20（100%）` 还是 `覆盖 8/19（42%）`——后者不会给你 A 级。

### 2. 分数会被强行压低

加权平均之后还有两条规则：

| 触发 | 封顶 |
|---|---|
| 存在任意一项严重问题 | **59（D 级）** |
| 盲区 ≥ 50% | 74（C 级） |
| 盲区 ≥ 30% | 84（B 级） |

避免出现「97 分 A 级」下面挂着一块随时要挂的盘。触发原因会写在报告里，不做静默降分。

### 3. 逐项对比，不只比总分

```
  对比  2026-10-20 03:00  →  2026-10-27 03:00
  分数  88 → 85（-3）   B → B

  指标恶化
    · 坏道计数
        reallocated_sector_ct: 0 → 12（+12）
```

**总分只掉 3 分，但那一行 `0 → 12` 才是真正要处理的。** 只比总分的工具永远看不出这种情况。

---

## 安装

```bash
python3 -m nastool          # 直接运行，无需安装
pip install -e .            # 或安装成命令
nastool --version
```

要求 Python ≥ 3.8。**没有第三方依赖**（`PyYAML` 仅读取可选配置文件时需要）。

---

## 快速开始

```bash
nastool                                    # 本机体检
nastool -p verify -o all --out-dir ./rpt   # 二手验机：三份报告一起出
nastool --list-checks                      # 查看全部 55 项检测
nastool --only storage.* --only security.* # 只查存储与安全
nastool --save-history --compare latest    # 存历史并和上次逐项对比
nastool -v                                 # 显示全部项与每项证据
```

完整参数见 [docs/CLI.md](docs/CLI.md)。

### 四个场景

同一台机器，用途不同，「健康」的定义就不同：

| 场景 | 用于 | 特点 |
|---|---|---|
| `nas`（默认） | 家用 / 小办公存储服务器 | 存储 34 分权重，不看 AI |
| `verify` | 买二手机器前验收 | 安全权重提到 18，阈值放宽避免误报 |
| `dev` | 开发机 / 软路由 / PVE 宿主 | 系统与网络优先，容忍高占用 |
| `ai` | Jetson / RK3588 / 昇腾盒子 | 算力占 26 分，缺加速器算严重 |

```bash
nastool -p verify
```

细节见 [docs/PROFILES.md](docs/PROFILES.md)。

---

## 能检测什么

共 **55 项**，分 7 类。逐条说明见 [docs/CHECKS.md](docs/CHECKS.md)，或直接跑 `nastool --list-checks`。

| 分类 | 项数 | 主要内容 |
|---|---|---|
| 存储 | 13 | 路径可写、容量与 inode、只读挂载、物理盘、阵列健康与重建、SMART 健康/坏道/通电时长/温度、读写速度 |
| 系统与硬件 | 10 | CPU/内存可读性、内存与 swap 压力、温度、负载、运行时长、时间同步、I/O 压力、进程数 |
| 网络 | 10 | 网卡与 IP、链路速率与双工、网关、DNS、外网、对端可达、主链路类型、网卡错误计数 |
| 服务与端口 | 8 | 端口清单、文件共享、管理界面、媒体栈、容器运行时、高风险服务、端口暴露范围、未识别端口 |
| 安全 | 8 | SSH root 登录与密码登录、防火墙、暴力破解防护、TLS 证书有效期与自签、SMB 匿名访问、NFS 权限映射 |
| AI 算力 | 4 | 加速硬件识别、推理运行时、真实推理耗时、厂商运行环境 |
| 外设 | 2 | USB 设备、数据盘连接方式（USB 外接盘降速提示） |

**平台识别**：群晖 DSM / 威联通 QTS / TrueNAS / unRAID / 铁威马 / 绿联 / OMV / CasaOS / 飞牛 / Proxmox / OpenWrt / 通用 Linux / Windows / macOS，并判断是否运行在 Docker / LXC / K8s / 虚拟机内。

**AI 算力是参考项**：纯存储 NAS 没有加速器完全正常，标「不适用」而不是「有问题」。只有 `-p ai` 场景下缺加速器才算严重。

---

## 文档

完整文档入口：[**docs/**](docs/README.md)

| 我想 | 读 |
|---|---|
| 知道某个参数的确切含义 | [docs/CLI.md](docs/CLI.md) |
| 搞懂为什么分数是这个数 | [docs/SCORING.md](docs/SCORING.md) |
| 查某一项在判什么、阈值多少 | [docs/CHECKS.md](docs/CHECKS.md) |
| 写脚本消费 JSON 报告 | [docs/OUTPUT.md](docs/OUTPUT.md) |
| 追踪硬盘老化趋势 | [docs/HISTORY.md](docs/HISTORY.md) |
| 排掉「为什么全是不适用」 | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| 加一项新检测 | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)（规范：[docs/STANDARDS.md](docs/STANDARDS.md)） |
| 理解分层为什么这样 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/adr/](docs/adr/) |
| 看改了什么 / 还欠什么 / 踩过什么坑 | [docs/memo/](docs/memo/)（日志 · 技术债 · 踩坑 · 未决问题） |
| 下一版做什么 | [docs/VERSION-PLAN.md](docs/VERSION-PLAN.md) |
| 这东西最终长成什么样、给谁用 | [docs/PRODUCT-PLAN.md](docs/PRODUCT-PLAN.md) |
| 知道还差哪些能力没做 | [docs/CHECKS-ROADMAP.md](docs/CHECKS-ROADMAP.md) |

---

## 上报通道（可选，默认完全离线）

默认不联网，只输出本地报告。需要时可加：

```bash
# 通用 webhook：把完整 JSON POST 到你自己的接口
nastool -q -o json --push webhook --push-url https://example.com/hook --push-token xxx

# AINAS 接入：登记设备并归档诊断报告（可选连接器，不启用时不会被 import）
nastool --push ainas --nas-host 192.168.1.10 --nas-port 8000
```

---

## 权限与限制

- **SMART / RAID / 温度**需要 root（Windows 需管理员）。非 root 时这些项标「不适用」，不会报错
- **容器内**看不到宿主机磁盘与传感器，报告会写明并在建议里提示在宿主机上复检
- 缺 `lsblk` / `smartctl` / `zpool` / `ss` / `openssl` 等命令时自动降级，只是降低覆盖度
- 硬件 RAID 卡后面的磁盘读不到 SMART，这是硬件限制
- 速度测试会真实写入 50MB 临时文件（跑完删除），机械盘上耗时数十秒，`--no-speed-test` 可跳过

排查方法见 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。

---

## 开发

```bash
pip install -e ".[dev]"
python -m pytest -q            # 全部测试，不依赖真实硬件
python tools/selfcheck.py       # 开发规范自检（12 项，含文档与代码一致性）
python -m nastool --no-speed-test -o all
```

**加一项检测 = 写一个函数**（[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)）：

```python
@check("storage.my_check", "我的检查", "storage",
       weight=3, platforms=["linux"], requires=["smart_data"])
def my_check(ctx):
    if not ctx.storage.smart:
        return R(Status.UNKNOWN, "没读到 SMART")
    return R(Status.PASS, "正常",
             evidence=[ev("smartctl", "value", 1, num=1, trend="up_bad")])
```

报告、评分、历史对比全部自动包含它。

改动前请读 [docs/STANDARDS.md](docs/STANDARDS.md)（强制规范），改动后请在
[docs/memo/](docs/memo/) 留一笔——日志、踩坑或技术债，总得留一样。

---

## 与 AINAS 的关系

nastool 是**独立产品**，与 AINAS（家庭 AI 媒体 NAS）没有任何代码依赖：

- 不接 AINAS 也能完整使用，`connectors/ainas.py` 不启用时根本不会被 import
- AINAS 接入只是可选连接器，用于把设备登记进 AINAS 设备列表并归档诊断报告
- 两者的版本线、发布节奏互不影响

---

## 前身项目

nastool 有一个前身（演进到 v7.1.0-beta，92 个检测器、6 个子包）。代码内核已随归档丢失，但设计文档保留下来了：

- [docs/DESIGN-NOTES.md](docs/DESIGN-NOTES.md) — 准确性保障层、场景化、自适应阈值、修复引擎的四级风险模型、12 条真机 BUG 教训
- [docs/CHECKS-ROADMAP.md](docs/CHECKS-ROADMAP.md) — 92 项清单中尚未覆盖的缺口，按价值排序的补齐顺序
- [reference/](reference/) — 前身原始文档与可复用代码片段（**不参与构建，不可直接运行**）

---

MIT License
