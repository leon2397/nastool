# 报告格式规范

> JSON 是这个产品对外最重要的接口：上报、历史库、二次分析、CI 判定都依赖它。
> 本文是 **`report_version: 4.0` 的字段说明书**。
>
> 相关：[CLI.md](CLI.md)（怎么产出）、[HISTORY.md](HISTORY.md)（存下来的报告怎么比对）

---

## 0. 版本契约

```json
"meta": { "report_version": "4.0" }
```

`REPORT_VERSION` 是**向后兼容契约**。规则：

- 加字段（非破坏性）→ 不升版本
- 改字段语义 / 删字段 / 改结构 → **必须升版本**，并在 CHANGELOG 写明迁移方式

消费方应当先校验 `meta.report_version`，不匹配时明确报错而不是猜。

- 3.0 相对 2.0 是破坏性升级，详见 [ADR-0005](adr/0005-report-version-3-breaking.md)。
- **4.0 相对 3.0 是破坏性升级**：`coverage` 新增三个字段、`blind_percent` 口径变了、
  `score` 的计算方式变了（低置信的 PASS 不再计入分母）。
  详见 [ADR-0009](adr/0009-confidence-participates-in-scoring.md)。

**跨版本对比的注意事项**：3.0 的报告与 4.0 的报告**分数不可直接相减**——
差值里一半来自设备变化、一半来自口径变化。`nastool --compare` 会自动识别并提示。

---

## 1. 三种输出，一份数据

三种格式都从同一个 `Report` 对象生成，因此**字段永远一致**：

| 格式 | 入口 | 用途 |
|---|---|---|
| terminal | `TerminalReporter.render(report)` | 人直接看 |
| JSON | `report.to_dict()` | 机器消费、入库、上报 |
| HTML | `HTMLReporter.build(report)` | 发给别人、存档、打印 |

一个容易踩的点：`score.categories[]` 里会出现**权重为 0 的分类**（例如 `verify` 场景下的 `ai`）。它表示「检测了但不计分」，不是错误。三个报告器的处理一致——只要该分类确实判定了项，就会显示并标注「仅展示不计分」；一项都没判定（`score: null`）时，终端与 HTML 会省略它以省版面。

---

## 2. 顶层结构

```json
{
  "meta":            { ... },   // 工具版本、场景、时间、指纹
  "score":           { ... },   // 总分 / 等级 / 分类得分 / 置信度
  "coverage":        { ... },   // 覆盖了多少项
  "checks":          [ ... ],   // 逐项结论（真正的价值在这里）
  "platform":        { ... },   // 平台识别原始结果
  "facts":           { ... },   // 设备清单（展示用，非判定依据）
  "collect_errors":  [ ... ]    // 仅在采集器失败时出现
}
```

前四个是**必有的**；`platform` / `facts` 在正常路径下必有；`collect_errors` 只在采集器自身异常时出现（这是诊断信息，不影响判定）。

---

## 3. `meta`

| 字段 | 类型 | 说明 |
|---|---|---|
| `tool` | string | 固定 `"nastool"` |
| `version` | string | 工具版本，如 `"0.3.4"` |
| `report_version` | string | **格式版本，当前 `"4.0"`** |
| `generated_at` | string | `YYYY-MM-DD HH:MM:SS`（本地时间，无时区） |
| `duration_s` | float | 本次检测耗时（秒） |
| `hostname` | string | 主机名 |
| `profile` | string | 场景：`nas` / `verify` / `dev` / `ai` |
| `python` | string | Python 版本 |
| `platform_summary` | string | `platform.platform(terse=True)` |
| `fingerprint` | string | **设备指纹**，16 位 hex（首次 16 字符 SHA-256） |
| `options` | object | 本次实际生效的参数 |

### `meta.options`

用于回答「这份报告是在什么条件下产生的」——排查问题时第一步就该看它。

| 字段 | 类型 | 说明 |
|---|---|---|
| `storage_path` | string | 实际检测的路径（可能是自动挑选的结果） |
| `peers` | string[] | 对端目标 |
| `speed_test` | bool | 是否做了读写测速 |
| `smart` | bool | 是否读了 SMART |
| `ai` | bool | 是否做了 AI 推理测试 |
| `internet` | bool | 是否检查外网 |
| `only` | string[] | `--only` 模式 |
| `skip` | string[] | `--skip` 模式 |

`options` **不包含** `--enable`，追加的分类反映在 `score.categories[]` 里（会出现权重 8 的分类）。

### `fingerprint` 的用途

同一台机器多次检测应得到相同指纹。历史对比时若指纹不同，说明报告来自不同设备，对比无意义——CLI 会打印警告：

```
⚠ 历史记录的设备指纹与本次不同，对比结果可能无意义
```

计算方式：`sha256(hostname | arch | platform_model | vendor)[:16]`。

**它不是安全标识**，只用于防止误比对。改主机名或换主板都会让指纹变化。

---

## 4. `score`

| 字段 | 类型 | 说明 |
|---|---|---|
| `total` | int \| null | 总分 0–100；`null` = 无法计算 |
| `grade` | string | `A` / `B` / `C` / `D` / `N/A` |
| `verdict` | string | 等级对应的一句话结论 |
| `confidence` | float | 整体置信度 0–1 |
| `capped` | bool | 是否触发了封顶 |
| `cap_reason` | string | 封顶原因（多条用 `；` 连接）；未封顶为空串 |
| `ai_score` | int | AI 能力分，**独立展示，与 `total` 无关** |
| `ai_note` | string | AI 能力的文字说明 |
| `categories` | array | 分类得分，见下 |

计算规则详见 [SCORING.md](SCORING.md)。

### `score.categories[]`

```json
{ "category": "storage", "name": "存储",
  "weight": 34, "score": 100, "judged": 3, "total": 13,
  "low_confidence": 0, "usable": 3 }
```

| 字段 | 说明 |
|---|---|
| `category` | 稳定机器标识（`storage` / `security` / `system` / `network` / `services` / `ai` / `usb`） |
| `name` | 中文显示名 |
| `weight` | 该项在本次场景下的权重；**0 表示不计入总分** |
| `score` | 该类得分 0–100；**`null` = 该类没有任何已判定项** |
| `judged` | 已判定项数，**含低置信项** |
| `total` | 该类总项数（含 SKIP / UNKNOWN） |
| `low_confidence` | 判定了但未计入分数的项数，**v4.0 新增** |
| `usable` | 真正计入分数的项数 = `judged − low_confidence`，**v4.0 新增** |

`usable / total < 0.5` 时报告会标「低覆盖」，提示该得分只基于少数几项。

**注意 `judged` 与 `usable` 的区别**：`judged` 是「判定了几项」，`usable` 是
「其中几项真的参与了计算」。低置信的 PASS 会让 `judged` 大于 `usable`——
终端会显示成 `0/1（1 项存疑未计分）`，让用户看到它被剔除了，而不是以为整类都查过了。

---

## 5. `coverage`

```json
{ "total": 51, "applicable": 19, "judged": 19,
  "unknown": 0, "skipped": 32, "low_confidence": 0,
  "trustworthy": 19,
  "percent": 100.0, "trustworthy_percent": 100.0, "blind_percent": 0.0 }
```

| 字段 | 说明 |
|---|---|
| `total` | 本次执行的检查项总数 |
| `applicable` | 适用项 = `total − skipped` |
| `judged` | 已判定（PASS + WARN + FAIL），**含低置信项** |
| `unknown` | 不可判定（读不到、权限不足、工具缺失） |
| `skipped` | 不适用（平台不支持） |
| `low_confidence` | 判定了但置信度不足（≤ 0.5）的项数（**含低置信的 FAIL**），**v4.0 新增** |
| `trustworthy` | 有可信结论的项数 = `judged − low_confidence`，**v4.0 新增** |
| `percent` | `judged / applicable × 100` |
| `trustworthy_percent` | `trustworthy / applicable × 100`，**v4.0 新增**——可信结论的占比 |
| `blind_percent` | `(unknown + low_confidence) / applicable × 100`，用于封顶判断 |

**`coverage.trustworthy` 与 `categories[].usable` 不是一回事**（[ADR-0011](adr/0011-coverage-field-naming.md)）：

| | `coverage.trustworthy` | `categories[].usable` |
|---|---|---|
| 衡量什么 | 有多少项的**结论可信** | 有多少项**参与了打分** |
| 低置信 PASS | 剔除 | 剔除 |
| 低置信 FAIL | **剔除**（结论不可信） | **保留**（照样扣分并封顶） |
| 用途 | 衡量报告可信度 | 报告里显示的打分分母 |

两者同名会让人误以为 `coverage` 里的数就是「参与打分的项数」——那是错的，
所以覆盖度侧改用 `trustworthy`。

**注意 `percent` 的分母是 `applicable` 而不是 `total`。** 在 Windows 上 `skipped` 会很大（Linux 专属项），若用 `total` 作分母会制造「覆盖率只有 39%」的假象。详见 [SCORING.md](SCORING.md#5-覆盖度)。

**`unknown` 与 `low_confidence` 是两回事，不要合并**：

| | 含义 | 典型成因 |
|---|---|---|
| `unknown` | **没测到** | 权限不足、工具缺失、读不到接口 |
| `low_confidence` | **测到了但不可信** | 多个来源读数互相矛盾（见 [ADR-0008](adr/0008-multi-source-fusion.md)） |

两者都会让「结论有限」，所以都计入 `blind_percent`；但成因不同，报告要分开显示，
否则用户会以为所有不确定都是「工具没装好」。

恒等式（可用于校验数据完整性）：

```
total == judged + unknown + skipped
applicable == total - skipped
usable == judged - low_confidence
```

---

## 6. `checks[]` — 核心

每一项都是一条可复核的结论。

```json
{
  "id": "storage.smart_bad_sectors",
  "title": "坏道计数",
  "category": "storage",
  "status": "warn",
  "confidence": 0.95,
  "summary": "1 块硬盘存在重映射扇区（/dev/sda:8）",
  "detail": "已有坏道被备用扇区替换，短期内可用，但数量持续增长说明盘在老化",
  "suggestion": "加强备份频率，记录数值以便下次对比是否增长",
  "weight": 5,
  "duration_ms": 87,
  "error": "",
  "evidence": [ ... ]
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 稳定标识，`分类.名称`。**历史对比、外部引用都靠它，不可随意改** |
| `title` | string | 显示名 |
| `category` | string | 所属分类 |
| `status` | string | `pass` / `warn` / `fail` / `unknown` / `skip` |
| `confidence` | float | 该项置信度 0–1。**≤ 0.5 时不再计入分数分母**（仅对 PASS 生效，详见下） |
| `summary` | string | 一句话结论（报告主行显示这个） |
| `detail` | string | 补充解释，为什么这是个问题 |
| `suggestion` | string | 修复建议（仅 WARN / FAIL 有） |
| `weight` | int | 该项在分类内的权重 1–6 |
| `duration_ms` | int | 该项耗时 |
| `error` | string | **检查器自身异常**，不是「被检测对象有问题」 |
| `evidence` | array | 支撑证据，见下 |

### `checks[].error` 的语义

这个字段区分两种完全不同的失败：

| 情况 | `status` | `error` |
|---|---|---|
| 硬盘真的有坏道 | `fail` | `""` |
| 检查代码自己崩了 | `unknown` | `"KeyError: 'model'"` |

消费者不要把 `error` 非空当成「设备有问题」——它意味着「这次没测成」，应联系工具维护者。

### `checks[].confidence` 如何参与判定（v4.0 起）

置信度低**不等于判定错**，而是「数据不足以支撑这个结论」。它如何影响分数：

| `status` | `confidence` | 计入分数分母 | 计入盲区 |
|---|---|---|---|
| `pass` | > 0.5 | 是 | 否 |
| `pass` | ≤ 0.5 | **否** | **是** |
| `warn` / `fail` | 任意 | **是** | 否 |
| `unknown` / `skip` | — | 否 | `unknown` 计入 |

**为什么 PASS 与 WARN/FAIL 的处理不同**：低置信的 PASS 不可信——不能因为读不准
就断言「没问题」，所以从分母剔除；但低置信的 WARN/FAIL 仍然要计入并扣分——
宁可误报不可漏报，把可疑的严重问题从分数里抹掉等于让设备看起来比实际更健康。

这条与「温度取 MAX 而非平均」是同一条安全保守逻辑，详见
[ADR-0009](adr/0009-confidence-participates-in-scoring.md)。

消费方若要自己重算分数，必须用同一套规则，否则算出来的数与工具对不上。

### `checks[].evidence[]`

```json
{ "source": "smartctl /dev/sda", "key": "reallocated_sector_ct",
  "value": "8", "num": 8, "trend": "up_bad",
  "note": "非零即为隐患" }
```

| 字段 | 必有 | 说明 |
|---|:--:|---|
| `source` | ✓ | 数据从哪来（命令 / 文件 / 接口） |
| `key` | ✓ | 读的是哪个指标 |
| `value` | ✓ | **字符串**形式的读数（永远可读） |
| `note` | | 补充说明 |
| `num` | | **数值**形式，历史对比用；缺省的证据不参与数值比较 |
| `trend` | | 方向语义，见下 |

`value` 与 `num` 同时存在是刻意的：`value` 保证人能读懂（`"8"`, `"PASSED"`, `"3.1 TB"`），`num` 保证机器能比较。

### `trend` 三种取值

| 值 | 含义 | 例子 |
|---|---|---|
| `"up_bad"` | 涨了是坏事 | 坏道数、重映射扇区、使用率、网卡错误计数 |
| `"up_good"` | 涨了是好事 | 可用空间 |
| 缺失 / `""` | 中性，波动不代表好坏 | 温度、负载、通电时长、进程数 |

**这是历史对比不产生噪音的关键。** 没有这个标注，diff 会把「运行时长 +0.1 小时」报成「指标恶化」。详见 [HISTORY.md](HISTORY.md#4-证据级对比)。

---

## 7. `platform` 与 `facts`

### `platform` — 平台识别原始结果

```json
{ "kind": "nas_appliance", "vendor": "Synology", "product": "DS920+",
  "version": "7.2", "pretty_name": "Synology DSM 7.2",
  "distro_id": "dsm", "kernel": "4.4.180", "arch": "aarch64",
  "hostname": "mynas", "model": "", "in_container": false,
  "container_type": "", "is_root": true, "data_roots": ["/volume1"],
  "facts": { "model": "DS920+" } }
```

| 字段 | 说明 |
|---|---|
| `kind` | `nas_appliance` / `nas_software` / `linux` / `windows` / `macos` |
| `vendor` / `product` / `version` | 厂商、产品、版本 |
| `distro_id` | 发行版标识（`dsm` / `qts` / `truenas` / `unraid` …） |
| `arch` / `kernel` | 架构、内核 |
| `in_container` / `container_type` | 是否在容器内（`docker` / `lxc` / `k8s`） |
| `is_root` | 是否 root / 管理员 |
| `data_roots` | 识别到的 NAS 数据根目录候选 |

### ⚠ 取型号要小心

型号有两个来源，**不是一个**：

| 位置 | 内容 | 何时有值 |
|---|---|---|
| `platform.model` | 平台层识别出的型号（如 DSM 的 `syno_hw_version`） | 仅成品 NAS |
| `facts.platform.model` | 上者，**或**回退到 DMI / 设备树的主板型号 | 几乎所有平台 |

做展示请用 `facts.platform.model`；只用 `platform.model` 会在普通 x86 机器上拿到空串。

### `facts` — 设备清单

`facts` 是**展示用**数据，不是判定依据。判定依据在 `checks[].evidence`。

| 子对象 | 内容 |
|---|---|
| `platform` | 同上的展示版（含回退后的 `model`） |
| `system` | `cpu`（model/cores/freq/arch）、`memory`（total/available/used_percent/swap）、`board`（manufacturer/model/serial/os/uptime_hours）、`virtualization`、`thermals[]` |
| `storage` | `target_*`、`speed`、`disks[]`、`physical_disks[]`、`raids[]`、`smart[]` |
| `network` | `interfaces[]`、`gateway`、`gateway_reachable`、`dns_server`、`dns_ok`、`internet_reachable`、`peers[]` |
| `services` | `total_listening`、`ephemeral_ports`、`docker_available`、`items[]`、`containers[]`、`processes[]` |
| `security` | `ssh`、`firewall`、`certs[]`、`smb_guest`、`smb_signing`、`nfs_no_root_squash`、`ftp_anonymous`、`fail2ban`、`ip_forward` |
| `ai` | `best_chip_type`、`hardware_accelerated`、`inference_*`、`devices[]`、`notes[]` |

**空数组不等于「没有」，只等于「没读到」。** 例如 `facts.storage.smart` 为空，可能是根本没有盘，也可能只是没装 `smartctl`。要区分必须看对应 `checks[]` 项的 `status`（`skip` vs `unknown`）。

---

## 8. 消费示例

### 提取所有需要处理的问题

```python
import json
from nastool.reporters.json_reporter import JSONReporter

report = JSONReporter.load("nastool_report.json")
for c in report["checks"]:
    if c["status"] in ("fail", "warn"):
        print(f"[{c['status'].upper()}] {c['title']}: {c['summary']}")
        if c["suggestion"]:
            print(f"        建议：{c['suggestion']}")
```

### CI 判定（不依赖退出码）

```python
def gate(report: dict, max_grade: str = "B") -> bool:
    """等级不低于 max_grade 且未触发严重封顶才放行。"""
    order = {"A": 0, "B": 1, "C": 2, "D": 3, "N/A": 4}
    return order[report["score"]["grade"]] <= order[max_grade]
```

### 只看某个阈值指标的真实数值

```python
for c in report["checks"]:
    if c["id"] == "storage.capacity":
        for e in c["evidence"]:
            if e["key"] == "use_percent":
                print("磁盘使用率", e["num"])
```

### 校验报告完整性

```python
cov = report["coverage"]
assert cov["total"] == cov["judged"] + cov["unknown"] + cov["skipped"]
assert cov["applicable"] == cov["total"] - cov["skipped"]
assert cov["trustworthy"] == cov["judged"] - cov["low_confidence"]
assert report["meta"]["report_version"].startswith("4.")
```

---

## 9. 终端与 HTML

### 终端报告的层次

```
nastool 0.3.1  ·  场景 nas  ·  时间      ← 我是谁、什么时候
主机 / 平台 / 数据盘                     ← 这是哪台机器
结论 / 覆盖 / 置信                        ← 先给答案
[! 封顶原因]                             ← 答案被削弱时立刻说明
⚠ 检测限制                               ← 什么没测到、为什么
分项（条形图 + 权重 + 判定比 + 低覆盖标记）  ← 结构
明细（按分类，只列非 PASS/SKIP 项）        ← 问题
[-v 时追加：设备清单]                     ← 原始数据
共 N 项 · 耗时 · 报告格式 · 指纹           ← 元信息
```

设计原则：**结论在最上面，证据在最下面**。默认不刷屏（几十项 PASS 不逐条列），`-v` 才展开。

### HTML 报告

单文件、零外部资源（不引用 CDN、不引用字体），可直接邮件发送、离线打开、打印。

包含：分数环、覆盖条、分项条形图、检测限制、按分类的明细（证据可展开）、设备清单（物理盘 / 阵列 / SMART / 网卡 / 端口 / 容器 / 安全配置）。

---

## 10. 相关代码

| 文件 | 职责 |
|---|---|
| `nastool/model.py` | 数据契约与全部 `to_dict()` |
| `nastool/reporters/json_reporter.py` | `build` / `dumps` / `dump` / `load` |
| `nastool/reporters/terminal.py` | 终端渲染、`render_diff` |
| `nastool/reporters/html_reporter.py` | HTML 渲染 |
| `nastool/collect/__init__.py` | `Facts.summary()`——三个报告器共用的展示结构 |
