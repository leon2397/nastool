# 历史记录与趋势对比

> 单次报告只是快照，两次报告才有趋势。
>
> 这是这个产品最容易被低估的部分：**总分稳定在 88，但那块盘的重映射扇区从 0 涨到了 12**——只有逐项对比能发现，看总分永远看不出来。
>
> 相关：[SCORING.md](SCORING.md)（封顶规则）、[OUTPUT.md](OUTPUT.md#6-checks--核心)（evidence 与 trend）

---

## 1. 为什么不只看总分变化

前身项目的历史对比只看 `score` 变化（±5 内视为无变化），结果抓不到最要命的情况：

| | 上次 | 本次 | 总分变化 | 真实情况 |
|---|---|---:|---|
| 场景 A | 88 分，重映射扇区 0 | 88 分，重映射扇区 12 | 0 | **盘在退化** |
| 场景 B | 60 分，阵列降级 | 60 分，阵列仍降级 | 0 | 没人处理 |
| 场景 C | 88 分，可用空间 40% | 88 分，可用空间 12% | 0 | **快写满了** |

总分不变，问题都在恶化。所以这里的核心是**逐项 diff + 证据级 diff**。

---

## 2. 历史库

### 位置与格式

默认 `~/.nastool/history.db`，SQLite 单文件。用 `--history-db` 可改。

```sql
CREATE TABLE runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT,      -- "YYYY-MM-DD HH:MM:SS"
    hostname     TEXT,
    fingerprint  TEXT,      -- 设备指纹，判断是否同一台机器
    profile      TEXT,      -- 检测场景
    score        INTEGER,   -- 总分（可为 NULL）
    grade        TEXT,      -- A/B/C/D/N/A
    confidence   REAL,
    judged       INTEGER,   -- 已判定项数
    total        INTEGER,   -- 总项数
    version      TEXT,      -- 工具版本
    report_json  TEXT       -- 完整报告（v3.0 结构）
);
CREATE INDEX idx_runs_host_ts ON runs(hostname, ts DESC);
```

### 为什么存完整 JSON 而不是拆开的指标

| 理由 | 说明 |
|---|---|
| 新增检查项时老记录仍可读 | 不需要迁移历史数据 |
| diff 可在任意两个版本间做 | 不依赖当前代码 |
| `report_version` 保证格式演进可控 | 老记录能识别出自己是什么格式 |
| 证据完整保留 | 能算出「从多少变成多少」，不只是「变了没」 |

代价是库会变大：一份完整报告约 20–35 KB。一天一次存一年约 10 MB，可忽略。

---

## 3. 命令行用法

```bash
# 存一次
nastool --save-history

# 存并和上次比
nastool --save-history --compare latest

# 看历史列表
nastool --history 10
```

`--history` 的输出：

```
  最近 2 次检测记录

    ID  时间                主机              场景     分数  等级  判定
     2  2026-10-28 15:29:19 tensor            nas        98  A      20/51
     1  2026-10-28 15:29:11 tensor            nas        98  A      20/51
```

最后一列 `判定` 是 `已判定/总项数`——同一个分数在不同覆盖度下的意义完全不同，所以并排显示。

### 对比任意两次

```bash
nastool --compare 12          # 与 ID 12 比
nastool --compare latest      # 与该主机上次比（默认）
nastool --compare             # 同上，省略参数
```

`--compare` 会**先取旧记录做对比，再把本次存进去**，所以不需要额外写 `--save-history`。

### 清理

```bash
nastool --prune-history 90     # 删除 90 天前的记录
nastool --prune-history 365
```

按 `ts` 字段的 `julianday` 差计算，删除后不可恢复。

---

## 4. 证据级对比

### 十种变化类型

按严重度排序（越小越该先看）：

| `kind` | 含义 | 触发条件 |
|---|---|---|
| `new_failure` | 新增严重问题 | 上次不是 FAIL，本次 FAIL |
| `still_failing` | 仍然严重 | 上次 FAIL，本次还是 FAIL |
| `evidence_worsened` | 指标恶化 | 状态没变，但标记 `up_bad` 的数值上升，或 `up_good` 的下降 |
| `new_warning` | 新增告警 | 上次 PASS，本次 WARN |
| `improved` | 有所好转 | 从 FAIL/WARN 变好 |
| `evidence_improved` | 指标好转 | 方向标记的数值朝好的方向变 |
| `evidence_changed` | 指标变化 | 中性指标变了（仅记录，不算问题） |
| `fixed` | 已修复 | 上次 FAIL，本次 PASS |
| `added` | 本次新增检测项 | 上次报告里没有这个 ID |
| `removed` | 本次未检测 | 本次报告里没有这个 ID（`--skip` 或依赖缺失） |

### `trend` 决定「恶化」的判断

只有带方向标注的证据才参与恶化/好转判断：

| 证据 | trend | 0 → 12 | 判定 |
|---|---|---|---|
| 重映射扇区 | `up_bad` | 增加 | **指标恶化** |
| 可用空间 GB | `up_good` | 减少 | **指标恶化** |
| 通电时长 | 无 | 增加 | `evidence_changed`（中性，不算问题） |
| 温度 | 无 | 升高 3°C | `evidence_changed` |

没有 `trend` 标注时，`uptime` 每跑一次都会让它「+0.1 小时」，如果按数值变化判恶化，每次对比都会刷出一堆假警报。这个设计是踩过坑之后加的。

### 一个真实的对比输出

```
  对比  2026-10-20 03:00:11  →  2026-10-27 03:00:09
  分数  88 → 85（-3）   B → B

  指标恶化
    · 坏道计数  无变化 → 重映射扇区增长
        reallocated_sector_ct: 0 → 12（+12）
```

注意分数只掉了 3 分——如果只看分数，很容易认为「还好」；但那一行 `0 → 12` 才是真正要处理的。

### 设备指纹校验

若旧记录的 `fingerprint` 与本次不同，会先警告：

```
  ⚠ 历史记录的设备指纹与本次不同，对比结果可能无意义
```

这防止「拿 A 机器的历史对比 B 机器」得出的荒谬结论。指纹由 `hostname + arch + 平台型号 + vendor` 计算，改主机名或换主板都会变。

---

## 5. 编程使用

```python
from nastool.history import HistoryStore
from nastool.diff import diff_reports

with HistoryStore() as store:            # 默认 ~/.nastool/history.db
    rows = store.list(hostname="mynas", limit=5)
    old = store.load(run_id=rows[1].id)
    new = store.load(run_id=rows[0].id)

result = diff_reports(old, new)
print(result.score_delta())          # 总分变化
print(result.has_regression())       # 是否有回归

for ch in result.of_kind("new_failure", "evidence_worsened"):
    print(ch.title, ch.note)
    for e in ch.evidence:
        print("  ", e.text())         # "reallocated_sector_ct: 0 → 12（+12）"
```

`diff_reports(old, new)` 接受任意两份 `Report.to_dict()` 结构的 dict——不要求来自历史库，也可以是两个 JSON 文件：

```python
from nastool.reporters.json_reporter import JSONReporter
from nastool.diff import diff_reports

a = JSONReporter.load("2026-10-01.json")
b = JSONReporter.load("2026-10-28.json")
print(diff_reports(a, b).to_dict())
```

`DiffResult.to_dict()` 可直接序列化，适合接入告警系统。

---

## 6. 现状与限制

| 限制 | 说明 |
|---|---|
| **没有趋势图** | 当前只能两两对比，不画曲线。想看长期趋势请自己查库 |
| **不做自动基线** | 前身有「理想基线」概念（按机型设定应有值），本项目未实现 |
| **对比不含采集事实** | `diff` 只比 `checks[]`，不比 `facts`（物理盘清单、端口清单等） |
| **`removed` 语义混合** | 「被 `--skip` 跳过」和「依赖缺失」都会记为 `removed`，需看 `note` 区分 |
| **时间戳无时区** | `ts` 是本地时间，跨时区机器混用一个库会乱序 |

### 自己查趋势

```sql
-- 最近 30 次的总分与覆盖度
SELECT id, ts, score, grade, judged || '/' || total AS coverage
FROM runs WHERE hostname='mynas' ORDER BY id DESC LIMIT 30;

-- 提取某次报告里的坏道数
SELECT json_extract(report_json,
         '$.checks[?(@.id=="storage.smart_bad_sectors")].evidence[0].num')
FROM runs WHERE id=12;
```

SQLite 的 JSON 函数（3.38+）可直接在库里查证据。

---

## 7. 相关代码

| 文件 | 职责 |
|---|---|
| `nastool/history.py` | `HistoryStore`：schema、save / list / load / latest_id / prune |
| `nastool/diff.py` | `diff_reports()`、`DiffResult`、`Change`、`EvidenceDelta` |
| `nastool/reporters/terminal.py` | `render_diff()` 终端渲染 |
| `nastool/cli.py` | `--save-history` / `--history` / `--compare` / `--prune-history` 流程 |
