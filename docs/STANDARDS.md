# 开发规范

> 这是本项目的强制规范。**能机器检查的，就不该靠自觉** —— 文中标 `[自动]` 的条目由
> `python tools/selfcheck.py` 检查，提交前必须全绿。

---

## 0. 效力分级与三条底线

规范分三级，含义不同：

| 级别 | 含义 | 违反后果 |
|---|---|---|
| **硬规则** `[硬]` | 不可协商。标 `[自动]` 的由脚本拦截 | 提交被拒 / 必须改 |
| **软规则** | 应当遵守，破例要在 PR 或 journal 里写一句理由 | 评审时会被问 |
| **建议** | 风格偏好，团队约定 | 无 |

三条底线高于其他所有条款：

### 底线一：运行时零第三方依赖

`dependencies = []` 不是"目前恰好没有"，是**产品承诺**。检测工具会被拷到没有 pip、
没有外网、甚至是只读根文件系统的机器上跑。为了一个 yaml 解析引入 PyYAML，会让
`nastool` 在最需要它的场景里装不上。详见 [ADR-0006](adr/0006-zero-dependency.md)。

### 底线二：不修改被检测设备

除测速时写入并立即删除的临时文件外，**任何检测项都不得产生持久化副作用**。不删文件、
不改配置、不重启服务、不 `mount`。体检不能变成治疗。

### 底线三：结论可复现

同一台机器、同一时刻、同一场景，两次运行必须给出相同结论。任何引入随机性、时间窗口
依赖、缓存污染的实现都要避免。无法避免时（网速、负载），报告里要能看出这是瞬时值。

---

## 1. 分层与依赖方向 `[硬] [自动]`

四层单向依赖，**不允许反向或跨层**。这张表由 AST 扫描生成，`selfcheck` 会比对：

| 模块 | 允许依赖 | 实际 |
|---|---|---|
| `model.py` | 仅标准库 | ✅ 无内部依赖 |
| `profiles.py` | 仅标准库 | ✅ 无内部依赖 |
| `history.py` | 仅标准库 | ✅ 无内部依赖 |
| `registry.py` | `model` | ✅ |
| `diff.py` | `model` | ✅ |
| `collect/*` | 仅标准库 | ✅ 无内部依赖 |
| `context.py` | `collect`, `profiles` | ✅ |
| `scoring.py` | `model`, `profiles` | ✅ |
| `checks/*` | `model`, `registry`, `collect`, `checks/_base` | ✅ |
| `reporters/*` | `model` | ✅ |
| `connectors/*` | 仅标准库（只吃 dict） | ✅ |
| `engine.py` | `model`, `registry`, `profiles`, `context`, `scoring`, `checks` | ✅ |
| `cli.py` | 全部 | ✅ |

具体禁止：

- **`collect/` 不得 import `checks` / `registry` / `scoring`** —— 采集只拿事实，不判断
  （[ADR-0002](adr/0002-collect-does-not-judge.md)）。一旦采集器里出现 `Status.FAIL` 的念头，
  说明判定写错了层。
- **`checks/` 不得 import `reporters` / `engine` / `cli`** —— 判定不知道自己会被怎么呈现。
- **`reporters/` 不得 import `collect` 的实现**，只能通过 `Report` 上已有的字段取值。
  要展示新数据，先去 `collect/` 采、让判定项带上证据，不要绕过。
- **`connectors/` 只吃 `dict`**（`report.to_dict()`），不得 import 内部类型。连接器是最可能
  被第三方替换的部分，它必须只依赖序列化契约（[OUTPUT.md](OUTPUT.md)）。

判据：**如果删掉 `reporters/`，其余模块还能 import 成功吗？** 能，才是对的。

---

## 2. 命名与文件组织 `[硬]`

| 对象 | 规则 | 示例 |
|---|---|---|
| 检测项 id | `分类.小写下划线`，**发布后不可改** | `storage.smart_bad_sectors` |
| 检测函数 | 与 id 后半段同名，只用小写下划线 | `def smart_bad_sectors(ctx)` |
| 采集函数 | 统一 `collect_*` | `collect_storage()` |
| 事实类 | 统一 `*Facts` | `StorageFacts` |
| 契约类 | 简短名词，不加后缀 | `Report` / `Evidence` / `Coverage` |
| 报告器 | 统一 `*Reporter`，方法 `build/save` | `HTMLReporter` |
| 私有辅助 | 单下划线前缀 | `_numeric_evidence()` |
| 常量 | 全大写 | `REPORT_VERSION` / `CRITICAL_CAP` |

一个文件一个主题，不要建 `utils.py` 这种万能回收站（`collect/util.py` 是历史遗留，
已限定为"跨平台执行与读取"，不要再往里加判定逻辑）。

---

## 3. 编码风格 `[硬]`

- 编码 UTF-8，换行 LF（`.gitattributes` 已锁定）。**不要在 Windows 上让编辑器改成 CRLF。**
- 每个模块开头写 `from __future__ import annotations`（Python ≥3.8 下才能用 `list[str]` 这类写法）
- 类型标注：**函数签名与 dataclass 必须有**，函数内部变量不强制
- 行长不强制，但超过 ~100 列的表达式应考虑拆行
- 中文字符串直接写，不用 `\u` 转义
- 导入顺序：标准库 → 包内相对导入，空行分隔
- 不使用 `# type: ignore` 掩盖真实类型错误；必须用时加原因

没有强制 linter（零依赖原则同样适用于开发链）。作为补偿，`selfcheck` 检查下面这些
**能用 AST 可靠判断**的项目，其余靠评审：

`[自动]` 库代码裸 `print`、宽捕获静默吞异常、分层反向依赖、版本号三处一致、
文件编码与行尾（UTF-8 + LF）、文档链接与锚点、文档数字与代码一致、
文档里 `--flag` 的真实性、profile 与分类常量的一致性、台账编号与交叉引用、
技术债与未决问题是否已排期。

> 行尾检查是必要的：`.gitattributes` 已声明 `eol=lf`，git 提交时会转换，但
> **工作区**会一直不一致——Windows 上编辑一次就变回 CRLF，来回反复。
> 这项检查让"工作区是 LF"成为可验证的事实，而不是靠约定。

---

## 4. 异常处理契约 `[硬]`

三层各有各的责任，**不要串岗**：

| 层 | 责任 | 做法 |
|---|---|---|
| `collect/` | 外部命令/文件失败时不中断采集 | 返回空值/默认值，把原因记进 `errors` 列表，**不抛** |
| `checks/` | 只捕获可预期的错误 | 捕获后返回 `UNKNOWN` 并写 `error` 字段；**不要 try/except 一圈然后返回 PASS** |
| `engine/` | 最后兜底 | 任何未捕获异常 → `UNKNOWN` + `error`，进程不崩 |

硬性禁止与明确允许：

```python
except Exception:          # ✗ 宽捕获 + 静默吞掉
    pass

except Exception:          # ✗ 吞掉后假装通过
    return R(Status.PASS, "正常")

except UnicodeDecodeError:  # ✓ 窄捕获 + 默认值，是正当的降级
    pass                     #   （编码回退链、/proc 数字解析都靠这个模式）

except Exception as e:      # ✓ 宽捕获但降级有据：记录、返回 UNKNOWN
    return R(Status.UNKNOWN, f"读取失败：{e}", confidence=0.0)
```

确需宽捕获吞掉时（如资源清理、读错误详情失败不影响主错误），**必须带
`# noqa: BLE001` 和原因注释**，让下一读的人知道这不是漏写。

**裸 `raise` 不得穿透到 CLI**，唯一例外是参数错误——那种情况用 `EXIT_ERROR`（2）退出并
打印可执行的提示，不要抛 traceback 给用户。

不要在 `checks/` 里写重试循环。单项检查有 60 秒硬超时（POSIX），重试只会把超时吃掉。

---

## 5. 输出与副作用边界 `[硬] [自动]`

**允许写磁盘的地方只有四处**，多一处都要在 PR 里说明：

| 位置 | 写什么 | 控制手段 |
|---|---|---|
| 测速临时文件 | 50MB 随机数据，写完立即删 | `--no-speed-test` |
| `--out-dir` / `--output-file` | 报告文件 | 用户显式指定 |
| `--history-db` | SQLite 历史库 | 用户显式指定，默认 `~/.nastool/history.db` |
| 标准输出 | 报告正文 | — |

**库代码（`nastool/` 除 `cli.py` 与 `reporters/` 外）禁止 `print`。** 想调试请用返回值或
`verbose` 回调；`print` 会污染 `-o json` 的 stdout 管道。

---

## 6. 注释 `[硬]`

**注释与实现矛盾是缺陷，不是笔误。** 这个项目已经发生过两次：`profiles.py` 声称"权重为 0
的分类直接标 SKIP"（实际按 `active` 过滤），`registry.py` 声明了 `tags` 却从不参与筛选。
读者会照着注释做决定，所以错注释比没注释危害更大。

- 写**为什么**，不写**是什么**。
  `# 取最长匹配，因为 /mnt 和 /mnt/data 都会匹配` 有价值；`# 循环 disks` 没有价值。
- 阈值必须带出处或理由：`# RK3588 长期 80°C 以上会降频，取 70 作告警线`。
- 禁止提交注释掉的代码（`git` 记得住，不需要注释记）。
- 大段设计理由不要塞进代码，写 ADR，代码里留一行 `# 设计理由见 ADR-0004`。

---

## 7. 依赖红线 `[硬] [自动]`

- 运行时 `dependencies = []`，`selfcheck` 会拦。
- `optional-dependencies` 只能是**有则增强**：缺失时必须能降级运行。
  `config = ["PyYAML>=5.4"]` 是唯一一例——读了 yaml 配置就多一个提示，没有也能跑。
- **新增任何运行时依赖 = 必须先写 ADR**，说明为什么标准库做不到、代价是什么。
  历史上这条挡住了 `psutil`（想用它的 CPU 采样）、`requests`（想用它的重试）、
  `rich`（想用它的表格）。

---

## 8. 兼容性承诺 `[硬]`

| 契约 | 承诺 |
|---|---|
| **检测项 id** | 发布后**永不改名**。历史对比按 id 认项，改名等于把过去所有记录变成"消失+新增" |
| **`REPORT_VERSION`** | 独立于产品版本。字段增删改必须升它，并在 [OUTPUT.md](OUTPUT.md) 写迁移说明 |
| **历史库 schema** | `runs` 表结构变更必须有迁移逻辑，或明确声明"旧库不可读"并**升级时不静默丢数据** |
| **CLI 参数** | 只加不删。要删先标记弃用，至少保留两个 minor 版本 |
| **退出码** | `0` 健康 / `1` 存在严重问题 / `2` 运行错误。语义不可改——cron 与 CI 依赖它 |
| **Python 版本** | `>=3.8`。用新语法前先想清楚是否值得抬门槛 |

产品版本用 `0.x` 语义：**minor 可以有破坏性变更**，但必须在 `CHANGELOG.md` 的
"破坏性变更"节写清迁移方式。到 `1.0` 之后才承诺语义化版本。

---

## 9. 提交规范 `[硬]`

```
<type>: <中文主题，一句话说清做了什么>

<为什么这么做：问题是什么、为什么不选另一条路>

<验证证据：跑过什么、结果如何>
<遗留：明确没做的、已知的坑>
```

`type` 取值：

| type | 用于 |
|---|---|
| `feat` | 新增检测项、参数、能力 |
| `fix` | 修正错误行为 |
| `refactor` | 结构变动，行为不变 |
| `docs` | 只动文档 |
| `test` | 只动测试 |
| `perf` | 性能 |
| `chore` | 构建、版本号、忽略规则 |
| `release` | 发版提交 |

规则：

- 破坏性变更在 type 后加 `!`：`refactor!: 架构重建为四层`
- **一次提交一件事**。重构与改行为分开，格式化与逻辑分开——否则出问题时无法二分定位。
- 主题用中文，不用 "update"、"fix bug"、"优化" 这类无信息量的词。
- 提交前跑 `python tools/selfcheck.py && python -m pytest -q`，结果写进末段。

---

## 10. 文档同步 `[硬] [自动]`

**代码改动必须在同一个提交里改文档。** 这个项目因为文档与代码脱节吃过两次亏（`CHECKS-ROADMAP.md`
里一批实现位置指向已删除的 `core/` 目录）。

| 改了什么 | 必须同步 |
|---|---|
| 新增 / 删除检测项 | [CHECKS.md](CHECKS.md) 对应章节 |
| 改权重 / 阈值 | [CHECKS.md](CHECKS.md)、[PROFILES.md](PROFILES.md)、[SCORING.md](SCORING.md) |
| 改评分或封顶规则 | [SCORING.md](SCORING.md)（含重算示例） |
| 改 JSON 字段 | [OUTPUT.md](OUTPUT.md)；破坏性改动必须升 `REPORT_VERSION` |
| 加 / 改 CLI 参数 | [CLI.md](CLI.md) |
| 加场景 | [PROFILES.md](PROFILES.md) |
| 任何用户可见变更 | `CHANGELOG.md` |
| 做出取舍决定 | [adr/](adr/) 新增一条 |
| 发现新坑 / 新债 / 未决问题 | [memo/](memo/) 对应台账 |

四条硬规则：

1. **单一来源**：同一事实只在一个文件定义，其他地方写链接。权重表只在 [PROFILES.md](PROFILES.md)。
2. **不写代码里没有的东西**：不确定就去看代码，不要凭印象写。
3. **数字可复现**：写"55 项"就该能对上 `nastool --list-checks`。`[自动]` 校验。
4. **以代码为准**：文档与代码冲突时改文档，并把它记进 [memo/gotchas.md](memo/gotchas.md)。

---

## 11. 提交前自审清单

```
[ ] python tools/selfcheck.py 全绿
[ ] python -m pytest -q 全通过
[ ] python -m nastool --no-speed-test 端到端能跑，结论与改动预期一致
[ ] 新增检测项：id 唯一、分类合法、读不到时返回 UNKNOWN 而非 WARN/FAIL
[ ] 新增检测项：数值证据带了 num，有方向语义才带 trend，拿不准就不带
[ ] 改了 scoring / reporters：六条不变式测试仍通过
[ ] 文档已按 §10 同步
[ ] 影响面写进 memo/journal.md；新发现的债/坑/问题已登记
[ ] 提交信息说明了"为什么"和"验证证据"
```

标 `[自动]` 的项不写进清单——脚本会管，人只管脚本管不了的。

---

## 12. 破例流程

想违反硬规则时，**不要默默违反**，也不要为了绕开规则去改规则。走这条路：

1. 在 [adr/](adr/) 新建一条，编号递增，写：想做什么、为什么必须破例、不破例的代价、
   破例后的代价、将来什么条件下回收。
2. 在 [open-questions.md](memo/open-questions.md) 登记，直到 ADR 定稿。
3. 破例处代码加一行注释指向 ADR 编号。

规范本身也是可以被修改的——但要走同样的路径，而不是这次先这样、下次再说。

---

## 附：规范与流程的关系

| 文件 | 回答什么 |
|---|---|
| **本文** | 必须符合什么 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 具体怎么做（加检测项、加分类、加报告格式的完整步骤） |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 为什么这样分层 |
| [adr/](adr/) | 某个决定的来龙去脉与被放弃的方案 |
| [memo/](memo/) | 干活时的记忆：日志、技术债、踩过的坑、未决问题 |
