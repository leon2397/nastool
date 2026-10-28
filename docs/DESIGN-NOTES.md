# 前身设计笔记（从归档文档提炼）

前身项目的代码内核已丢失，但文档把设计记录下来了。这里只留**当前产品能用上**的部分，每条都注明来源与我这边的差距。

---

## 〇、最重要的三条

如果只能带走三条，是这三条：

1. **每条检查结果自带置信度**，而不是只给一个 PASS/FAIL。
2. **检测标准按设备用途分级**（`--profile`），同一项指标在不同用途的设备上严重程度不同。
3. **报告不只列问题，还给带风险等级的行动计划**（`action_plan`）。

当前 nastool 三条都还没有。这三点合起来，正好是"报告可信"的技术实现——比我之前说的"卖点是可信报告"要具体得多。

---

## 一、准确性保障层（来源：`ARCHITECTURE.md` §2.2.2、`BUG_SUMMARY_V4.1.md`）

前身在 `nastool_core` 里做了一层独立于检查逻辑的"准确性保障"，包含四个组件：

| 组件 | 职责 |
|---|---|
| `DataFusionEngine` | 多源数据融合（同一指标从多个来源取，融合成一个值） |
| `ConsistencyValidator` | 一致性验证（时间 / 值 / 趋势 / 来源 四个维度） |
| `AsyncDataCollector` | 异步并发采集 |
| `HealthScorer` | 健康评分 |

**数据融合支持 8 种方法**（实测全部通过）：

`weighted_average` · `median` · `mean` · `mode` · `geometric_mean` · `harmonic_mean` · `min` · `max`

**异常值检测支持 3 种算法**：IQR · Z-score · MAD

**一致性验证四个维度**：时间一致性、值一致性、趋势一致性、源一致性

**`CheckResult` 带 `confidence: float (0.0-1.0)`**，实测高置信场景 0.866、低置信场景 0.722。

### 为什么这值得抄

以"CPU 温度"为例：`/sys/class/thermal`、`sensors`、`tegrastats`、`nvidia-smi` 可能给出不同读数。当前实现是**取第一个读到的**，前身是**融合 + 交叉验证 + 给出置信度**。

对"读不到"这件事，这层直接把结论从"未知"变成"低置信度读数"——这正是我们定的"读不到 ≠ 坏掉"原则的技术落地方式，而不只是一句口号。

### 我这边的差距

当前 `core/*` 每个采集器返回单一值，`scoring.py` 直接按阈值判定，**没有置信度概念**。改造点：给每个采集结果加 `sources: List[str]` 与 `confidence: float`，评分时对低置信项降权而非直接判失败。

---

## 二、按用途分级的标准（来源：`IMPROVEMENT_PLAN.md` §2.1、`TEST_BUGS.md` IMP-001/002）

前身踩过的坑，和我们遇到的是同一个：**Jetson 设备没有外网，结果所有网络检测全 FAIL，整机被判不健康。**

它的解法是 `--profile`：

```
nastool --profile nas      # 完整网络检测
nastool --profile dev      # 跳过外网检测
nastool --profile jetson   # Jetson 专用（含 tegrastats）
```

配套的**动态权重**（按设备用途给不同分类加权）：

```python
WEIGHTS = {
    "default":   {"system": 1.0, "network": 1.0, "storage": 1.0, "ai": 0.5, "security": 1.0},
    "nas":       {"system": 0.8, "network": 1.2, "storage": 1.5, "ai": 0.3, "security": 1.2},
    "ai_server": {"system": 0.8, "network": 0.5, "storage": 1.0, "ai": 2.0, "security": 1.0},
    "jetson":    {"system": 1.0, "network": 0.3, "storage": 1.0, "ai": 1.5, "security": 0.8},
}
```

同一份文档里还写了另一条判定纪律：

- DNS 解析 `baidu.com` 失败 → **Warning**（可能网络隔离）
- DNS 解析 `google.com` 失败 → **Info**（国内正常现象）
- TensorFlow / Keras / OpenVINO 未安装 → 如果设备不是 AI 推理服务器，应该是 **Info** 而不是 Warning

**注意**：这两条和我上一轮独立修的问题（外网不可达不该算错误、AI 算力不参与合格判定）完全一致。两个人在不同时间得出同一结论，说明这是真问题。

### 我这边的差距

现在是**一套固定标准 + 固定权重**（存储 40 / 网络 25 / 系统 20 / 服务 15）。加 `--profile` 是实现成本最低、收益最直接的一项改造。

---

## 三、自适应阈值（来源：`BUG_SUMMARY_V4.1.md`）

前身按芯片型号给不同温度阈值，实测数据：

| 设备类型 | CPU 警告 | CPU 严重 | GPU 警告 | GPU 严重 |
|---|---:|---:|---:|---:|
| `rk3588` | 70°C | 80°C | 75°C | 85°C |
| `rk3568` | 70°C | 80°C | 75°C | 85°C |
| `jetson_xavier` | 75°C | 85°C | 80°C | 90°C |
| `generic` | 75°C | 85°C | 80°C | 90°C |

阈值验证实测：60 / 70°C → PASSED，75 / 80°C → WARNING，85 / 90°C → CRITICAL。

### 我这边的差距

当前 `scoring.py` 对所有设备用同一套温度阈值。而**不同芯片的耐温差异是真实存在的**（RK3588 到 80°C 已经很高，Jetson 到 85°C 才警告）。这是一条"别人不会抄、但用户能感知"的细节。

---

## 四、报告给行动计划（来源：`IMPROVEMENT_PLAN.md` §2.3）

JSON 报告结构：

```json
{
  "device": "jetson-xavier-nx",
  "profile": "jetson",
  "score": 78,
  "grade": "B",
  "timestamp": "2026-04-23T15:36:45+08:00",
  "checks": [],
  "suggestions": [],
  "action_plan": [
    {"priority": 1, "fix": "ssh_hardening", "risk": "medium"},
    {"priority": 2, "fix": "cleanup_temp",  "risk": "low"}
  ]
}
```

关键在 `action_plan` 带 **priority + risk 双维度**。当前 `scoring.py` 只产出 `findings`（问题清单），没有"先做什么、风险多大"。

---

## 五、修复引擎的安全架构（来源：`MEMO.md` §安全架构、`IMPROVEMENT_PLAN.md` §3）

前身有自动修复能力，安全设计相当完整，**即使当前产品不做自动修复，这套风险模型也该抄**：

> 最高准则：零破坏、零篡改、所有操作可撤销

**禁止清单 `FORBIDDEN_FIXES`**（代码级硬编码，不可绕过）：

| 类别 | 代表操作 | 原因 |
|---|---|---|
| 网络配置 | 改 DNS / 网络 / 防火墙 | 可能导致设备断连 |
| 用户管理 | 禁用 root / 增删用户 | 可能锁死管理员 |
| CUDA / 驱动 | 安装 CUDA / 驱动 | 风险极高 |
| 破坏性 | 格式化磁盘 / 清数据 / 恢复出厂 | 数据永久丢失 |

**四级风险**：`low`（可自动执行）· `medium`（需确认）· `high`（确认 + 备份）· `danger`（禁止清单直接屏蔽）

**执行保障**：`risk >= medium` 强制先 dry-run；执行前创建快照；执行后自动跑验证检查，不通过自动回滚。

### 对当前产品的意义

我们**不做**自动修复，但报告里的每条建议都应该标 `risk` 与 `是否可自动处理`——这决定了用户敢不敢照做。这是纯文档层的改动，成本几乎为零。

---

## 六、检查框架结构（来源：`ARCHITECTURE.md` §2.2.1 / §5）

前身的检查是**注册中心 + 插件**模式：

```
checks/
├── base.py          # 抽象基类 Check
├── registry.py      # 检查注册中心
├── decorators.py    # @register_check 装饰器
├── ai/ network/ security/ storage/ system/ nas/ usb/
```

插件写法：

```python
@register_check
class MyCustomCheck(Check):
    check_id = "my_custom_check"
    category = CheckCategory.SYSTEM
    title = "..."
    def run(self) -> CheckResult: ...
```

`CheckResult` 的字段设计值得注意——它有 **`current` 与 `expected` 一对**：

| 字段 | 说明 |
|---|---|
| `check_id` / `category` / `severity` / `passed` | 基本身份 |
| `title` | 显示名 |
| **`current` / `expected`** | **当前值 vs 期望值** |
| `message` | 详细说明 |
| `confidence` / `data_sources` / `consistency_report` | 准确性 |

### 我这边的差距

当前是**七个写死的采集模块**（device / storage / network / services / ai_accel / platform / scoring），加新检测项要改 `runner.py`。

92 项检测要补齐，**必须先有注册中心**，否则每个新项都要动编排层。而且 `current` / `expected` 这个模型比当前的 `findings` 列表信息量大：能直接生成"本应 60°C 以下，实际 78°C"这种报告措辞。

---

## 七、真机 BUG 教训清单（来源：`TEST_BUGS.md`，Jetson Xavier NX 实测 12 条）

这些是**在真机上撞出来的**，值得当检查表用：

| 编号 | 问题 | 根因 | 当前产品是否已规避 |
|---|---|---|---|
| BUG-001 | 评分恒为 0 | `severity` 有时是 str 有时是 enum | ✅ 当前用纯字符串常量 |
| BUG-002 | SSL 证书天数显示 -1148 | 时间戳相减方向/基准错 | — 未实现该检测项 |
| BUG-003 | Jetpack 版本检测失败 | 只认 x86 路径 | ✅ 无此项 |
| BUG-004 | GPU 误报"未检测到加速器" | 假设有 `nvidia-smi` | ✅ 已按 `/dev/nvidia0` 等多路探测 |
| BUG-005 | CUDA 版本检测失败 | 只在 `PATH` 找 `nvcc` | ✅ 已多路径探测 |
| BUG-006/007/008 | 温度 / 运行时长 / 网卡速率**乱码** | subprocess 未指定编码 | ✅ 已统一 UTF-8 + `errors="replace"` |
| BUG-009 | `nvidia-smi` 失败但 GPU 实际存在 | 同上 | ✅ 已规避 |
| BUG-010 | 内存显示 6846 GB | 单位换算错 | ✅ 从 `/proc/meminfo` 的 kB 一次性换算 GB，口径唯一 |
| BUG-011 | 后端检测超时 | 超时设置过短 | ✅ 已设 3-5s 并分级为提示 |
| BUG-012 | 写入速度偏低误报 | 阈值未分设备类型 | ◐ 已默认跳过测速 |

**结论**：12 条里有 8 条当前产品已经规避，而且其中 4 条（编码、GPU 多路探测、CUDA 路径、内存单位）是**独立踩到并修掉的**——说明这些坑是这条路上的必经点，值得保留在测试用例里防止回归。

### 一个额外的坑

`IMPROVEMENT_PLAN.md` 提到：前身的 `--quick` 统计显示有 BUG，`HTML 报告未生成` 也是 P0。**报告生成器在真机上容易静默失败**——这和我昨天在 `html_reporter.py` 里发现的模板占位符不匹配（`{nas_class}` vs `nas_cls`）是同一类问题。建议给报告器加一个"产物存在性 + 内容完整性"断言。

---

## 八、前身没做到的事（来源：`MEMO.md` §已知限制）

| 项目 | 状态 |
|---|---|
| 统一配置中心 | 未完成 |
| RK3588 NPU 检测 | 待完善 |
| USB 即插即用 | 未实现 |
| PyPI 发布 | 未完成 |
| 插件系统 | **未实现**（架构里设计了，但没落地） |

**注意最后一条**：插件系统只在架构图里存在。所以上面的"注册中心"设计是**纸面设计**，不是验证过的实现——抄设计要自己验证，不能假定它跑通过。

---

## 九、历史数据模型（来源：`reference/code/compare.py`）

这是唯一一份**可以直接照搬的可用代码**（纯 `sqlite3`，无第三方依赖）：

```sql
CREATE TABLE IF NOT EXISTS diagnosis_history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id      TEXT NOT NULL,
    timestamp      TEXT NOT NULL,
    score          INTEGER,
    critical_count INTEGER,
    warning_count  INTEGER,
    info_count     INTEGER,
    passed_count   INTEGER,
    total_count    INTEGER,
    report_json    TEXT,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_history_device ON diagnosis_history(device_id);
CREATE INDEX IF NOT EXISTS idx_history_time   ON diagnosis_history(timestamp);
```

趋势判定极简：`score_change = 当前 - 基线`，`> +5` 改善、`< -5` 恶化、其余稳定。

理想基线按设备类型存 `~/.nastool/baselines.json`：

```json
{
  "rk3588":  {"cpu_governor": "performance", "npu_freq": "1000000000", "thermal_zone_0": 45},
  "rk3568":  {"cpu_governor": "performance", "npu_freq": "800000000",  "thermal_zone_0": 45},
  "jetson":  {"cpu_governor": "performance", "gpu_freq": "1300500000", "thermal_zone_0": 50},
  "generic": {"cpu_governor": "performance", "thermal_zone_0": 50}
}
```

### 注意一个设计缺陷

趋势判定只看 `score` 总分。分数可能因为无关项变化掩盖关键项恶化——**"总分稳定但某块盘重映射扇区从 0 涨到 12"这种最要命的情况，它抓不到**。

这正是我上一轮说的"diff 才是复利项"：要做就做**逐项 diff**，不是只看总分趋势。总分趋势是它已经做到但不够的那一层。

---

*所有引用均来自 `reference/legacy/docs/` 下 14 篇原始文档，行号可对照原文核查。*
