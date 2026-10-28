# 故障排查

> 按「你看到的现象」组织。每条都给出原因与验证命令。
>
> 相关：[CHECKS.md](CHECKS.md)（每项的判定条件）、[SCORING.md](SCORING.md)（为什么是这个分）

---

## 1. 大部分检测项显示「不适用」

### 现象

```
覆盖  20/20 项已判定（100.0%），31 项不适用
⚠ 本平台有 31 项检测不适用（多为 Linux 专属…）
```

### 原因

这是**正常现象**，不是故障。55 项里有约 31 项是 Linux 专属（SMART、mdstat、`/proc`、`/sys/class/thermal`、inode、USB 子系统…）。在 Windows / macOS / 容器里它们本来就不适用。

`不适用`（SKIP）与`不可判定`（UNKNOWN）是完全不同的两件事：

| | 含义 | 是否降低覆盖度 |
|---|---|---|
| 不适用 | 这台机器没有这个概念，不该查 | 否 |
| 不可判定 | 该查但没查到 | **是** |

### 怎么确认不是真问题

```bash
nastool --list-checks        # 看每项标注的平台
```

被标 `平台: linux` 的项在 Windows 上必然是 SKIP。

### 想看完整能力

在 Linux 主机上直接跑（不要在容器里）。见下面第 6 条。

---

## 2. 某项显示「不可判定」，不知道怎么办

### 现象

```
? 硬盘 SMART 健康    缺少依赖：smart_data，本次未检测
```

### 原因与对策

`checks[].summary` 会直接写明原因。常见几种：

| 提示 | 原因 | 解决 |
|---|---|---|
| `缺少依赖：smart_data` | 没有 `smartctl`，或没有 root，或盘在硬件 RAID 卡后面 | 装 `smartmontools`；用 root 跑；硬件 RAID 需厂商工具 |
| `缺少依赖：ssh_config` | 找不到 `/etc/ssh/sshd_config` | 容器/精简系统常见，忽略即可 |
| `未读取到温度传感器` | 容器、虚拟机、部分 ARM 板卡不暴露 `/sys/class/thermal` | 在宿主机上跑 |
| `无法读取链路速率` | `/sys/class/net/*/speed` 不可读（虚拟网卡） | 正常现象 |
| `检查执行失败，本次无法判定` + `检查器异常` 行 | **检查代码自己崩了** | 看 `error` 字段，提 issue |
| `无法判定时间同步状态` | 既没有 `timedatectl`，也没有 NTP 配置文件 | 装 systemd-timesyncd 或 chrony |

### 关键区分

```
? 硬盘 SMART 健康    缺少依赖：smart_data        ← 没测成，设备未必有问题
✗ 硬盘 SMART 健康    1 块硬盘 SMART 未通过       ← 测了，确实有问题
```

第一种看 `status=unknown`、`error=""`；第二种看 `status=fail`。**UNKNOWN 不扣分**，它只让你知道「这里没查清」。

### 为什么 UNKNOWN 会拉低等级

盲区太大时报告会主动降级：

| 盲区 | 封顶 |
|---|---|
| ≥ 50% | 74（C 级） |
| ≥ 30% | 84（B 级） |

如果你觉得不该降，说明该补依赖（装 `smartctl`、用 root 跑），而不是改判定。

---

## 3. 分数 59 分 D 级，但我看不出哪里坏了

### 原因

触发了「存在严重问题封顶 59」。报告里会有一行明确说明：

```
! 存在 1 项严重问题，总分封顶 59
```

### 怎么找出那一项

```bash
nastool -v | grep "✗"          # 直接看严重项
nastool -o json -q && \
  python -c "
import json
for c in json.load(open('nastool_report.json'))['checks']:
    if c['status']=='fail': print(c['id'], c['title'], '|', c['summary'])"
```

JSON 里 `checks[]` 已按「分类 → 严重度」排序，`fail` 排在最前面。

---

## 4. 等级是 C，但所有项都通过了

### 现象

```
结论  74 分 · C 级 · 存在明显问题，建议尽快处理
覆盖  8/19 项已判定（42.1%），11 项不可判定
! 57.9% 的适用项不可判定（盲区过大），等级封顶 C
```

### 原因

不是「有问题」，是「**没查清**」。11 项 UNKNOWN 把总分从 100 压到 74。

### 对策

先解决 UNKNOWN（见第 2 条），而不是纠结分数。补上依赖后重跑，等级自然会回来。

如果这台机器确实拿不到那些数据（例如容器里跑），那 C 级就是诚实结论——**它表达的是「这份报告的解释力有限」，不是「设备有问题」**。

---

## 5. SMART 读不到（最常见）

### 症状

`storage.smart_*` 四项全部 SKIP 或 UNKNOWN。

### 逐项排查

```bash
# 1) smartctl 装了吗
which smartctl || echo "没装：apt install smartmontools"

# 2) 用 root 能读吗（非 root 通常读不到）
sudo smartctl -H /dev/sda

# 3) 盘在硬件 RAID 卡后面吗
lsblk -o NAME,TYPE,MODEL
# 只看到 /dev/sda 而看不到 /dev/sdb /dev/sdc → 多半是硬件 RAID 或 HBA
```

| 情况 | 能否读到 SMART |
|---|---|
| 普通 SATA / NVMe 直连，root | 能 |
| 非 root | 通常不能 |
| 硬件 RAID 卡（MegaRAID 等） | **不能**，需 `storcli` / `perccli` 等厂商工具 |
| USB 桥接硬盘盒 | 多数不能（桥接芯片不透传 SMART） |
| 虚拟机 | 通常不能 |
| 容器 | 不能（看不到宿主机块设备） |

**这是硬件限制，不是工具问题。** 报告标 SKIP 而不是 FAIL 正是因为这个原因。

---

## 6. 在容器里跑，检测项很少

### 现象

```
⚠ 运行在 docker 容器内：SMART / RAID / 温度等项目可能不可见，建议在宿主机上复检
```

### 原因

容器看不到宿主机的块设备与传感器：

- `/dev/sd*` 通常未挂载进容器
- `/sys/class/thermal` 是容器自己的
- `/proc/mdstat` 是宿主机的，但需要 `--privileged` 或挂载

### 对策

**在被检测的那台机器上直接跑，不要在容器里跑。**

如果只能用容器，至少加：

```bash
docker run --rm --privileged --pid=host \
  -v /sys:/sys:ro -v /dev:/dev:ro -v /proc:/proc:ro \
  -v /volume1:/volume1 \
  python:3-slim python -m nastool
```

即便如此，SMART 与温度也大概率读不到。这时报告会明确告诉你哪些项没查到——这是它该做的。

---

## 7. Windows 上中文乱码

### 症状

命令输出里的中文变成 `����`。

### 原因与现状

`collect/util.py` 的 `run()` 已实现三级解码回退：

```
UTF-8（严格） → mbcs（中文 Windows 的 CP936） → locale.getpreferredencoding()
```

这个顺序是刻意的：先试 UTF-8（Linux 与 `wsl` 输出），失败再退到中文 Windows 的本地编码。

### 如果仍然乱码

说明遇到了三级都解不对的输出（少见）。排查：

```python
from nastool.collect.util import run
print(repr(run("wmic os get Caption")))
```

把输出贴到 issue 里。**不要自己加 `decode("gbk")`** ——那会在 UTF-8 环境里制造新的乱码。

PowerShell 调用已改为**参数列表**（不是拼字符串），避免引号被 shell 吃掉。

### 另一种情况：整个程序起不来，stdout 一片空白

**症状**：在**英文** Windows（系统 locale 不是中文）上运行，命令没有任何输出，
直接退出。退出码 1。

**原因**：Windows 标准输出的默认编码由**系统 locale** 决定——英文系统是 cp1252，
它编不了本工具输出的中文。`print` 抛 `UnicodeEncodeError`，进程当场崩掉。

**为什么本地复现不了**：中文 Windows 的 locale 是 cp936，恰好能编中文，
所以在中文机器上永远看不到这个现象。**只有英文 Windows 才会中招**——
包括 CI 的 Windows runner。

**现状**：已在 `cli.py` 的 `main()` 入口把 stdout/stderr 切到 UTF-8
（`reconfigure(encoding="utf-8", errors="replace")`），并有回归测试
`test_survives_non_utf8_console_encoding` 盯着。

验证方法：

```bash
PYTHONIOENCODING=cp1252 python -m nastool --list-checks
```

---

## 8. 自动挑选的存储路径不对

### 现象

报告里的「数据盘」是 `C:\` 或 `/`，而不是你的数据盘。

### 挑选规则

Linux 按顺序找第一个**可写**的：

```
/volume1 → /volume2 → /share/CACHEDEV1_DATA → /mnt → /media → /data → /srv
→ /mnt/user → /tank → /mnt/tank → /vol1 → /vol2
```

都不存在时选可用空间最大的可写挂载点。Windows 选 D–Z 中可用空间最大的盘。

### 对策

显式指定：

```bash
nastool --storage-path /volume2/media
nastool --storage-path "D:\data"
```

注意必须指向**目录**，指向文件会得到 `storage.path_exists` FAIL。

---

## 9. 速度测试很慢或结果异常

### 现象

- 跑了几十秒还没完
- 写 12 MB/s、读 480 MB/s（差异巨大）

### 原因

测速会**真实写入 50MB 临时文件**并 `fsync`，机械盘上确实需要数十秒。

读写差异大是正常的：读走缓存，写要落盘。判定用的是 `max(读, 写)`，所以不会因为写慢就误判。

### 对策

```bash
nastool --no-speed-test      # 不想等就跳过（该项标 SKIP）
```

如果在 USB 2.0 硬盘盒上跑，写 30 MB/s 以下很常见——那说明链路有问题，不是工具算错。见 `usb.storage_media`。

---

## 10. `--compare` 说「没有实质变化」，但我感觉变了

### 可能原因

| 原因 | 怎么确认 |
|---|---|
| 有变化的是**中性指标**（温度、负载、通电时长） | 中性指标只记为「指标变化」不算恶化，这是有意的。看 `evidence_changed` 分组 |
| 变化的项<b>没有 `num` 或 `trend`</b> | 该证据不参与数值比较。看 JSON 里对应 evidence 是否有 `num` |
| 对比的是**上一次**而不是你以为的那次 | 用 `--compare <ID>` 显式指定，先 `--history` 查到 ID |
| 两次之间没有真正执行该项 | 检查是否加了 `--skip` 或依赖缺失导致 SKIP |
| 设备指纹不同，被警告过 | 输出开头有 `⚠ 历史记录的设备指纹与本次不同` |

### 想看全部变化（含中性）

终端只显示「有实质变化」的项。完整清单：

```python
from nastool.history import HistoryStore
from nastool.diff import diff_reports

store = HistoryStore()
new = store.load()                      # 最近一次
old = store.load(run_id=new_id - 1)     # 或指定 ID
for ch in diff_reports(old, new).changes:   # .changes 含全部，.significant 才有过滤
    print(ch.kind, ch.check_id, ch.note)
```

---

## 11. 历史库打不开

### 症状

```
错误：无法打开历史库：[Errno 13] Permission denied: '/root/.nastool'
```

### 原因与对策

| 原因 | 对策 |
|---|---|
| 以 `sudo` 跑，库被建在 `/root/.nastool` | 用 `--history-db` 指定普通用户可写的路径 |
| 多个用户/NAS 账户各跑各的，看不到彼此历史 | 显式指定同一个 `--history-db` |
| 通过 API 传了 `~/xxx.db` | `~` 不会展开，请写绝对路径 |
| 库文件损坏 | 备份后删掉重建（历史会丢） |

```bash
nastool --history-db /var/lib/nastool/history.db --save-history
```

---

## 12. 退出码是 1，但终端看起来很平静

### 原因

退出码只看 **FAIL**，而终端默认只列非 PASS/SKIP 的项——FAIL 一定在里面，但可能被 `-q` 吞了横幅或翻页滚走了。

```bash
nastool -q; echo "exit=$?"
```

### 找出是哪项

```bash
nastool -v | grep -A3 "✗"
```

### 反过来：等级很差但退出码是 0

这也是正常的设计：

| 情况 | 等级 | 退出码 |
|---|---|---|
| 1 项 SMART 失败 | D | **1** |
| 盲区 60% 导致封顶 | C | **0** |

盲区大表示「没查清楚」，不等于「确认有故障」，不该让 cron 半夜报警。要用等级做门禁请消费 JSON，见 [CLI.md](CLI.md#2-退出码)。

---

## 13. HTML 报告打不开 / 没样式

### 原因

HTML 是**单文件、零外部资源**（不引用 CDN、不引用字体、不引用图片）。样式全部内联。

如果打开后确实没样式，可能文件被截断了：

```bash
ls -l nastool_report.html      # 正常约 30–40 KB
tail -3 nastool_report.html    # 应该以 </html> 结尾
```

### 打印

已加 `@media print` 规则：隐藏交互元素、避免分页割裂条目。直接 Ctrl+P 即可。

---

## 14. 某个检查项每次都崩（`检查器异常`）

### 症状

```
? 某某检查    检查执行失败，本次无法判定
     检查器异常：KeyError: 'model'
```

### 原因

这是**工具的 bug**，不是设备问题。`status=unknown` + `error` 非空就是这个含义。

### 收集信息提 issue

```bash
nastool -v -o json -q
python -c "
import json
for c in json.load(open('nastool_report.json'))['checks']:
    if c['error']: print(c['id'], '=>', c['error'])"
```

附上这些内容：

1. `nastool --version`
2. `meta.platform_summary` 与 `platform.kind`
3. 该条的 `error` 文本
4. `platform` 与 `facts` 里对应的子结构（**脱敏后再贴**：主机名、IP、序列号）

---

## 15. 还是不确定，怎么自查

按这个顺序，基本能定位：

```bash
# 1) 版本与平台
nastool --version
uname -a          # 或 Windows: systeminfo | findstr /C:"OS 名称"

# 2) 注册了哪些项
nastool --list-checks | head -40

# 3) 只跑一类，看仔细
nastool --only storage.* -v --no-speed-test

# 4) 看结构化结果里到底发生了什么
nastool -q -o json
python -c "
import json; d=json.load(open('nastool_report.json'))
print('options:', d['meta']['options'])
print('coverage:', d['coverage'])
print('collect_errors:', d.get('collect_errors', []))"

# 5) 采集层是否报错
#    collect_errors 非空说明某个采集器整体失败了
```

`meta.options` 能告诉你「这次到底在什么条件下跑的」——很多困惑源于实际生效的参数和你以为的不一样（例如 `--no-smart` 让 SMART 全 SKIP）。
