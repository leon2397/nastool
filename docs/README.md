# nastool 文档

> 按「你是谁 / 想做什么」分流。读一篇就够，不需要通读。

---

## 我想……

| 我想 | 读 |
|---|---|
| 先看看这工具是干什么的、装一下试试 | [项目 README](../README.md) |
| 知道某个参数的确切含义 | [CLI.md](CLI.md) |
| 搞懂为什么我的分数是这个数 | [SCORING.md](SCORING.md) |
| 查某一项检测到底在判什么、阈值多少 | [CHECKS.md](CHECKS.md) |
| 决定该用哪个场景（`nas` / `verify` / `dev` / `ai`） | [PROFILES.md](PROFILES.md) |
| 从报告里读出信息、写脚本消费 JSON | [OUTPUT.md](OUTPUT.md) |
| 追踪某块盘的老化趋势 | [HISTORY.md](HISTORY.md) |
| 排掉「为什么全是不适用 / 为什么读不到 SMART」 | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| 加一项新检测 / 改评分 / 提交代码 | [DEVELOPMENT.md](DEVELOPMENT.md)，规范见 [STANDARDS.md](STANDARDS.md) |
| 查某个词到底指什么 | [GLOSSARY.md](GLOSSARY.md) |
| 看这轮改了什么 / 还欠什么 / 踩过什么坑 | [memo/](memo/) |
| 下一版做什么、什么时候发 1.0 | [VERSION-PLAN.md](VERSION-PLAN.md) |
| 理解这套分层为什么是这样 | [ARCHITECTURE.md](ARCHITECTURE.md) + [adr/](adr/) |
| 知道还差哪些能力没做 | [CHECKS-ROADMAP.md](CHECKS-ROADMAP.md) |
| 看前身项目的设计遗产 | [DESIGN-NOTES.md](DESIGN-NOTES.md) |

---

## 文档清单

### 用户向

| 文档 | 内容 | 规模 |
|---|---|---|
| [CLI.md](CLI.md) | 全部参数、退出码、典型用法、环境依赖、已知行为细节 | 中 |
| [SCORING.md](SCORING.md) | 三层计算、权重矩阵、两条封顶规则、覆盖度、置信度，含手算示例 | 中 |
| [CHECKS.md](CHECKS.md) | **55 项检测逐条说明**：判什么、依据、每种情况给什么状态 | **大（核心）** |
| [PROFILES.md](PROFILES.md) | 四个场景的权重/阈值/范围差异，怎么选，`--enable` 与 `--only` 的交互 | 中 |
| [OUTPUT.md](OUTPUT.md) | JSON `report_version 3.0` 逐字段说明、`trend` 语义、消费示例 | 中 |
| [HISTORY.md](HISTORY.md) | 库结构、十种变化类型、证据级对比、现状限制 | 中 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 15 个典型现象：原因、验证命令、对策 | 中 |

### 开发者向

| 文档 | 内容 |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 四层结构、数据流、五个关键机制、四个扩展点、与旧架构的对比 |
| [STANDARDS.md](STANDARDS.md) | **开发规范**（强制）：分层依赖、异常契约、兼容承诺、提交格式、自审清单；`python tools/selfcheck.py` 可自动检查 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 加检测项（含完整示例）、加分类、加报告格式、加连接器、测试约定、发布流程 |
| [GLOSSARY.md](GLOSSARY.md) | 术语表：状态五态、覆盖度 vs 置信度、两个 weight 的区别 |
| [adr/](adr/) | 7 条架构决策的来龙去脉（为什么这样，放弃了什么） |
| [memo/](memo/) | **项目记忆**：工作日志、技术债台账、踩坑记录、未决问题 |

### 规划与历史

| 文档 | 内容 |
|---|---|
| [VERSION-PLAN.md](VERSION-PLAN.md) | **版本计划**：0.4.0 / 0.5.0 / 0.6.0 / 1.0.0 各做什么、破坏性变更预告、1.0 门槛、明确不做的决定 |
| [CHECKS-ROADMAP.md](CHECKS-ROADMAP.md) | 当前 55 项清单 + 前身 92 项中的缺口 + 价值判断（排期见版本计划） |
| [DESIGN-NOTES.md](DESIGN-NOTES.md) | 前身项目（v7.1.0-beta，92 检测器）的设计要点与 12 条真机 BUG 教训 |

---

## 三个必须先建立的概念

如果只看三段，看这三段。

### 1. 状态是五态，不是两态

```
✓ 通过    ! 告警    ✗ 严重    ? 不可判定    · 不适用
```

**`?` 与 `·` 的区别决定了整份报告的可信度**：

- `·` 不适用：这台机器没有这个概念，不计入覆盖度
- `?` 不可判定：该查但没查到，**不扣分但拉低覆盖度**，盲区太大时会封顶等级

详见 [CHECKS.md](CHECKS.md#0-先理解五个状态) 与 [ADR-0001](adr/0001-unknown-is-first-class.md)。

### 2. 分数会被强行压低

加权平均之后还有两条规则：

| 触发 | 封顶 |
|---|---|
| 存在任意 FAIL | 59（D） |
| 盲区 ≥ 50% | 74（C） |
| 盲区 ≥ 30% | 84（B） |

所以会出现「C 级但全部通过」——那表示**没查清**，不是有问题。详见 [SCORING.md](SCORING.md#4-两条封顶规则核心)。

### 3. 只有 15 项能产生「严重」

55 项里其余 40 项在设计上不可能 FAIL。「严重」这个词必须稀缺，否则它就不严重了。这 15 项决定了退出码、决定了封顶、决定了报告里那行红字。清单见 [CHECKS.md](CHECKS.md#只有-15-项能产生-fail)。

---

## 文档维护规则

这个项目因为文档与代码脱节吃过两次亏（一批实现位置指向已删除的 `core/` 目录），所以定下硬规则：

1. **单一来源。** 同一事实只在一个地方定义，其他地方引用链接。例如 profile 权重表只在 [PROFILES.md](PROFILES.md) 出现。
2. **代码改动同 PR 改文档。** 对照表见 [STANDARDS.md](STANDARDS.md#10-文档同步-硬-自动)。
3. **不写代码里没有的东西。** 不确定就去看代码，不要凭印象写。
4. **数字必须可复现。** 写「55 项」就该能对上 `nastool --list-checks` 的输出。

发现文档与代码不一致时，**以代码为准**，并请提 issue 修正文档。
