# 0005. 报告格式升到 3.0（破坏性）

- 状态：生效
- 日期：2026-10-28（0.3.0）
- 影响：所有消费 JSON 的外部脚本、AINAS 连接器、历史库既有记录

## 背景

2.0 的报告是「采集结果直接序列化」：

```json
{
  "device":  { "cpu": {...}, "board": {...} },
  "storage": { "target_path": "...", "target_use_percent": 62.5 },
  "network": {...},
  "services": {...},
  "ai_accelerator": { "best_chip_type": "cpu" },
  "score": { "total": 92, "grade": "A" },
  "findings": [ { "level": "warn", "message": "..." } ]
}
```

三个结构性问题：

**1. 没有「每一条结论」的粒度**

`findings` 是一个扁平的字符串列表。没法回答「这一条的依据是什么」「这一项上次是多少」，也没法做逐项对比。历史趋势只能看总分。

**2. 事实与判断混在一起**

`target_use_percent: 62.5` 是事实，`"磁盘快满了"` 是判断，两者在同一个层级。消费方无法区分「这个数字」和「这个结论」。

**3. 没有覆盖度概念**

读不到的东西直接不出现。消费方看到 `"ai_accelerator": {"best_chip_type": "cpu"}` 无法判断这是「探测过、确实只有 CPU」还是「探测失败了」。

这三个问题在内部是 [ADR-0001](0001-unknown-is-first-class.md) 与 [ADR-0002](0002-collect-does-not-judge.md) 要解决的同一件事——外部格式必须跟着变，否则内部分层毫无意义。

## 决策

**升到 `report_version: 3.0`，不与 2.0 兼容。**

新结构：

```json
{
  "meta":     { "report_version": "3.0", "fingerprint": "...", "options": {...} },
  "score":    { "total": 88, "grade": "B", "capped": false, "categories": [...] },
  "coverage": { "total": 51, "applicable": 19, "judged": 19, "unknown": 0 },
  "checks":   [ { "id": "...", "status": "warn", "confidence": 0.95,
                  "evidence": [ {"source": "...", "key": "...", "num": 8,
                                 "trend": "up_bad"} ] } ],
  "platform": { ... },
  "facts":    { ... }
}
```

四件事对应四个问题：

| 变化 | 解决 |
|---|---|
| `checks[]` 成为主体，每项带 `confidence` 与 `evidence[]` | 结论可追溯、可逐项对比 |
| `facts` 与 `checks` 分离 | 事实与判断在结构上分开 |
| `coverage` 独立成块 | 解释力边界成为一等公民 |
| `status` 五态化 | UNKNOWN 可被消费方识别 |

**不做兼容层。** 不提供 2.0 字段的兼容映射，也不保留 `findings`。

## 后果

### 好处

- 外部消费方能做逐项对比、能区分「没查到」与「查到了没问题」、能追溯每条结论的依据
- `checks[].id` 成为稳定契约，历史库可以跨版本对比（存完整 JSON 的价值在这里）
- 内部结构与外部格式对齐后，报告器只做渲染，不再各自解读

### 代价

- **所有消费 2.0 的脚本都会挂**。这是真实的破坏，不是理论风险
- 已经踩到一次：`connectors/ainas.py` 仍在读顶层 `device` / `storage` / `ai_accelerator`，升级后推送的设备信息会**全空**——不会报错，只是静默变成空值。事后补了两个契约测试才锁住
- 历史库里 2.0 时代的记录无法与新记录逐项对比（`checks` 字段结构不同）。`diff_reports` 对缺 `checks` 的报告会得到空结果，不会崩，但也比不出东西

### 缓解

- `REPORT_VERSION` 常量集中在 `model.py`，并在 `docs/OUTPUT.md` 写明「破坏性改动必须升版本」
- `CHANGELOG.md` 的 0.3.0 条目把所有破坏性变更单独列节
- 新增契约测试 `test_ainas_connector_maps_v3_report` 与 `test_zero_weight_category_visible_in_all_reporters`，防止「改了结构但某个消费方没跟上」再次静默发生
- 消费方应先校验 `meta.report_version`，不匹配时明确报错而不是猜

## 考虑过但否决的方案

**同时输出 2.0 与 3.0 两套字段。**

否决理由：两套字段要保持同步，就回到了「同一事实两处维护」的老问题，几个月后必然漂移。宁可一次性破坏，不要长期半新半旧。

**只加字段不删字段（非破坏性升级）。**

否决理由：2.0 的 `findings` 是字符串列表，无法在不改变语义的前提下承载 evidence 与 confidence。留着它只会让消费方继续读错的字段。
