# 踩坑记录

> 每条必须有 **守门**：哪条测试或自检规则能防止它复发。没有守门的坑要在
> [debt.md](debt.md) 里登记一条"补守门"，否则它一定还会被踩第二次。
>
> 这是四本台账里最贵的资产——债务可以慢慢还，坑不记就会反复付学费。
> 规则见 [README.md](README.md)。

---

## GOTCHA-001 报告格式升级，消费者没跟

**现象** `report_version` 从 2.0 升到 3.0 后，AINAS 连接器推给后端的设备信息全部是空值，
但上报返回成功。

**根因** 连接器读的是 2.0 的顶层字段 `payload["device"]` / `["storage"]` / `["ai_accelerator"]`。
3.0 把这些挪进了 `payload["facts"]` 和 `payload["platform"]`。用 `.get()` 取不存在的键返回
`None`，`None.get(...)` 又走了 `or {}` 兜底——于是静默产出空值，一路"成功"到底。

**规避** 报告结构改动时，**把所有消费者找出来一起改**。`grep -rn 'payload\["' nastool/`
应该能一眼看完（现在连接器只有两个）。

**守门** ✅ `test_ainas_connector_maps_v3_report`（断言每个字段的映射）、
`test_ainas_connector_tolerates_missing_facts`（缺字段只降级不抛）。

---

## GOTCHA-002 Windows 防火墙状态被误判为"全部关闭"

**现象** 明明防火墙开着，报告说"所有配置档均未启用"。

**根因** 代码解析 `Get-NetFirewallProfile | ConvertTo-Csv` 的输出，找 `,True`（逗号后紧跟 True）。
但 PowerShell 的 CSV 会把布尔值加引号，实际是 `"Domain","True"`。匹配失败 → 全部判为关闭。

**规避** 解析 PowerShell 的 CSV 输出时，**布尔值是带引号的字符串**，不是裸 `True`/`False`。
更稳的做法是 `ConvertTo-Json` 再用 `json.loads`，别自己切字符串。

**守门** ⚠️ 暂无自动守门。Windows 专属分支，测试环境不覆盖。已登记 [DEBT-013](debt.md#debt-013-一半的坑没有守门测试)。

---

## GOTCHA-003 `w32tm` 输出是 GBK，按 UTF-8 解码后全是乱码

**现象** Windows 时间同步检查永远报"未同步"。

**根因** 代码搜索"源"/"Source"关键字，但 `subprocess` 用 UTF-8 解码 GBK 输出得到乱码，
关键字自然搜不到。

**规避** 统一走 `collect/util.py: run()` 的编码回退链（UTF-8 → `mbcs` → `locale`）。
**任何地方都不要自己 `.decode()`**。另外这个检查后来改成 `w32tm /query /source` 直接读值，
不再解析表格——少解析就少出错。

**守门** ⚠️ 暂无自动守门（同上）。

---

## GOTCHA-004 中性指标被报成"指标恶化"

**现象** 两次运行之间"运行时长 +0.1 小时"被标为"指标恶化"。温度、负载、进程数同样中招。

**根因** 历史对比只看数值变化方向，不知道"涨了是好是坏"。uptime 涨了当然正常。

**规避** `Evidence.trend` 三态语义：`up_bad`（涨是坏事，如坏扇区数）、`up_good`（涨是好事，
如可用空间）、`""`（中性，如温度、uptime、端口数）。**只有标了方向的数值才参与好坏判断。**
拿不准就不标——漏标的代价是少一条洞察，标错的代价是假警报，后者更伤信任。

**守门** ✅ `test_diff_ignores_neutral_evidence`（中性证据变化不产生恶化结论）。

---

## GOTCHA-005 覆盖度被算成 39%，报告看起来像残废

**现象** Windows 上跑出来"覆盖 39.2%"，用户以为工具坏了。

**根因** 覆盖率分母用了 `total`（全部检测项），但 31 项 Linux 专属检查在 Windows 上本来就是
SKIP。用"全部项"当分母，等于因为"这台机器不是 Linux"而惩罚它。

**规避** 分母必须是 **applicable = total − skipped**。同时报告里要显式说明
"本平台有 N 项不适用"，让用户知道这不是缺陷。

**守门** ✅ `test_skipped_excluded_from_scoring`、`test_small_blind_spot_does_not_cap`
（后者防止反向错误：少量盲区不该触发封顶）。

---

## GOTCHA-006 同一份数据，三个报告器三种说法

**现象** `verify` 场景下 `score.categories[]` 里有 AI 算力，终端和 HTML 的分项图里没有。

**根因** 终端和 HTML 用 `if c.weight > 0` 过滤分类，而 `verify` 场景的 `ai` 权重恰好是 0
（只展示不计分）。JSON 直接序列化，没有过滤。

**规避** 过滤条件应该是"**有没有判定**"，不是"有没有权重"。权重为 0 但判定了的，要显示并
标注"仅展示不计分"。任何"按权重过滤"的想法都要先问：这是展示逻辑还是计分逻辑？

**守门** ✅ `test_zero_weight_category_visible_in_all_reporters`。

---

## GOTCHA-007 全部不适用，被写成"全部通过"

**现象** `--only storage.*` 过滤后终端输出"73 项均不适用"，同时又说"全部通过"。

**根因** 汇总文案的判断条件只看了"有没有 FAIL/WARN"，没看"有没有真的判定过"。全 SKIP 满足
"没有失败"，于是走了成功分支。

**规避** 文案有三种情况不是两种：有判定且全过 / 有判定但有失败 / **根本没判定**。第三种必须
单独措辞，否则就是在报告里说假话。

**守门** ⚠️ 暂无自动守门（文本断言脆弱）。已登记 DEBT-013。

---

## GOTCHA-008 `/tmp` 在 Windows 上不是临时目录

**现象** 用 `--storage-path /tmp` 测试，工具报"路径不存在"，但以为它该存在。

**根因** Windows 的 Python 把 `/tmp` 解析成当前盘符根下的 `\tmp`，不是 Git Bash 里的 `/tmp`。
从 MSYS/Git Bash 里传路径给 Python 时最容易踩。

**规避** 跨平台验证一律用**相对路径**（`tmpr/xxx`），不要用 shell 的绝对临时路径。
文档示例也应优先用相对路径或明确的平台路径。

**守门** ⚠️ 无（约定问题，靠这条记录）。

---

## GOTCHA-009 注释比代码更会骗人

**现象** 两次：
① `profiles.py` 文档串写"权重为 0 的分类，其检查项直接标 SKIP"，实际过滤靠 `active`，
`verify` 场景的 `ai` 权重 0 但照样跑 4 项；
② `registry.py` 声明 `tags: Sequence[str]` 并注明可用来筛选，实际从不参与筛选。

**根因** 写注释时描述的是"设计意图"，后来实现变了（或从没实现），注释没跟着改。

**规避** 注释里的每个**行为断言**都要能被代码验证。写不了验证方式的，改成疑问句或删掉。
`selfcheck` 能查出"文档说 55 项但代码是 54 项"这类数字矛盾，但查不出语义矛盾——这层仍要靠人。

**守门** ⚠️ 部分：`selfcheck` 校验数字与参数真实性；语义矛盾无守门。

---

## GOTCHA-010 `NameError` 潜伏在从未被走到的分支里

**现象** `network.py` 在 `rep.warnings.append(...)` 处有个未定义变量 `rep`，代码存活了很久
没被发现。

**根因** 那个分支只在链路速率 ≤100 Mbps 时触发。开发机是千兆，测试机器也是千兆——分支从未
执行，语法检查也不会报（`NameError` 是运行时错误）。

**规避** 重构时优先用**统一出口**（0.3.0 直接把判断逻辑从采集层剥掉，那段代码整个消失）。
另外：任何"只在罕见条件下执行"的分支，写的时候就要想"我怎么验证它"。

**守门** ⚠️ 无。这类问题只能靠结构上减少分支——所以有了 [ADR-0002](../adr/0002-collect-does-not-judge.md)
（采集层不判断）。

---

## GOTCHA-011 测试会写进真实历史库

**现象** 跑测试后 `~/.nastool/history.db` 里多出几条 `hostname=demo` 的记录。

**根因** `HistoryStore()` 默认路径是用户主目录，测试里直接 `HistoryStore()` 就落到真实位置。

**规避** 测试里**永远显式传 `--history-db` / `db_path` 到临时目录**。任何有默认落盘位置的
构造函数，在测试里都要覆盖它。

**守门** ✅ 测试统一传 `tmp_path` 下的 db 路径（见 `tests/test_smoke.py` 的历史往返用例）。

---

## GOTCHA-012 上报失败不影响退出码

**现象** webhook 地址写错，上报返回 ✗，但进程 `exit 0`，cron 认为一切正常。

**根因** 这是**有意设计**：报告生成本身成功了，上报是附加动作。但容易被误读为"上报成功"。

**规避** 依赖上报的场景必须检查输出里的 `✓`/`✗`，或者用 `--push` 之后另行确认后端收到了数据。
不要把退出码当作"上报成功"的信号。（是否要加 `--push-required` 仍在讨论，见
[open-questions.md](open-questions.md) Q-002。）

**守门** ⚠️ 无（行为设计如此，需要在 [CLI.md](../CLI.md) 里写清）。

---

## GOTCHA-013 `signal.SIGALRM` 在 Windows 上不存在

**现象** 在 Windows 上 `import signal` 后直接用 `signal.SIGALRM` 会 `AttributeError`。

**根因** `SIGALRM` 是 POSIX 专有。`signal` 模块在 Windows 上能导入，但缺这个属性。

**规避** 用 `hasattr(signal, "SIGALRM")` 守卫（`engine.py:55` 已这么做）。任何 POSIX 专有
能力（`SIGALRM`、`os.fork`、`termios`、`fcntl`）都要先判断存在性，并且**要有不用它的降级路径**，
不能只是跳过就算完。

**守门** ⚠️ 无（降级后行为正确，但没有测试覆盖 Windows 分支）。

---

## GOTCHA-014 版本号有三个地方，漏一处就对不上

**现象** `nastool --version` 显示 0.3.0，但 `pip show nastool` 是 0.3.1。

**根因** 版本号在 `VERSION`、`nastool/__init__.py`、`pyproject.toml` 三处独立维护。
`--version` 读的是 `__init__`，pip 元数据来自 `pyproject.toml`。

**规避** 三处同步改（[DEVELOPMENT.md](../DEVELOPMENT.md#8-发布) 有清单）。更好的是从
`VERSION` 单一读取，但打包时需要静态值，暂保持三处。

**守门** ✅ `selfcheck` 校验三处一致。
