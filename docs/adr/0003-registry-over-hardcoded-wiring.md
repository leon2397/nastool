# 0003. 用注册表替代硬编码编排

- 状态：生效
- 日期：2026-10-28（0.3.0）
- 影响：扩展成本、自描述能力、检查项的组织方式

## 背景

0.2.0 的编排层 `core/runner.py` 是硬编码的：它知道有哪些采集模块、哪些评分维度、哪些报告字段。

```python
# 0.2.0 的 runner.py（示意）
def run(options):
    platform = detect_platform()
    device   = get_device_info()
    storage  = collect_storage(options.storage_path)
    network  = collect_network()
    services = detect_services()
    ai       = detect_ai_accelerator()
    score    = compute_score(storage, network, device, services, ai)
    ...
```

加一项检测的完整成本是 **5 个文件**：

| 文件 | 要改什么 |
|---|---|
| `core/<某模块>.py` | 加采集与判断逻辑 |
| `core/scoring.py` | 加扣分规则 |
| `reporters/terminal.py` | 加显示行 |
| `reporters/json_reporter.py` | 加 JSON 字段 |
| `reporters/html_reporter.py` | 加 HTML 片段 |

这直接决定了产品的天花板：想从 22 项做到 92 项检测，就要重复 70 次这种五处同步。而且每多一处手写，就多一处不一致的机会——0.2.0 里「终端能显示、HTML 漏字段」正是这么来的。

## 决策

引入 `@check` 装饰器 + 全局注册表，把元信息与函数绑在一处。

```python
@check("storage.smart_health", "硬盘 SMART 健康", "storage",
       weight=6, platforms=["linux"], requires=["smart_data"],
       tags=["nas", "verify"])
def smart_health(ctx):
    ...
```

注册表提供三件事：

| 能力 | 实现 |
|---|---|
| 自描述 | `nastool --list-checks` 直接从注册表生成 |
| 过滤 | `resolve(only, skip, categories)` 支持 `fnmatch` 通配 |
| 元信息单一来源 | 权重、平台、依赖只写在装饰器里，评分与报告器读注册表 |

**新增一项检测 = 写一个函数。** 报告、评分、历史、对比全部自动包含。

注册时做两道校验：分类必须在 `CATEGORY_ORDER` 里、`id` 不可重复。两者都在 import 阶段直接抛 `RegistryError`，所以**带病代码无法启动**，不会出现「跑到第 30 项才发现 ID 冲突」。

## 后果

### 好处

- 扩展成本从「5 个文件」降到「1 个函数」。这是 0.3.0 能在一次重写里做出 55 项的直接原因
- 自描述：`--list-checks` 的输出永远与代码一致，不可能过期。这也是 [CHECKS-ROADMAP](../CHECKS-ROADMAP.md) 能改成「第一部分从注册表生成」的前提
- 元信息去重：权重只在装饰器写一次，`scoring.py` 从 `CheckMeta` 读，不存在两处不一致
- 测试可以直接断言「注册了多少项、每类几项」（`test_registry_loaded`）

### 代价

- **注册是 import 的副作用**。只有被 import 的模块才会注册，所以 `checks/__init__.py` 必须显式导入全部子模块。漏写一个模块，它的检查项就静默消失——没有报错，只是项数变少
- 装饰器把「元信息」和「实现」耦合在同一个文件里，无法在不 import 的情况下查看元信息
- 全局可变状态：`_REGISTRY` 是模块级 dict，测试之间可能互相污染（目前没有动态注册的需求，暂未受影响）

### 缓解

- `test_registry_loaded` 断言总项数与分类分布，漏 import 会被测试抓住
- `checks/__init__.py` 集中列出所有子模块导入，新增模块时只需改这一处
- `id` 重复直接抛异常而不是覆盖，避免两个模块抢同一个 ID 时静默丢失

## 考虑过但否决的方案

**用类继承 `Check` 基类**（前身项目的做法，`@register_check` + `run()` 方法）。

否决理由：一个只有单一方法、没有状态的类，用函数表达更直接。类的唯一好处是「可以覆写钩子」，但这里的检查项没有共享生命周期需要覆写。函数 + 装饰器让「加一项」的心智负担最小。

**用装饰器 + 显式列表双保险**（既要装饰器又要在列表里登记）。

否决理由：那样就退回了「两处同步」，正是要消除的问题。
