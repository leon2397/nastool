# 架构

> 四层，依赖单向：**collect → checks → 聚合 → 呈现**。
>
> 一句话概括设计目标：**新增一项检测 = 写一个带 `@check` 的函数**，其他任何地方都不用改。
>
> 相关：[DEVELOPMENT.md](DEVELOPMENT.md)（怎么加）、[adr/](adr/)（为什么这样）

---

## 1. 全景

```
┌─────────────────────────────────────────────────────────────┐
│  cli.py          解析参数 → RunOptions → 调 run() → 输出/上报  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  engine.py       按 profile/--only/--skip 挑出检查项，逐个执行  │
│                  · 平台不适用 → SKIP                          │
│                  · 依赖缺失   → SKIP                          │
│                  · 抛异常     → UNKNOWN + error               │
│                  · 超时       → UNKNOWN                      │
│                  · 生成设备指纹                                │
└──────┬──────────────────────┬───────────────────────┬────────┘
       │                      │                       │
┌──────▼──────┐   ┌───────────▼─────────┐   ┌─────────▼───────┐
│ context.py  │   │ checks/  (55 项判定) │   │ registry.py     │
│ 惰性采集     │──▶│ 每项 @check 声明     │◀──│ 元信息注册表     │
│ 能力查询     │   │ 元信息/权重/依赖      │   │ 过滤与自描述     │
│ 阈值解析     │   └───────────┬─────────┘   └─────────────────┘
└──────┬──────┘               │
       │                      │ CheckResult（含 Evidence / confidence）
┌──────▼──────────┐   ┌───────▼──────────┐
│ collect/        │   │ scoring.py       │
│ 只读事实，不判断 │   │ 分类得分 → 总分   │
│ 7 个采集器       │   │ 两条封顶 + 覆盖度 │
└─────────────────┘   └───────┬──────────┘
                              │ Report
                    ┌─────────▼──────────┐
                    │ reporters/         │
                    │ terminal/json/html │
                    └─────────┬──────────┘
                              │
              ┌───────────────┴───────────────┐
        history.py (SQLite)              connectors/ (可选)
        diff.py (逐项对比)                webhook / ainas
```

---

## 2. 各层职责与边界

### 契约层 `model.py`

**唯一的数据定义处。** 四层都只认这里的类型，谁都不许自造结构。

| 类型 | 作用 |
|---|---|
| `Status` | 五态枚举（PASS/WARN/FAIL/SKIP/UNKNOWN）+ `.judged` / `.glyph` / `.label` |
| `Evidence` | 一条可复核的观测事实（source/key/value/num/trend） |
| `CheckResult` | 单条检查的完整结论 |
| `Coverage` | 覆盖度（`applicable` / `percent` / `blind_percent` 是派生属性） |
| `CategoryScore` | 分类得分 |
| `Score` | 总分、等级、封顶状态、AI 参考分 |
| `ReportMeta` | 版本、场景、时间、指纹、生效参数 |
| `Report` | 全部聚合，含 `to_dict()` / `healthy` / `by_category()` |
| `REPORT_VERSION` | 格式契约版本 |

### 注册层 `registry.py`

`@check` 装饰器把元信息（分类/权重/平台/依赖/标签）与函数绑定，存进 `_REGISTRY`。

```python
@check("storage.smart_health", "硬盘 SMART 健康", "storage",
       weight=6, platforms=["linux"], requires=["smart_data"],
       tags=["nas", "verify"])
def smart_health(ctx): ...
```

注册时校验：分类必须在 `CATEGORY_ORDER` 里，`id` 不可重复（重复直接抛 `RegistryError`，在 import 阶段就崩，不会带病上线）。

`resolve(only, skip, categories)` 负责筛选，支持 `fnmatch` 通配。

### 采集层 `collect/`

**只做一件事：把机器上的事实读出来。** 这一层**没有** `warnings` / `errors` / `ok` 这类判断字段——判断只允许出现在 `checks/`。

| 模块 | 采集内容 |
|---|---|
| `platform.py` | NAS 平台识别、容器/虚拟化判断、root 判定、数据根目录 |
| `device.py` | CPU、内存、主板、温度传感器、运行时长 |
| `storage.py` | 挂载点容量、物理盘、RAID（mdstat/zpool/btrfs）、SMART、测速 |
| `network.py` | 网卡、网关、DNS、外网、对端可达性 |
| `services.py` | 监听端口、服务识别、Docker 容器 |
| `security.py` | SSH 配置、防火墙、证书、smb.conf、/etc/exports、fail2ban（**全部只读**） |
| `ai_accel.py` | 加速器探测、推理测试 |
| `util.py` | 命令执行（含编码回退）、文件读取、默认路径挑选 |

每个采集器返回一个 `*Facts` dataclass：纯数据，没有方法（除了派生的属性计算）。

### 判定层 `checks/`

7 个模块，55 个函数。每个函数签名统一：

```python
def some_check(ctx: CheckContext) -> dict   # 由 _base.R() 构造
```

拿 `ctx` 访问事实与阈值，返回状态 + 摘要 + 证据 + 置信度。**不直接碰文件系统或执行命令**（那些属于 `collect/`）。

### 编排层 `engine.py`

`run(options, progress) -> Report`。核心是 `_run_one()` 的四道关卡：

| 顺序 | 检查 | 结果 |
|---|---|---|
| 1 | 平台是否适用 | 不适用 → SKIP（附「需要 linux」等原因） |
| 2 | 依赖能力是否满足 | 缺失 → SKIP（附具体缺哪个） |
| 3 | 执行（POSIX 下带 `SIGALRM` 超时） | 抛异常/超时 → UNKNOWN + `error` 字段 |
| 4 | 归一化返回值 | 补 id/title/category/weight，记录耗时 |

**任何单项失败都不会中断整次检测。** 这是产品的可用性底线。

### 聚合层 `scoring.py`

纯算术，**没有任何具体判定逻辑**。分类得分 → 总分 → 两条封顶 → 覆盖度 → 置信度。见 [SCORING.md](SCORING.md)。

### 呈现层 `reporters/`

三个报告器都只依赖 `Report`，互相不知道对方存在。加一种输出格式不需要动检测逻辑。

### 输出与持久化

| 模块 | 职责 |
|---|---|
| `history.py` | SQLite 存完整报告 JSON |
| `diff.py` | 两份报告的逐项与证据级对比 |
| `connectors/` | 可选上报（`webhook` / `ainas`），默认不启用、不 import |

---

## 3. 一次检测的完整路径

```
nastool -p verify --only storage.* -v
  │
  ├─ cli.py        解析参数 → RunOptions(profile="verify", only=["storage.*"], verbose=True)
  │
  ├─ engine.run()
  │   ├─ profile = with_categories(get_profile("verify"), [])   # 应用场景
  │   ├─ ctx = CheckContext(options, profile)
  │   ├─ ctx.platform          ← 先采平台，它决定后续哪些项适用
  │   ├─ resolve(only=["storage.*"], skip=[], categories=None)  # --only 时跳过场景过滤
  │   │     → 13 个 storage 检查项
  │   ├─ for meta in metas:
  │   │     _run_one(meta, ctx, timeout=60)
  │   │        ├─ ctx.has("linux")?  → 不适用则 SKIP
  │   │        ├─ ctx.has("smart_data")? → 缺失则 SKIP
  │   │        └─ meta.function(ctx)
  │   │              └─ ctx.storage   ← 第一次访问触发 collect_storage()，之后复用
  │   │                    └─ 读 df / lsblk / smartctl ...
  │   └─ compute(checks, profile, ai_facts)
  │
  └─ Report → TerminalReporter(verbose=True).print(report)
            → [可选] store.save() / diff_reports() / connector.push()
```

关键点：**13 个存储检查项只采一次磁盘信息**。没有惰性上下文的话，`df` 会被执行 13 次。

---

## 4. 五个关键机制

### 惰性采集（`context.py`）

```python
@property
def storage(self) -> StorageFacts:
    return self._get("storage", lambda: collect_storage(...), StorageFacts)
```

- 第一次访问执行采集，之后命中缓存
- **采集器抛异常时降级为空事实**，并记入 `collector_errors`，对应检查项自然落到 UNKNOWN
- 报告末尾的「检测警告」会显示这些错误

### 能力查询（`ctx.has()`）

检查项用字符串声明依赖，而不是写 `if platform == "linux"`：

| 类别 | 取值 |
|---|---|
| 平台 | `linux` / `windows` / `macos` / `any` |
| 权限 | `root` / `not_container` |
| 数据 | `smart_data` / `physical_disks` / `raid` / `docker` / `ssh_config` / `certs` / `smb_config` / `nfs_config` |
| 工具 | 任意命令名，转 `shutil.which()` |

好处：**缺依赖时引擎直接标 SKIP，检查项自己永远不需要写「如果没有 X 就跳过」**。这样不可能出现「缺 smartctl 却报 SMART 正常」。

### 异常收敛

```python
except Exception as e:
    return CheckResult(..., status=Status.UNKNOWN,
                       summary="检查执行失败，本次无法判定",
                       error=f"{type(e).__name__}: {e}")
```

`error` 字段区分了两种完全不同的失败：硬盘真有坏道（`status=fail`, `error=""`）vs 检查代码自己崩了（`status=unknown`, `error="KeyError: ..."`）。

### 单项超时

POSIX 下用 `signal.SIGALRM`，Windows 无此机制（依赖各采集器自身的 subprocess timeout）。超时被当作异常捕获 → UNKNOWN。

### 设备指纹

```
sha256(hostname | arch | platform_model | vendor)[:16]
```

用于历史对比时校验「这两份报告是不是同一台机器」。**不是安全标识**。

---

## 5. 四个扩展点

| 想做什么 | 改哪里 | 影响面 |
|---|---|---|
| 加一项检测 | 在 `checks/<分类>.py` 加一个 `@check` 函数 | 零——报告/评分/历史/对比全自动包含 |
| 加一个分类 | `CATEGORY_ORDER` + `CATEGORY_NAMES` + 新 `checks/<cat>.py` + 各 profile 的 `weights`/`active` | 三处常量 + 一个文件 |
| 加一种输出格式 | 新建 `reporters/xxx.py`，只依赖 `Report` | 采集与判定完全不动 |
| 加上报通道 | 继承 `connectors/base.py: BaseConnector`，在 `connectors/__init__.py` 注册 | 默认不 import，不影响离线使用 |

---

## 6. 为什么这样分层

### 旧架构的问题

0.2.0 的结构是「采集模块里夹着判断，判断结果又被三个报告器各自解读一遍」：

```
core/storage.py   → 采集 + 判断 + 攒 findings
core/scoring.py   → 根据 findings 算分
reporters/*.py    → 各自再判断一次该显示什么
```

后果：

| 症状 | 根因 |
|---|---|
| 加一项检测要改 5 个文件 | 判断逻辑散在采集/评分/三个报告器里 |
| 「读不到」被当成「坏掉」 | 没有独立状态，只能塞进 PASS 或 FAIL |
| 终端能显示、HTML 漏字段 | 三个报告器各写一遍取值逻辑 |
| 结论与分数矛盾 | 评分和报告各自判断，判断标准会漂移 |

### 现在的边界

| 规则 | 强制方式 |
|---|---|
| 采集层不做判断 | 字段里没有 `warnings`/`errors`/`ok`，想判断都没地方放 |
| 判定只在 `checks/` | `scoring.py` 只做算术，`reporters/` 只做渲染 |
| 报告器不碰采集 | 只接 `Report`，拿不到 `ctx` |
| 单项失败不致命 | `engine._run_one()` 统一兜底 |

详见 [ADR-0002](adr/0002-collect-does-not-judge.md) 与 [ADR-0003](adr/0003-registry-over-hardcoded-wiring.md)。

---

## 7. 代码规模

| 部分 | 行数 |
|---|---:|
| `collect/`（7 采集器 + util） | 2,921 |
| `checks/`（55 项判定 + `_base`） | 1,486 |
| 契约 + 注册 + 场景 + 上下文 | 831 |
| 引擎 + 评分 + 历史 + 对比 | 815 |
| 报告器（terminal / json / html） | 783 |
| CLI + 连接器 + 包入口 | 602 |
| **合计** | **7,438** |

零第三方依赖（`PyYAML` 仅可选）。
