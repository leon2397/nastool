# reference/ — 前身 nastool 设计资产（仅供追溯，不参与构建）

本目录是从归档中抢救出的 **nastool 前身项目**的设计资料与少量可复用代码。

> **不参与构建**：`pyproject.toml` 只打包 `nastool*`，本目录不进 wheel、不被 import。
> **不可直接运行**：`code/` 下的文件依赖已丢失的 `nastool_core` 等子包，仅作算法与结构参考。

---

## 一、前身项目的真实规模

归档里留下的只是残片。据原始文档记载：

| 指标 | 数值 | 来源 |
|---|---|---|
| 文件总数 | 1,086 个 | `docs/DEEP_CODE_AUDIT.md` |
| 代码体积 | 6.19 MB（迁移包 ~105 MB） | `docs/DEEP_CODE_AUDIT.md` / `docs/迁移说明.md` |
| 函数/类定义 | 1,817 个 | 同上 |
| 子包 | 6 个（cli / core / common / reporters / fixes / adapters） | `docs/NASTool部署备忘录.md` |
| 检测项 | **92 个**（分 7 类） | `docs/CODE_AUDIT_REPORT.md` |
| 版本 | 演进到 **v7.1.0-beta** | `docs/MEMO.md` |
| 交付形态 | 还出过 GUI 包 + Windows exe（41MB / 51MB） | `docs/迁移说明.md` |

**归档中实际保留下来的代码只有约 9,400 行**（`devices/cli` 6,517 + `desktop/arm/nastool` 2,888）。
缺失的是 `nastool-core`（检查框架、数据融合、设备管理、调优建议）、`nastool-common`、`nastool-fixes`（6 个修复域）、`nastool-reporters` 的完整版——即**整个业务内核**。

因此：**文档比代码值钱**。代码是壳，文档记的是设计。

---

## 二、本目录内容

### `docs/` — 原始设计文档（14 篇，3,720 行）

| 文档 | 行数 | 价值 |
|---|---:|---|
| `ARCHITECTURE.md` | 331 | **检查注册中心 + 准确性保障层 + 插件系统**，最核心的设计参考 |
| `IMPROVEMENT_PLAN.md` | 325 | **profile 场景化检测、动态权重、action_plan、fix 安全架构** |
| `MEMO.md` | 372 | 项目定位、版本演进、**修复引擎风险分级与禁止清单**、已知限制 |
| `BUG_SUMMARY_V4.1.md` | 319 | **93 检测项分类、8 种数据融合算法、按设备类型的自适应阈值数值** |
| `CODE_AUDIT_REPORT.md` | 550 | **92 个检测器的文件名清单**（本目录最有行动价值的部分） |
| `TEST_BUGS.md` | 129 | Jetson 真机 12 个真实 BUG 及根因分析 |
| `TEST_PLAN.md` | 317 | 测试用例规格 |
| `TEST_REPORT.md` | 195 | 测试执行记录 |
| `API.md` | 467 | 模块接口契约 |
| `DEVELOPER_GUIDE.md` | 474 | 开发规范 |
| `NASTool部署备忘录.md` | 87 | 6 子包目录结构（权威） |
| `迁移说明.md` | 113 | 历史迁移与部署信息 |
| `DEEP_CODE_AUDIT.md` | 34 | 规模统计与死代码比例 |
| `VALIDATION_REPORT.md` | 7 | 156 项验证：通过 91 / 失败 21 / 跳过 44 |

### `code/` — 可复用的纯标准库代码（5 个文件，1,971 行）

这几个文件**只 import 标准库**（`sqlite3` / `socket` / `asyncio` / `dataclasses` 等），逻辑可整段移植：

| 文件 | 行数 | 可复用点 |
|---|---:|---|
| `compare.py` | 729 | **历史库 schema + 趋势判定 + 理想基线**。`diagnosis_history` 表设计可直接照搬 |
| `scan.py` | 627 | 网段扫描、设备类型自动识别、并发探测 |
| `batch.py` | 420 | 多设备并行诊断调度 |
| `upnp_discovery.py` | 149 | SSDP/UPnP 发现局域网 NAS |
| `scan_ports.py` | 46 | 多线程端口探测 |

---

## 三、刻意未提取的部分

| 内容 | 原因 |
|---|---|
| `devices/cli/main.py`（1,953 行） | 纯壳，依赖 5 个已丢失的子包；其命令结构在 `MEMO.md` 里描述得更清楚 |
| `devices/cli/commands/*` | 同上 |
| `devices/agent/nastool_agent.py` | 连接中继后**可远程执行任意 shell**，属后门性质 |
| `devices/discovery/deep_network_diagnosis.py` | **硬编码 SSH 凭据**（root / linaro123） |
| `jetson_install.py` / `jetson_patch.py` | FastAPI 管理端点，**默认管理令牌** `nastool-update-secret` |
| `ws_client.py` | 依赖 relay 服务端，且与"零联网"定位冲突 |
| `nastool_gui/`、`deploy/*.exe` | 归档中已不存在 |

> 前身项目还存在大量硬编码：中继服务器 `120.77.249.3:18888`、测试机 `192.168.1.123`、SSH 密码 `nvidia`。这些一律不继承。

---

## 四、可以直接拿走的三样东西

按投入产出排序，最值得移植的是：

1. **`diagnosis_history` 表 + 趋势判定**（`code/compare.py`）
   单次报告是快照，历史才是体检。这是产品从"工具"变"标准"的关键一步，schema 已经现成。

2. **92 项检测清单**（`docs/CODE_AUDIT_REPORT.md` → 已整理为 `docs/CHECKS-ROADMAP.md`）
   当前实现约 23 项，剩下 69 项是一份现成的路线图，不用再凭空想"还能测什么"。

3. **准确性保障层的设计**（`docs/ARCHITECTURE.md`）
   多源数据融合 + 一致性验证 + 每条检查带 `confidence`。这是"报告可信"的技术实现路径，比任何单项检测都更重要。

---

## 五、注意事项

- 本目录的代码**没有经过运行验证**，不能当作可用实现。引用的子包（`nastool_core`）已不存在。
- 文档描述的是 **v7.1/v7.2**，而保留的代码是 **v4.1**，两者存在代差。以文档为准看设计，以代码为准看实现细节。
- 前身项目的定位是"**诊断 + 一键部署 ARM NAS 系统**"双重属性（见 `MEMO.md`）。当前的 nastool 只保留**纯检测**这一半，不继承部署能力。
