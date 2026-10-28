# 0002. 采集层不做判断

- 状态：生效
- 日期：2026-10-28（0.3.0）
- 影响：分层结构、`collect/` 与 `checks/` 的边界、扩展成本

## 背景

0.2.0 的采集器同时干三件事：执行命令、解析输出、**顺手判断好坏并攒 `warnings` / `errors`**。

```python
# 0.2.0 的 core/storage.py（示意）
def collect_storage(path):
    ...
    if use_percent >= 90:
        rep.warnings.append("磁盘快满了")      # ← 判断混进采集
    return rep
```

后果有三个，都在实际开发中撞到了：

**1. 同一个结论会在两个地方各写一遍**

采集器说「磁盘快满了」，`scoring.py` 又按自己的阈值算一遍，报告器再根据 `findings` 决定怎么显示。三处标准迟早对不上。

**2. 潜伏了真 bug**

`core/network.py` 里有一行 `rep.warnings.append(...)`，但那个函数里 `rep` 从未定义。它只在「链路 ≤100 Mbps」这一条分支执行——所以**在有线千兆的开发机上永远不触发**，直到某台百兆设备跑才 `NameError`。

这个 bug 的根因不是手滑，而是**采集函数不该有 `warnings` 这个字段可用**。

**3. 采集失败变成了错误结论**

`services.py` 读不到端口时返回空列表。采集层不做区分，于是「端口列表为空」既可能是「没开服务」也可能是「`ss` 命令不存在」，判定层无从分辨。

## 决策

**采集层只输出事实，判断只允许出现在 `checks/`。**

具体做法：

- 所有 `collect/*.py` 的返回类型（`*Facts` dataclass）**移除** `warnings` / `errors` / `ok` 这类判断字段
- 命名从动词式判断改为中性采集：`check_storage()` → `collect_storage()`、`check_network()` → `collect_network()`、`detect_services()` → `collect_services()`
- 采集器失败时的唯一表达是**空事实 + 记录到 `ctx.collector_errors`**，由判定层自行决定这是 UNKNOWN 还是 SKIP
- 判断所需的阈值不进采集层，由检查项通过 `ctx.threshold()` 取

## 后果

### 好处

- **只有一个地方定义「什么算问题」**：`checks/`
- `warnings.append` 这类 bug 在结构上不可能再出现——返回类型里没有这个字段
- 同一份事实可被多个检查项复用。13 个存储检查项共用一次 `df` / `lsblk` / `smartctl` 调用，靠 `ctx.storage` 的惰性缓存
- 采集器变得可测试：喂一段 `df` 输出，断言解析出的字段，不需要构造「健康/不健康」的场景

### 代价

- **检查项要自己写判断**，比「采集时顺手 append 一条 warning」啰嗦。一项检查平均 25–45 行，而采集层的一段判断只要 3 行
- 需要 `CheckContext` 这一层胶水来缓存与分发事实，多了一个间接层
- 采集器必须输出**所有可能用到**的原始字段，即使当前没有检查项用它。例如 `StorageFacts` 保留了 `inodes_use_percent`、`readonly`，哪怕判定逻辑以后才用

### 缓解

- `checks/_base.py` 提供 `R()` 与 `ev()` 两个构造助手，把样板压到最低
- `context.py` 统一处理「采集失败降级为空事实」，检查项不需要写 try/except

## 考虑过但否决的方案

**保留判断字段，但要求「只在一个地方判断」**——靠约定而不是结构来保证。

否决理由：约定会被打破，而结构不会。移除字段之后，想在采集层写判断都没有地方写，这比文档里加一条红线可靠得多。
