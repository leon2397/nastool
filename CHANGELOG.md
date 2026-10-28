# 变更日志

## 0.3.4 — 多源数据融合与一致性验证（0.4.0 的第一步）

**产品行为有变化**：温度不再只取一个来源，报告可能新增「温度读数存在争议」的提示。

### 补充：产品化规划（同版本追加）

在多源融合之后追加了 [docs/PRODUCT-PLAN.md](docs/PRODUCT-PLAN.md)——产品层面的
"长成什么样"，与 [docs/VERSION-PLAN.md](docs/VERSION-PLAN.md) 的"什么时候动手"分开。

同批追加的打包基础修复：

- **新增 `LICENSE`（MIT 正本）**——此前 README 与 `pyproject.toml` 都声明 MIT，
  但仓库里没有许可文件，从未提交过。法律基础缺失（DEBT-015）。
- **新增 `MANIFEST.in`**——`reference/`（前身归档，245 KB）不进构建产物；
  实测 sdist 从含归档变为 98 个文件、含 `LICENSE`、不含 `reference/`。
- `pyproject.toml` 改用 SPDX license 表达式（`license = "MIT"` + `license-files`），
  消除 setuptools 的弃用警告（2027-02-18 后旧写法不再受支持）。

`selfcheck` 新增第 13 项「产品化规划一致」：规划与版本计划必须双向引用、
规划引用的债与问题必须已排期、`LICENSE` 必须存在。13/13 绿。

### 新增

- `nastool/fusion.py` —— 通用融合引擎
  - 5 种融合方法：`WEIGHTED_AVERAGE` / `MEDIAN` / `MAJORITY_VOTE` / `TRUSTED_SOURCE` / `MAX`
  - 一致性验证：极差超容差即判为不一致，≥3 个来源时才判离群
  - 测量点归一化：`cpu` / `soc` / `cpu-thermal` / `x86_pkg_temp` → `cpu`
  - 按量纲分列的容差表（温度 5°C、使用率 2 个百分点、通电时长 24 小时……）
- 报告层：置信度低于 0.7 的判定项在终端与 HTML 标注「⚠ 结论存疑」

### 变更

- **温度采集改为保留全部来源**：原先 hwmon 有值就不读 thermal_zone，现在两个都读并标注来源
- **温度判定改用 MAX 融合**：原先取最热传感器，现在跨测量点取最高值（同点内做一致性验证）
- `system.thermal` 在同测量点两来源相差 > 5°C 时返回 WARN「温度读数存在争议」，
  detail 列出两个来源的具体读数，置信度降至 0.5
- `nastool/collect/device.py` 的 `ThermalInfo` 新增 `source` 字段

### 修复

- `tools/selfcheck.py` 的锚点算法未剥离 emoji，导致 `### ✅ DEBT-xxx` 这类标题的
  锚点算成 `-debt-xxx`（正确应为 `debt-xxx`）。此前无引用所以未暴露

### 设计要点

融合放在**判定层**而非采集层：采集层保留多个来源是「事实的完整性」，不违反
「采集层不判断」（ADR-0002）。温度用 MAX 而非平均——平均会低估散热风险。

详见 [ADR-0008](docs/adr/0008-multi-source-fusion.md)。

### 测试

54 项（0.3.3 为 31 项）。新增 `tests/test_fusion.py` 23 项，并用**变异测试**验证
这些测试真的有牙齿（把 MAX 改成平均、归一化全部映射到 cpu、冲突仍返回 PASS，
三种变异均被精确捕获）。

---

## 0.3.3 — 版本计划

产品运行行为不变。本次补的是**排期的唯一权威来源**。

### 新增

- `docs/VERSION-PLAN.md` —— 0.4.0 / 0.5.0 / 0.6.0 / 1.0.0 四个节点，每节含目标、为什么是现在、
  包含项（对应 DEBT / Q 编号）、**破坏性变更预告**、验收标准、明确不做的内容。
  另含版本策略（0.x 允许破坏性变更、1.0 起语义化）、依赖关系图、**1.0 门槛清单**、
  **明确不做的决定**表（自动修复 / 修复脚本 / 批量体检 / 第三方依赖 / AI 框架点名）。
- `selfcheck` 第 11 项检查：技术债与未决问题必须在版本计划中有归属，否则报「未排期」。
  当前覆盖 13 条未修债 + 10 个开放问题。

### 变更

- `docs/CHECKS-ROADMAP.md` 的「建议的补齐顺序」改为「价值判断（排期见版本计划）」——
  它回答"值不值得做"，版本计划回答"什么时候做"，两处不再各排一次。

### 修复

- `docs/VERSION-PLAN.md` 中 DEBT-002 的锚点写法与标题实际 slug 不符（逗号被 GitHub 丢弃）。

---

## 0.3.2 — 开发规范与项目记忆体系

产品运行行为不变。本次补的是「怎么改」与「改了什么」的记录层。

### 新增

| 内容 | 说明 |
|---|---|
| `docs/STANDARDS.md` | 开发规范，12 节，按效力分级（硬规则 / 软规则 / 建议）。含分层依赖矩阵、异常三层契约、兼容承诺、提交格式、自审清单、破例流程 |
| `docs/GLOSSARY.md` | 术语表：状态五态、覆盖度 vs 置信度、两个 `weight` 的区别、版本三兄弟 |
| `docs/memo/` | 项目记忆四本台账：工作日志、技术债（14 条）、踩坑（14 条）、未决问题（10 条） |
| `tools/selfcheck.py` | 规范自检，10 项：分层依赖、裸 print、宽捕获吞异常、版本一致性、文档链接与锚点、文档数字与代码一致、`--flag` 真实性、profile 分类一致性、台账编号与交叉引用 |

### 变更

- `docs/DEVELOPMENT.md` 的 §7（文档同步）与 §9（代码风格）收敛为指向 `STANDARDS.md` 的引用，
  消除同一规则两处维护
- 文档与代码的一致性从「靠纪律」改为「靠脚本」：`selfcheck` 会比对文档里写的检测项数、
  可 FAIL 项数、测试数、版本号、参数名与代码实际值
- 版本号升 0.3.2

### 修复

- `docs/memo/gotchas.md` 两处失效引用（ADR 相对路径少一级、DEBT-013 锚点名写错）
- 自检规则按现实校准：首跑报出 22 处 `except: pass`，核实后确认绝大多数是
  「窄捕获 + 默认值」的正当降级（编码回退链、`/proc` 数字解析）。规则改为
  **禁止宽捕获且无 `# noqa` 与原因注释的静默吞**，允许窄捕获降级

---

## 0.3.1 — 文档体系重建

产品代码行为不变（除一处报告一致性修复与两处注释修正），本次重写的是文档。

0.3.0 之后文档处于「半新半旧」状态：README 讲的是新架构，但细节仍散落在一处，`docs/` 只有两篇规划类文档。这次按手册结构重建。

### 新增文档（10 篇 + 7 条 ADR）

| 文档 | 内容 |
|---|---|
| `docs/README.md` | 导航入口，按「我想做什么」分流 |
| `docs/CHECKS.md` | **55 项检测逐条手册**：判什么、依据什么、每种情况给什么状态 |
| `docs/SCORING.md` | 三层计算、权重矩阵、两条封顶规则、覆盖度、置信度，含可复现的手算示例 |
| `docs/PROFILES.md` | 四个场景的权重/阈值/范围差异，选择指南，`--enable` 与 `--only` 的交互 |
| `docs/OUTPUT.md` | `report_version 3.0` 逐字段说明、`trend` 语义、消费示例、报告完整性校验 |
| `docs/CLI.md` | 全部参数、退出码语义（含「退出码只看 FAIL」的坑）、典型用法、环境依赖 |
| `docs/HISTORY.md` | 库结构、十种变化类型、证据级对比、现状限制 |
| `docs/ARCHITECTURE.md` | 四层结构、数据流、五个关键机制、四个扩展点、与旧架构对比 |
| `docs/DEVELOPMENT.md` | 加检测项（完整示例）、加分类/报告格式/连接器、测试约定、文档同步规则、发布流程 |
| `docs/TROUBLESHOOTING.md` | 15 个典型现象的原因、验证命令、对策 |
| `docs/adr/` | 7 条决策记录：UNKNOWN 一等状态、采集不做判断、注册表、两条封顶、格式 3.0、零依赖、不做修复引擎 |

### README 重写

从「功能罗列」改为「差异化说明 + 快速开始 + 文档导航」。深度内容（权重矩阵、JSON 字段、项目结构、开发约定）全部移入 `docs/`，消除同一事实的多处维护。

### 修复

- **报告一致性**：权重为 0 但确有判定的分类（如 `verify` 场景的 `ai`），JSON 里有、终端与 HTML 却按 `weight > 0` 过滤掉了，导致同一份数据两种说法。现在只要判定了就显示，并标注「仅展示不计分」
- `profiles.py` 文档串称「权重为 0 的分类其检查项直接标 SKIP」，与实际不符——范围由 `active` 决定，权重只影响计分。已改正
- `registry.py` 的 `tags` 字段实际不参与筛选，注释已标明

### 测试

31 项（+1）：新增 `test_zero_weight_category_visible_in_all_reporters`，锁住三个报告器的一致性。

### 文档验证

- 全部内部链接与锚点通过校验（37 个 markdown 文件）
- 文档中出现的 47 个 `--flag` 全部对应真实参数或明确属于其他工具（`smartctl` / `docker` / `pytest`）
- 文档中的 15 条命令实际逐条执行通过
- HTML 报告经无头浏览器渲染确认无破版

---

## 0.3.0 — 架构重建

不是修补，是重写判定内核。0.2.0 的根本问题是**加一项检测要改五个地方**（采集、评分、终端、JSON、HTML），导致每个新检查都得复制一遍逻辑，结论还容易在几处之间对不上。这一版把职责切开，让「加一项检测 = 写一个函数」。

### 四层架构（`collect → checks → 聚合 → 呈现`，依赖单向）

| 层 | 位置 | 职责 |
|---|---|---|
| 契约 | `model.py` | `Status` / `Evidence` / `CheckResult` / `Coverage` / `Score` / `Report` |
| 注册 | `registry.py` | `@check` 装饰器，`resolve(only, skip, categories)` |
| 采集 | `collect/` | 只拿事实，**不做判断**（已移除 `warnings` / `errors` / `ok` 等判断字段） |
| 判定 | `checks/` | 一类一个模块，共 **55 项** |
| 编排 | `engine.py` | 跑检查、超时、异常收敛、设备指纹 |
| 聚合 | `scoring.py` | 分类得分 → 总分 → 封顶规则 + 覆盖度 + 置信度 |
| 呈现 | `reporters/` | terminal / json / html，只依赖 `Report` |

### 新增能力

- **`Status.UNKNOWN` 成为一等状态**：读不到 SMART 既不判「硬盘坏了」也不判「硬盘没事」，不扣分但降低覆盖度。之前这种情况要么被当成 PASS（掩盖问题）要么被当成 FAIL（制造假故障）
- **`Evidence`（source / key / value / num / trend）**：每条结论都能追溯到具体命令输出
- **置信度（0-1）** 按权重加权到整体，随证据质量变化
- **覆盖度**：分母是**适用项**（`总数 − 不适用`），并给出盲区比例。此前 Windows 上 31 项 Linux 专属检测拿不到数据，覆盖率被算成 39%
- **两条封顶规则**：存在严重问题 → 59；盲区 ≥50% → 74、≥30% → 84。触发原因写入 `cap_reason`，不静默降分
- **`--profile` 场景化**（`nas` / `verify` / `dev` / `ai`）：四套权重、阈值与启用分类。`verify` 提高安全权重，`ai` 给算力 26 分
- **按芯片自适应温度阈值**：RK3588 → 70/82，Jetson → 75/88，其余走场景默认
- **`--only` / `--skip` / `--enable` / `--list-checks`**：按模式筛选检查项
- **历史库与逐项对比**：`history.db`（SQLite）存完整报告；`--compare` 输出 `new_failure / still_failing / evidence_worsened / new_improved / fixed / added / removed`。证据带 `trend` 方向语义（`up_bad` / `up_good` / 空），避免把「多跑了 0.1 小时」报成「指标恶化」
- **检查超时**：`signal.SIGALRM`，单条卡死不会拖住整份报告
- **新增安全分类（8 项）**：SSH root 直登、密码登录、防火墙、fail2ban、TLS 证书有效期与自签、SMB 匿名访问、NFS `no_root_squash`。全部只读配置
- **新增外设分类（2 项）**：USB 设备、数据盘连接方式（USB 外接盘降速提示）

### 破坏性变更

- **`report_version` 2.0 → 3.0**：顶层改为 `meta / score / coverage / checks[] / platform / facts`；每条 check 带 `status / confidence / evidence[]`。**消费旧 JSON 的脚本需要改**
- 删除 `nastool/core/`（拆入 `collect/` 与顶层模块）与 `nastool/adapters/`（平台专项检查并入 `checks/`）
- 公开 API 改为 `run / RunOptions / Report / CheckResult / Evidence / Score / Status / REPORT_VERSION`
- 默认权重从固定四维（存储 40 / 网络 25 / 系统 20 / 服务 15）改为按 profile 分配，`nas` 场景为存储 34 / 系统 16 / 网络 18 / 服务 16 / 安全 10 / 外设 6

### 修复

- 覆盖率分母错误（把不适用项算进分母，Windows 上显示 39.2%）
- 历史对比误报「指标恶化」（中性数值被当成越大越差）
- **AINAS 连接器读取已删除的报告字段**（`device` / `storage` / `ai_accelerator`）——格式升级到 3.0 后这些顶层键不存在了，推过去的设备信息会全为空。已改为从 `facts` / `platform` 取，并补契约测试锁住映射关系
- `core/network.py` 在 ≤100 Mbps 链路下访问未定义的 `rep` 引发 `NameError`（潜伏 bug，重写后采集层无判断逻辑，问题消失）
- 终端与 HTML 把「全部不适用」误写成「全部通过」，`--only` 过滤后尤其误导

### 测试

30 项（0.2.0 为 18 项），新增：UNKNOWN 不扣分类分、盲区封顶、FAIL 封顶 59、WARN 不封顶、不适用项不计入评分、注册表完整性、`--only` 过滤、JSON schema、HTML 自包含、历史往返、证据恶化检测、中性证据不误报、新故障检测、AINAS 连接器字段映射、facts 缺失容错。

---

## 未发布 — 前身设计资产提取

从归档中抢救前身项目的设计资料，整理为可执行的路线图。**不改动产品代码**。

### 新增文档
- `docs/CHECKS-ROADMAP.md`：前身 92 个检测器的完整清单，逐项标注当前实现状态（已实现 20 / 部分 8 / 未实现 64，已实现 22%、含部分覆盖约 26%）
- `docs/DESIGN-NOTES.md`：从 14 篇原始文档提炼的设计要点——准确性保障层（数据融合 / 一致性验证 / 置信度）、`--profile` 场景化检测与动态权重、按芯片型号的自适应阈值、带风险等级的行动计划、修复引擎的四级风险模型、12 条真机 BUG 教训
- `reference/README.md`：前身项目全貌（1,086 文件 / 1,817 函数类 / 6 子包 / v7.1.0-beta）、可复用资产、刻意排除项

### 新增参考代码（`reference/legacy/code/`，不参与构建、不参与打包）
- `compare.py`（729 行）：历史库 schema、趋势判定、理想基线——纯标准库，可直接移植
- `scan.py`（627 行）：网段扫描与设备类型识别
- `batch.py`（420 行）：多设备并行诊断调度
- `upnp_discovery.py`（149 行）：SSDP/UPnP 局域网发现
- `scan_ports.py`（46 行）：多线程端口探测

### 说明
- 前身项目的业务内核（`nastool-core` / `-common` / `-fixes`）已随归档丢失，参考代码依赖这些不存在的包，**不可直接运行**
- 下列内容刻意未提取：`main.py`（纯壳）、`nastool_agent.py`（远程执行 shell）、硬编码 SSH 凭据的诊断脚本、带默认管理令牌的 Jetson 安装脚本、依赖 relay 服务端的 WebSocket 客户端

---

## 0.2.0 — 首个独立版本（通用 NAS 化）

从 AINAS 项目的 `tools/nastool` 中独立出来，成为不依赖任何后端的通用 NAS 检测工具。

### 新增
- **NAS 平台识别**（`core/platform_detect.py`）：群晖 DSM、威联通 QTS、TrueNAS、unRAID、铁威马 TOS、绿联 UGOS、OMV、CasaOS、飞牛 fnOS、Proxmox、OpenWrt、通用 Linux / Windows / macOS；并识别 Docker / LXC / K8s / 虚拟机
- **RAID 检测**：`/proc/mdstat`（含降级与重建进度）、ZFS `zpool`、Btrfs 设备错误计数
- **SMART 检测**：健康结论、温度、通电时长、重映射/待定扇区
- **服务与端口探测**（`core/services.py`）：常见 NAS 服务对照、Docker 容器清单、风险端口提示
- **健康评分**（`core/scoring.py`）：存储 40 / 网络 25 / 系统 20 / 服务 15，A-D 等级，问题清单带修复建议
- **连接器层**（`nastool/connectors/`）：`webhook` 通用上报、`ainas` 可选接入；默认完全离线
- **HTML 报告重写**：单文件、零外部依赖、可打印
- **打包**：`pyproject.toml`，`pip install -e .` 后可用 `nastool` 命令；`python -m nastool` 也可直接跑
- **测试**：18 项，覆盖解析器、评分与端到端报告生成

### 通用化改造
- 存储路径默认值不再写死 `/home/nvidia`，改为自动挑选 NAS 数据盘（并验证可写）
- 移除 AI-NAS 专属 config.yaml 探测，改为通用 `--config` / `NASTOOL_CONFIG` 提示
- 网络检测从「NAS 后端连通性」改为通用「对端 host:port 可达性」
- AI 能力改为加分项：不再因为没装 PyTorch 而判整机不健康
- 新增 AMD ROCm、Google Coral Edge TPU 识别
- 设备采集补齐 Windows / macOS 实现（原先在非 Linux 上一片未知）

### 修复
- `core/network.py`：`_cidr_to_netmask` 位移方向错误，`/24` 会算成 `0.255.255.255`
- `core/network.py`：`get_interfaces()` 使用 `os.path.exists` 但顶层缺 `import os`
- `core/storage.py`：字段名 `4k_read_iops` / `4k_write_iops` 是非法 Python 标识符，整个包无法 import
- `reporters/terminal.py`：访问不存在的 `report.device` 属性
- `reporters/html_reporter.py`：模板占位符 `{nas_class}` 与传参 `nas_cls` 键名不一致
- 非 Linux 环境下 `/dev`、`/sys/class/thermal` 的 `listdir` 缺少存在性保护
- Windows 中文输出乱码（`text=True` 固定编码）→ 统一 UTF-8 优先 + locale 回退；PowerShell 调用改为参数列表
- 评分与结论可能矛盾（A 级 + 严重问题）→ 存在严重问题时总分封顶 59

### 移除
- `nastool_agent.py`（可远程执行任意 shell 的 relay 客户端）
- `jetson_install.py` / `jetson_patch.py`（带默认管理令牌的管理端点）
