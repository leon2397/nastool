# 开发指南

> 面向要改这个项目的人。核心只有一句：**新增一项检测 = 写一个函数**。
>
> 相关：[ARCHITECTURE.md](ARCHITECTURE.md)（分层为什么这样）、[CHECKS.md](CHECKS.md)（现有 55 项怎么写判定的）

---

## 1. 环境

```bash
git clone <repo> && cd nastool
python -m pip install -e ".[dev]"        # 只有 pytest 一个开发依赖
python -m pytest -q                       # 54 passed
python -m nastool --no-speed-test -v      # 端到端跑一次
```

要求 Python ≥ 3.8。**运行时不依赖任何第三方包**，请不要为了方便引入。

---

## 2. 加一项检测

### 最小可用版

```python
# nastool/checks/storage.py 末尾
from ..model import Status
from ..registry import check
from ._base import R, ev

@check("storage.bitrot_scan", "静默损坏扫描", "storage",
       weight=3, platforms=["linux"], requires=["btrfs"])
def bitrot_scan(ctx):
    s = ctx.storage
    if not s.raids:
        return R(Status.SKIP, "没有可扫描的阵列")

    errors = sum(len(r.errors) for r in s.raids if r.kind == "btrfs")
    if errors:
        return R(Status.FAIL, f"检测到 {errors} 处校验错误",
                 detail="Btrfs 校验和不匹配说明数据已静默损坏",
                 suggestion="从备份恢复受影响文件；检查内存与线缆",
                 evidence=[ev("btrfs device stats", "csum_errors", errors,
                              num=errors, trend="up_bad")],
                 confidence=0.95)
    return R(Status.PASS, "未检测到校验错误", confidence=0.9)
```

**不需要注册、不需要改报告器、不需要改评分。** 导入 `nastool.checks` 时装饰器就把它挂进注册表了。

### `@check` 参数

| 参数 | 必填 | 说明 |
|---|:--:|---|
| `id` | ✓ | `分类.名称`，小写下划线。**一旦发布不可改**（历史对比靠它） |
| `title` | ✓ | 中文显示名，尽量简短（终端里和别的项并排显示） |
| `category` | ✓ | 必须是 `CATEGORY_ORDER` 里的值，否则 import 时就抛 `RegistryError` |
| `weight` | | 1–6，同类内相对重要性。默认 1 |
| `platforms` | | `["linux"]` / `["any"]`。默认空 = 任何平台都跑 |
| `requires` | | 依赖能力，见下。默认空 |
| `tags` | | 元数据（`nas` / `verify` / `slow` / `ai`）。**当前只做记录，不参与筛选** |
| `description` | | 长说明，`--list-checks` 不显示，留给将来 |

### `requires` 可用值

声明依赖后，引擎会**自动**在条件不满足时标 SKIP，你的函数根本不会被调用——所以函数里不需要写「如果没有 X 就返回 SKIP」。

| 值 | 含义 |
|---|---|
| `linux` / `windows` / `macos` | 平台（也可写在 `platforms` 里，二者等效） |
| `root` | 需要 root / 管理员 |
| `not_container` | 不能在容器内 |
| `smart_data` | 读到了 SMART 数据 |
| `physical_disks` | 识别到物理盘 |
| `raid` | 检测到阵列 |
| `docker` | Docker 可用 |
| `ssh_config` | 找到 sshd_config |
| `certs` | 找到可解析的证书 |
| `smb_config` / `nfs_config` | 找到 smb.conf / /etc/exports |
| 其他任意字符串 | 当作命令名，走 `shutil.which()` |

### 返回状态的选择

| 情况 | 用 |
|---|---|
| 读到了，正常 | `PASS` |
| 读到了，有问题但可用 | `WARN` |
| 读到了，确认严重 | `FAIL` |
| **读不到 / 权限不足 / 采集器返回空** | **`UNKNOWN`** |
| 平台不支持 / 依赖缺失 / 没有可检对象 | `SKIP` |

最常见的错误是**把「读不到」写成 WARN 或 FAIL**。`grep` 一下你写的 `Status.WARN`，逐个问自己「这是确认有问题，还是只是没看到？」后者必须改成 UNKNOWN。

### 证据怎么写

```python
ev(source, key, value, note="", num=None, trend="")
```

| 参数 | 要求 |
|---|---|
| `source` | 数据从哪来：命令名、文件路径、接口名。要能让别人复现 |
| `key` | 具体指标名，snake_case |
| `value` | 人可读的字符串。传数字会自动转 |
| `num` | **数值型指标必须给**，否则历史对比看不到它 |
| `trend` | 有明确好坏方向才给，见下 |

`trend` 的判断标准：

| 问题 | 答案 | 该填 |
|---|---|---|
| 数值涨了是坏事吗？ | 是 | `up_bad` |
| 数值涨了是好事吗？ | 是 | `up_good` |
| 涨跌都不代表好坏吗？ | 是 | 不填 |

**拿不准就不填。** 填错的后果是历史对比出现假警报（前身踩过「运行时长 +0.1h 报成恶化」），不填的后果只是不参与好坏判断。

典型漏填：温度、负载、通电时长、进程数、端口数——这些涨跌正常，都是中性。

### 置信度怎么给

不填时引擎按状态给默认值（PASS 0.9 / WARN 0.85 / FAIL 0.85 / UNKNOWN 0）。需要覆盖时：

| 场景 | 建议值 |
|---|---|
| 文件系统/内核直接回答（`os.path.exists`、mdstat） | 0.95–1.0 |
| 走了回退路径（读了配置文件推断） | 0.80–0.88 |
| 数据来自第三方命令且可能有版本差异 | 0.85–0.9 |
| 明确无法判定 | 0.0 |

### 建议写详实

WARN / FAIL 时应给 `suggestion`——这是报告里唯一告诉用户「接下来做什么」的字段。写「有问题请检查」没有价值，写「改用 `root_squash`（默认），仅在确有需要时对特定主机放开」才有。

---

## 3. 加一个分类

比加检查项麻烦，因为涉及评分。四处改动：

```python
# 1. nastool/model.py
CATEGORY_ORDER = [..., "backup"]                 # 决定报告中的顺序
CATEGORY_NAMES = {..., "backup": "备份"}

# 2. 新建 nastool/checks/backup.py，写 @check(category="backup") 的函数
#    （别忘了在 checks/*.py 的 import 链里被导入——见 checks/__init__.py）

# 3. nastool/profiles.py —— 给需要它的场景加权重与 active
"nas": Profile(..., weights={..., "backup": 8}, active=[..., "backup"])

# 4. 若要有阈值，加进 _BASE_THRESHOLDS 再在场景里覆盖
```

加了分类之后，`--enable backup` 会自动成为合法取值（CLI 的 `choices` 读的是 `CATEGORY_ORDER`）。

---

## 4. 加一种报告格式

新建 `nastool/reporters/xxx.py`，只接 `Report`：

```python
class XXXReporter:
    def build(self, report: Report) -> str:
        return "..."

    def save(self, text: str, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path
```

然后在 `cli.py` 的 `_write_reports()` 加一个分支、`-o` 的 `choices` 加一个值。**采集与判定完全不用动。**

约束：不要从 `ctx` 取数据，只能用 `Report` 里已有的东西。要展示新数据，先去 `collect/` 采、再让判定项带上证据。

---

## 5. 加上报通道

```python
# nastool/connectors/myhook.py
from .base import BaseConnector

class MyConnector(BaseConnector):
    name = "myhook"

    def __init__(self, url="", **kwargs):
        self.url = url

    def push(self, payload: dict) -> tuple:
        """payload = report.to_dict()，格式见 docs/OUTPUT.md"""
        try:
            ...
            return True, "已上报"
        except Exception as e:
            return False, f"上报失败：{e}"
```

在 `connectors/__init__.py` 的注册表里加一行，`--push` 的候选值会自动包含它。

**注意 payload 是 `report_version 3.0` 结构**：事实数据在 `payload["facts"]`，平台在 `payload["platform"]`。不要读 2.0 时代的顶层 `device` / `storage` ——它们在 3.0 里已不存在（这个坑真实发生过一次）。

---

## 6. 测试

```bash
python -m pytest -q                    # 全部 54 项
python -m pytest -q --junit-xml=r.xml  # 终端汇总可能被吞时用这个取结果
python -m pytest tests/test_smoke.py -k cap -v
```

### 两类必须有的测试

**1. 不变式测试**（`tests/test_smoke.py`）——保护产品的可信度根基：

| 测试 | 保护什么 |
|---|---|
| `test_unknown_does_not_deduct_category_score` | UNKNOWN 不扣分类分 |
| `test_failure_caps_total_at_59` | 有 FAIL 必须封顶 |
| `test_small_blind_spot_does_not_cap` | 盲区小时不该封顶（防过度保守） |
| `test_warn_does_not_cap` | WARN 不触发严重封顶 |
| `test_skipped_excluded_from_scoring` | SKIP 不进分母 |
| `test_zero_weight_category_visible_in_all_reporters` | 三个报告器对同一份数据说法一致 |

**改 `scoring.py` 或 `reporters/` 后一定要跑这组。** 它们不是「测覆盖率」，是在守边界。

**2. 解析器测试**（`tests/test_parsers.py`）——喂真实命令输出片段，断言解析正确。新写采集器时照这个模式加。

### 不需要测的

- 真实硬件行为（没有真机就 mock 数据）
- 系统命令的可用性（用 `ctx.has()` 表达依赖，测这个没意义）

---

## 7. 文档同步

**代码改动必须在同一个提交里改文档**——完整的对照表与四条硬规则见
[STANDARDS.md](STANDARDS.md#10-文档同步-硬-自动)。那是唯一权威来源，这里不再复制。

---

## 8. 发布

版本号在三处，必须同步：

```bash
VERSION                 # 0.3.4
nastool/__init__.py     # __version__ = "0.3.4"
pyproject.toml          # version = "0.3.4"
```

三项都改完后：

```bash
python tools/selfcheck.py             # 规范自检（含版本一致性）
python -m pytest -q
python -m nastool --no-speed-test -o all --out-dir /tmp/relcheck
git add -A && git commit -m "release: 0.3.4"
git tag v0.3.4
```

`CHANGELOG.md` 用「新增 / 变更 / 修复 / 移除」分节。破坏性变更单独标 **破坏性变更** 并写迁移方式。

---

## 9. 代码风格

完整规范见 [STANDARDS.md](STANDARDS.md)——分层依赖、命名、异常契约、输出边界、依赖红线、
兼容承诺、提交格式都在那里，`python tools/selfcheck.py` 会自动检查其中能机器判断的部分。
这里是开发时最常翻的两条速查：

- **异常**：采集层失败返回空值并记录；检查层捕获后返回 `UNKNOWN` + `error`；禁止 `except Exception: pass`
  静默吞（宽捕获必须 `# noqa` + 原因）。
- **编码**：Windows 走 `collect/util.py: run()` 的 UTF-8 → mbcs → locale 回退链，**不要自己 `decode()`**。
