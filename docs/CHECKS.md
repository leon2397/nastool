# 检测项参考手册

> 本文是 **55 个检测项的权威说明**：每项判什么、依据什么数据、在什么条件下给出 PASS / WARN / FAIL / UNKNOWN / SKIP。
>
> 权威性声明：本文与 `nastool/checks/*.py` 一一对应。若两者冲突，以代码为准，并请提 issue 修正本文。
> 查看当前构建实际注册了哪些项：`nastool --list-checks`。

---

## 0. 先理解五个状态

一个检测项的结果不是「对/错」两态，而是五态。这是理解本手册的前提。

| 状态 | 含义 | 计分 | 什么情况下出现 |
|---|---|:--:|---|
| **PASS** | 判定为正常 | 1.0 | 读到了数据，且在阈值内 |
| **WARN** | 有问题但可用 | 0.5 | 读到了数据，超出告警阈值 |
| **FAIL** | 严重问题 | 0.0 | 读到了数据，确认异常（或路径不可用等硬故障） |
| **UNKNOWN** | 无法判定 | **不扣分**，但计入盲区 | 读不到、权限不足、采集器异常 |
| **SKIP** | 不适用 | 不计入分母 | 平台不支持、依赖缺失、场景不检测、无可检对象 |

两条规则必须记住：

1. **UNKNOWN 不是失败。** 读不到 SMART 既不能算「硬盘要坏」，也不能算「硬盘没事」。它只降低覆盖度。详见 [ADR-0001](adr/0001-unknown-is-first-class.md)。
2. **SKIP 不计入覆盖度分母。** 在 Windows 上跑，31 项 Linux 专属检测标 SKIP，不影响覆盖率。

### 只有 15 项能产生 FAIL

55 项中其余 40 项**在设计上不可能给出 FAIL**——它们要么是信息项，要么最多告警。这个分布是有意的：**「严重」这个词必须稀缺，否则它就不严重了。**

| 分类 | 能 FAIL 的项 |
|---|---|
| 存储 | `path_exists` `writable` `capacity` `readonly_mount` `raid_state` `smart_health` `smart_bad_sectors` |
| 系统 | `memory_pressure` `thermal` |
| 网络 | `interface_present` `ip_assigned` |
| 服务 | `risky_ports` |
| 安全 | `ssh_root_login` `tls_cert` |
| AI | `hardware`（**仅在 `--profile ai` 下**） |
| 外设 | 无 |

这也决定了退出码：**只有这 15 项能让 `nastool` 返回 1。**

---

## 1. 存储（13 项）

NAS 的核心职能，权重最高（`nas` 场景 34 分）。设计上把「容量 / 权限 / 阵列 / 硬盘健康 / 性能」拆成独立项，这样历史对比能精确到某一项，而不是笼统的「存储变差了」。

### `storage.path_exists` — 数据路径存在

| 项 | 值 |
|---|---|
| 权重 | 5 |
| 平台 | 全部 |
| 依据 | `os.path.exists()` + `is_dir()` |

| 情况 | 结果 |
|---|---|
| 路径不存在 | **FAIL** —「挂载点掉了 / 网盘未挂载 / 路径写错」 |
| 路径存在但不是目录 | **FAIL** — `--storage-path` 指向了文件 |
| 可用 | PASS，置信度 1.0 |

这是最容易也最该先过的一关：NAS 重启后阵列未自动挂载，会让所有后续存储检测失去意义（它们会全部对着一个空目录做判断）。

### `storage.writable` — 数据路径可写

| 项 | 值 |
|---|---|
| 权重 | 5 |
| 平台 | 全部 |
| 依据 | **真实建文件写入探针**（不只看权限位） |

| 情况 | 结果 |
|---|---|
| 路径不可用（不存在/非目录） | SKIP |
| 写入失败 | **FAIL** —「权限不足、只读挂载，或文件系统已转为只读」 |
| 写入成功 | PASS，置信度 0.95 |

为什么不看权限位：`chmod` 正常但文件系统被内核转成只读（磁盘错误后的自我保护）时，权限位完全看不出问题，写入才会失败。这是 NAS 上真实且高频的故障形态。

### `storage.capacity` — 数据盘容量

| 项 | 值 |
|---|---|
| 权重 | 4 |
| 平台 | 全部 |
| 阈值 | `disk_use_warn` / `disk_use_crit`，随场景变化 |

| 场景 | 告警 | 严重 |
|---|---:|---:|
| `nas` | 80% | 90% |
| `verify` | 85% | 95% |
| `dev` | 90% | 95% |
| `ai` | 85% | 92% |

达到 `crit` → **FAIL**（写满会导致应用异常、快照失效）；达到 `warn` → WARN；否则 PASS。

证据带方向语义：`use_percent` 标 `up_bad`，`free_gb` 标 `up_good`，因此历史对比能正确判断「可用空间减少 = 恶化」。

### `storage.inode` — inode 使用率

| 项 | 值 |
|---|---|
| 权重 | 2 |
| 平台 | Linux |
| 阈值 | `inode_use_warn`（默认 90，各场景一致） |

取**所有挂载点中 inode 使用率最高者**判断，而不是只看数据盘——inode 耗尽的典型受害者是 `/var`（日志、缓存）。

| 情况 | 结果 |
|---|---|
| 无挂载信息 | UNKNOWN |
| 最高值为 0 | SKIP（btrfs / ZFS 等动态 inode 文件系统不报此值） |
| ≥ 90% | WARN —「空间可能还很充足」 |
| 否则 | PASS |

这类误判很常见：`df -h` 显示空间够，但一个文件都建不出来。

### `storage.readonly_mount` — 挂载只读

| 项 | 值 |
|---|---|
| 权重 | 4 |
| 平台 | Linux |
| 依据 | `/proc/mounts`，排除 `squashfs` / `iso9660` / `erofs` |

| 情况 | 结果 |
|---|---|
| 数据盘为只读 | **FAIL** —「内核检出错误后会自动转只读，这是数据受损的强信号」 |
| 其他文件系统只读 | WARN |
| 全部可写 | PASS |

### `storage.physical_disks` — 物理磁盘识别

| 项 | 值 |
|---|---|
| 权重 | 2 |
| 平台 | Linux |
| 依据 | `lsblk` |

信息项，**永远不会 FAIL**。识别不到时给 UNKNOWN，并区分原因：

- 运行在容器内 →「容器看不到宿主机块设备，SMART / 阵列检测均无法进行」，建议在宿主机上跑
- 其余 →「可能运行在虚拟机中，或 lsblk 不可用」

### `storage.raid_state` — 阵列健康

| 项 | 值 |
|---|---|
| 权重 | 5 |
| 平台 | Linux |
| 依据 | `/proc/mdstat`、`zpool status`、Btrfs 设备统计 |

| 情况 | 结果 |
|---|---|
| 无软阵列 | SKIP —「单盘使用、或使用硬件 RAID 卡（需厂商工具才能读取）」 |
| 任一成员缺失 / 状态异常 | **FAIL** — 列出每个异常阵列的级别与错误；建议「立即备份并更换故障盘；降级阵列在重建期间风险最高，避免再断电」 |
| 全部健康 | PASS，置信度 0.95 |

硬件 RAID 卡后面的阵列读不到是硬件限制，不是工具问题，因此是 SKIP 而不是 UNKNOWN。

### `storage.raid_rebuild` — 阵列重建

| 项 | 值 |
|---|---|
| 权重 | 3 |
| 平台 | Linux |
| 依据 | mdstat 的 `rebuilding` 状态 / `rebuild_percent > 0` |

重建中 → WARN（阵列处于降级状态，再坏一块就丢数据）；否则 PASS。

与 `raid_state` 分开的原因：重建中的阵列「状态正常但脆弱」，这是两种不同的风险，合并会丢失信息。

### `storage.smart_health` — 硬盘 SMART 健康

| 项 | 值 |
|---|---|
| 权重 | **6（全项最高）** |
| 平台 | Linux |
| 依赖 | `smart_data`（需要 `smartctl` 且能读到盘） |

任一盘的 SMART 总判定为 `FAILED` → **FAIL**（建议立即备份并准备更换）。

依赖不满足时引擎直接标 SKIP 并写明「缺少依赖：smart_data，本次未检测」——**绝不写「SMART 正常」**。

### `storage.smart_bad_sectors` — 坏道计数

| 项 | 值 |
|---|---|
| 权重 | 5 |
| 平台 | Linux |
| 依赖 | `smart_data` |
| 依据 | `Reallocated_Sector_Ct`、`Current_Pending_Sector` |

| 情况 | 结果 |
|---|---|
| 有待定扇区（pending > 0） | **FAIL** —「已经出现读不出来的扇区，是最直接的硬盘失效前兆」 |
| 有重映射扇区（reallocated > 0） | WARN —「已有坏道被备用扇区替换，短期内可用，但数量持续增长说明盘在老化」 |
| 均为 0 | PASS |

两个计数都标了 `up_bad`。这是历史对比最该盯的指标：**总分不动、状态不变，但重映射扇区 0 → 12**，只有逐项证据 diff 能发现。

### `storage.smart_age` — 硬盘通电时长

| 项 | 值 |
|---|---|
| 权重 | 2 |
| 平台 | Linux |
| 依赖 | `smart_data` |

| 情况 | 结果 |
|---|---|
| 无数据 | UNKNOWN |
| ≥ 8 年 | WARN —「机械盘设计寿命通常 5-8 年，二手验机时这是重要议价点」 |
| ≥ 5 年 | WARN —「进入老化期，建议提高备份频率」 |
| 否则 | PASS |

两档都是 WARN，区别在提示措辞（议价 / 保养），不影响分数。

### `storage.smart_temperature` — 硬盘温度

| 项 | 值 |
|---|---|
| 权重 | 2 |
| 平台 | Linux |
| 依赖 | `smart_data` |

取最热的盘：≥ 60°C → WARN（过高）；≥ 50°C → WARN（关注散热）；否则 PASS。

注意这里的阈值是**硬编码在检查项里**的，与 `system.thermal` 的芯片自适应阈值是两套——硬盘工作温度区间与 SoC 完全不同，不能共用。

### `storage.speed` — 读写速度

| 项 | 值 |
|---|---|
| 权重 | 2 |
| 平台 | 全部 |
| 依据 | 50MB 顺序读写实测（含 `fsync`） |

| 情况 | 结果 |
|---|---|
| 未执行（`--no-speed-test` 或路径不可写） | SKIP |
| 读写均为 0 | UNKNOWN |
| 最优值 < 10 MB/s | WARN —「读写异常低」 |
| 最优值 < 50 MB/s | WARN —「读写偏慢，排除是否走了 USB 2.0 或链路降速」 |
| 否则 | PASS |

取 `max(读, 写)` 判断，因为缓存会让其中一项虚高——只要有一项达到水平，就不是「盘不行」。

---

## 2. 系统与硬件（10 项）

判定逻辑统一为三档：读到了且正常 → PASS；读到了但异常 → WARN/FAIL；**读不到 → UNKNOWN（不扣分）**。

### `system.cpu_visible` / `system.memory_readable`

各权重 1，信息项。读不到核心数/内存容量 → UNKNOWN（附 `collect_errors` 里的具体原因）。读到 → PASS，置信度 0.95。

这两项存在的意义不是打分，而是**建立可信度基线**：如果 CPU 都读不到，整份报告的解释力就该被质疑。

### `system.memory_pressure` — 内存压力

| 项 | 值 |
|---|---|
| 权重 | 3 |
| 阈值 | `mem_use_warn` / `mem_use_crit` |

| 场景 | 告警 | 严重 |
|---|---:|---:|
| `nas` | 85% | 95% |
| `verify` / `dev` | 90% | 97% |
| `ai` | 85% | 95% |

≥ crit → **FAIL**（接近耗尽）；≥ warn → WARN；否则 PASS。

`nas` 场景的告警提示里特意提到 ZFS ARC：ZFS 会主动占用大量内存，这通常是正常的，调 `arc_max` 即可，不是内存不够。

### `system.swap_pressure` — 交换分区压力

权重 1，Linux。未启用 swap → SKIP（「NAS 上不启用 swap 是常见做法，不影响使用」）；使用率 ≥ `swap_use_warn`（50%）→ WARN；否则 PASS。

### `system.thermal` — 温度

| 项 | 值 |
|---|---|
| 权重 | 3 |
| 平台 | Linux |
| 依据 | `/sys/class/thermal`（取最热传感器） |
| 阈值 | **按芯片自适应**，见下表 |

| 芯片 | 告警 | 严重 |
|---|---:|---:|
| RK3588 / RK3568 / RK3566 | 70°C | 82°C |
| Raspberry Pi (bcm2711/2712) | 70°C | 82°C |
| Jetson / Orin | 75°C | 88°C |
| 昇腾 Ascend | 78°C | 90°C |
| 其他（按场景默认） | `temp_warn` | `temp_crit` |

场景默认值：`nas` 75/88、`verify` 80/92、`dev` 85/95、`ai` 75/85。

芯片识别顺序：先看 AI 加速器探测结果，再在平台型号 / 主板型号 / CPU 型号中匹配关键字。命中非 generic 芯片时，summary 会附注「阈值按 rk3588 校准：70/82°C」，让用户知道用的哪套标准。

≥ crit → **FAIL**；≥ warn → WARN；无传感器 → UNKNOWN（「容器 / 虚拟机 / 部分 ARM 设备不暴露温度接口」）。

### `system.load_average` — 负载

权重 2，Linux / macOS。按 `load1 / 核心数` 判断，阈值 `load_per_core_warn`（1.5）：

- ≥ 1.5 × 2 = 3.0 → WARN「明显偏高」
- ≥ 1.5 → WARN
- 否则 PASS

除以核心数是关键：8 核机器的 load 8 与 2 核机器的 load 8 是两回事。

### `system.uptime` — 运行时长

权重 1。**< 0.5 小时 → WARN**：「如果这台机器不是刚刚部署的，可能发生了意外重启或断电恢复」。

这是验机时的关键信号：卖家说「一直稳定运行」，但 uptime 只有 20 分钟。

### `system.clock_sync` — 时间同步

| 项 | 值 |
|---|---|
| 权重 | 2 |
| 平台 | Linux / Windows |

**Windows**：读 `w32tm /query /source`。来源为本地 CMOS / free-running → WARN；有外部 NTP 源 → PASS。

**Linux**：
1. 优先 `timedatectl show -p NTPSynchronized --value`
2. 退回读 `/etc/ntp.conf`、`/etc/chrony.conf`、`/etc/chrony/chrony.conf`：找到 `server` / `pool` 行即视为「已配置」
3. 两条路都失败 → UNKNOWN

「已配置」与「已生效」是两件事，因此配置文件路径的置信度只有 0.85，且 summary 不会声称「已同步」。

时间不同步的实际影响：TLS 证书校验失败、Kerberos/域认证失败、备份时间戳错乱。

### `system.io_pressure` — 磁盘 I/O 压力

权重 2，Linux。依据 `/proc/pressure/io`（PSI，需 Linux 4.20+）：

- `full avg10 ≥ 30%` → WARN「磁盘 I/O 已饱和」
- `some avg10 ≥ 50%` → WARN「压力偏高」
- 不支持 PSI → SKIP（老内核可忽略）

### `system.process_count` — 进程数量

权重 1，Linux。≥ 2000 → WARN（检查是否有进程反复重启或 fork 炸弹）；否则 PASS。

---

## 3. 网络（10 项）

判定口径按 **NAS 常识**，而不是按「能不能上网」——隔离内网完全正常，不该扣分。

### `network.interface_present` — 网络接口

权重 3。无任何接口 → **FAIL**（驱动缺失 / 容器无网络命名空间 / `ip` 不可用）；全部 DOWN → **FAIL**；否则 PASS。

### `network.ip_assigned` — IP 地址

| 项 | 值 |
|---|---|
| 权重 | 5 |

| 情况 | 结果 |
|---|---|
| 有可用 IP（非 169.254.x.x） | PASS |
| 只有链路本地地址 | WARN —「DHCP 没成功，实际无法与局域网其他设备通信」 |
| 完全没有 IP | **FAIL** |

169.254 单独判定很重要：`ip addr` 会显示有地址，新手容易误以为网络正常。

### `network.link_speed` — 链路速率

权重 3，Linux。只看**已启用的有线网卡**，取最低速率：

| 速率 | 结果 |
|---|---|
| < 100 Mbps | WARN —「网线只通了 4 芯、水晶头氧化、或走了 USB 网卡」 |
| 100–999 Mbps | WARN —「非千兆」 |
| ≥ 1000 Mbps | PASS（≥ 2500 标注 2.5G+） |

没有有线网卡 → SKIP；`/sys/class/net/*/speed` 读不到 → UNKNOWN（虚拟网卡常见）。

百兆是 NAS 的真实瓶颈：机械盘顺序读写 150+ MB/s，百兆网络只能跑 12 MB/s。

### `network.duplex` — 双工模式

权重 2，Linux。半双工 → WARN（协商失败的结果，会大量冲突与丢包）；全部无数据 → UNKNOWN。

### `network.gateway` — 默认网关

权重 2。**未配置网关 → SKIP**（「隔离内网 / 纯二层存储网络属于正常配置」）；网关不可达 → WARN；可达 → PASS。

### `network.dns` — DNS 解析

权重 2。**这里有一个刻意的判罚豁免**：

| 情况 | 结果 |
|---|---|
| 无网关且无 DNS 配置 | SKIP（隔离内网） |
| 解析成功 | PASS |
| 解析失败，**且网关本身不可达** | **UNKNOWN** —「先解决网关问题才能判断 DNS，因此本次不算 DNS 故障」 |
| 解析失败，网关照常可达 | WARN |

第三条是关键：网关都ping不通时把 DNS 判 WARN，等于把同一个故障数两遍。

### `network.internet` — 外网连通

权重 1。`--no-internet` → SKIP；**网关不可达 → UNKNOWN**（不联外网的 NAS 是合理配置）；外网不可达 → WARN（提示「若无需远程访问/更新套件可忽略」）。

### `network.peer_reach` — 对端可达性

权重 2。未指定 `--peer` → SKIP；任一目标不可达 → WARN（列出每个目标的错误）；全部可达 → PASS，置信度 0.95。

用途：顺手验证备份服务器、客户端、管理后台是否可达。证据里带 RTT（毫秒）。

### `network.wireless_primary` — 主链路类型

权重 3。有可用有线链路 → PASS；只有无线可用 → WARN —「NAS 走 WiFi 会出现带宽不稳、延迟抖动、断流，尤其在多客户端并发时」。

对 NAS 这是真实隐患，所以给了 3 分权重。

### `network.interface_errors` — 网卡错误计数

权重 2，Linux。读 `/sys/class/net/*/statistics/` 的 `rx_errors` / `tx_errors` / `rx_dropped`。

- `rx_errors + tx_errors > 0` → WARN（累计值，标 `up_bad`）
- 全为 0 → PASS

**注意这是累计计数器**，不是速率。开机很久的机器有几个错误很常见，真正的信号是「这个数字在涨」——所以标了 `up_bad`，靠历史对比看趋势。

---

## 4. 服务与端口（8 项）

核心原则：**服务缺失不算故障。** 一台只跑 SMB 的裸 NAS 完全正常，不能因为没装 Plex 就扣分。

只有两类情况真正扣分：高风险服务对外暴露、敏感端口绑定在所有地址上。

### `services.port_inventory` — 端口清单

权重 1，信息项。读不到监听端口 → UNKNOWN（`ss` / `netstat` 不可用）；否则 PASS，附带「共 N 个监听端口，识别出 M 个已知服务」，并单独统计 49152+ 的临时端口。

### `services.file_sharing` — 文件共享服务

权重 3。

| 情况 | 结果 |
|---|---|
| 检测到 SMB / NFS / FTP / SFTP 等 | PASS |
| 端口列表不可用 | UNKNOWN（不能因为没看到就说不存在） |
| 端口列表可用但没有共享服务 | WARN —「NAS 的核心职能是文件共享」 |

### `services.risky_ports` — 高风险服务

| 项 | 值 |
|---|---|
| 权重 | 4 |
| 明确定义的高风险端口 | 见下 |

| 端口 | 服务 | 判定 |
|---|---|---|
| 2375 | Docker API（未加密） | **FAIL** —「可直接创建特权容器，等同于交出 root」 |
| 23 | Telnet | WARN —「明文传输，凭据可被直接抓包」 |
| 21 | FTP | WARN —「明文传输；建议改用 SFTP」 |

2375 是唯一的服务类 FAIL：无认证的 Docker API 等于把整机交给任何能访问该端口的人。

### `services.exposed_bind` — 端口暴露范围

权重 3。以下端口若绑定在 `0.0.0.0` / `*` / `::` / 空 → WARN：

`445` SMB、`2049` NFS、`3306` MySQL、`6379` Redis、`5432` PostgreSQL、`27017` MongoDB

判罚措辞刻意克制：「这些服务本身有认证，但对外暴露会放大暴力破解与漏洞利用面」。绑在内网地址上则是 PASS。

### `services.docker` — 容器运行时

权重 2。未检测到 Docker（未安装 / 未启动 / 无权限）→ SKIP；有 → PASS 并统计运行中/已停止容器数。信息项。

### `services.web_ui` / `services.media_stack` — 管理界面 / 媒体服务

各权重 1。**没有则 SKIP**（「纯文件存储用途无需此项」），有则 PASS 并列出端口。纯信息项。

### `services.unknown_services` — 未识别端口

权重 1。未识别端口 ≥ 10 个 → WARN（「可能是自建服务、恶意程序，或端口映射残留」）；少于 10 个 → PASS（置信度 0.8，因为少量未识别端口多是自建服务）。

---

## 5. 安全（8 项）

**全部只读**，不修改任何配置。

判定刻意不搞一刀切：

- `PermitRootLogin prohibit-password` 是现代发行版默认值，**不算问题**
- 只有明确 `yes` 才算严重
- 自签名证书在纯内网属于合理选择，只告警不建议强制更换

依赖项（`ssh_config` / `certs` / `smb_config` / `nfs_config`）不满足时标 SKIP，不会凭空猜结论。

### `security.ssh_root_login` — SSH 允许 root 登录

| 项 | 值 |
|---|---|
| 权重 | 4 |
| 依据 | `sshd_config`（含 `/etc/ssh/sshd_config.d/*`，多行取最后生效值，遇 `Match` 停止） |

| 配置值 | 结果 |
|---|---|
| `yes` / `true` | **FAIL** —「root 账户名是公开已知的，允许直接登录等于把暴力破解的目标减半」 |
| `prohibit-password` / `without-password` / `forced-commands-only` | PASS |
| `no` | PASS |
| 未显式声明 | UNKNOWN —「不同发行版默认值不同」 |

### `security.ssh_password_auth` — SSH 密码登录

| 项 | 值 |
|---|---|
| 权重 | 3 |

`no` / `false` → PASS（仅密钥）；`yes` / `true` → WARN；未声明 → UNKNOWN。

### `security.firewall` — 防火墙

| 项 | 值 |
|---|---|
| 权重 | 4 |
| 依据 | ufw / firewalld / nftables / iptables / Windows 防火墙 |

| 情况 | 结果 |
|---|---|
| 检测到且已启用 | PASS（附规则数） |
| 检测到但未启用 | WARN |
| 完全没检测到 | WARN —「至少启用 ufw / firewalld 并放行必要端口；路由器侧做 NAT 也能缓解」 |
| 无法判定 | UNKNOWN |

### `security.tls_cert` — 证书有效期

| 项 | 值 |
|---|---|
| 权重 | 4 |
| 依据 | `openssl x509` 解析证书的 `notAfter` |

| 剩余天数 | 结果 |
|---|---|
| < 0（已过期） | **FAIL** —「已过期 N 天」 |
| ≤ 7 天 | **FAIL** —「立即续签，避免服务中断」 |
| ≤ 30 天 | WARN |
| > 30 天 | PASS |

前身项目在这个检查上有过「剩余天数显示 -1148 天」的 BUG。本项目对已过期证书单独走 FAIL 分支并显示正的「已过期 N 天」，不会出现负数天数。

### `security.self_signed` — 证书类型

权重 2。发现自签名证书 → WARN（「内网使用自签名是常见做法，但会导致客户端告警、部分 API 拒绝连接」）；无证书 → SKIP；全部受信任机构签发 → PASS。

### `security.smb_guest` — SMB 匿名访问

权重 3，Linux，依赖 `smb_config`。`guest ok = yes` → WARN（「任何人都能读取共享目录，勒索软件也会优先利用这类共享」）；否则 PASS。

### `security.nfs_root_squash` — NFS 权限映射

权重 3，Linux，依赖 `nfs_config`。`/etc/exports` 中出现 `no_root_squash` → WARN（「客户端 root 会保留为服务端 root，等于把整机控制权交给能挂载该目录的主机」）。

### `security.fail2ban` — 暴力破解防护

权重 1，Linux。未安装 → SKIP（「可用 systemd / 容器方案替代，不算缺陷」）；已安装但未运行 → WARN；运行中 → PASS。

---

## 6. AI 算力（4 项）

定位克制：**AI 不是合格线。**

- 纯存储 NAS 没有加速器完全正常 → SKIP，不是 FAIL
- 只有 `--profile ai` 时，缺加速器才算 FAIL
- 「有硬件但推理引擎不可用」才是真正需要处理的 WARN

### `ai.hardware` — AI 加速硬件

| 项 | 值 |
|---|---|
| 权重 | 3 |
| 识别范围 | NVIDIA / AMD ROCm / Rockchip / 昇腾 / Intel / 算能 / Coral / CPU 兜底 |

| 情况 | 结果 |
|---|---|
| 有加速硬件 | PASS |
| 无硬件，且 `profile=ai` | **FAIL** —「当前使用 ai 场景，预期这台机器应具备 NPU / GPU 加速能力」 |
| 无硬件，其他场景 | SKIP（不计入评分） |

### `ai.runtime` — 推理运行时

权重 2。无加速硬件 → SKIP；`--no-ai` → SKIP；**有硬件但没有可用推理引擎 → WARN**（常见原因：PyTorch/ONNX Runtime 未装、装的是 CPU 版、CUDA/ROCm 版本不匹配）。

这是 AI 场景下最有价值的一项：硬件在，但跑不起来，才是真实痛点。

### `ai.inference_perf` — 推理性能

权重 2。无推理耗时数据 → SKIP；单次 ≥ 5000 ms → WARN（「可能是驱动回退到 CPU 执行，或模型过大」）；否则 PASS。

### `ai.vendor_env` — 厂商运行环境

权重 1，Linux。检测 `/etc/nv_tegra_release`（Jetson）、`/proc/device-tree/model`（Rockchip）、`/usr/local/Ascend/version.info`（昇腾）。未检测到 → SKIP（「通用 x86 / ARM 平台无需此项」）。

---

## 7. 外设（2 项）

只做两件真正有价值的事：清点 USB 设备（验机时能看出有没有偷偷插挖矿/加密狗/无线网卡）、判断数据盘是不是挂在 USB 上（真实且常见的稳定性隐患）。

### `usb.devices` — USB 设备

权重 1，Linux。无 USB 子系统 → SKIP（虚拟机/容器/ARM 板卡常见）；有设备 → PASS 并列出（排除 root hub 与接口节点）；无设备 → PASS。

信息项，但验机时有用。

### `usb.storage_media` — 数据盘连接方式

| 项 | 值 |
|---|---|
| 权重 | **4（外设类主力）** |
| 依据 | `/sys/block/<dev>/removable` |

| 情况 | 结果 |
|---|---|
| 数据盘在可移动总线（USB/SD） | WARN —「USB 桥接的硬盘会因供电不稳、休眠、线缆接触不良而掉盘，RAID 场景下掉盘会直接触发降级」 |
| 内置接口连接 | PASS |
| 无法确定块设备（网络挂载 / 容器卷） | SKIP |

给了 4 分权重，因为这是外设类里唯一有实质风险的项——很多人把小主机 + USB 硬盘盒当 NAS 用，然后不解为什么阵列老是掉。

---

## 附：如何验证本文与代码一致

```bash
# 1. 检查项总数与分类分布
nastool --list-checks

# 2. 实际跑一遍，看每项的真实结果与证据
nastool -v --no-speed-test

# 3. 只跑某一类，对照本文对应章节
nastool --only storage.* -v
```

如果文档与 `--list-checks` 的数量或 ID 不一致，说明文档过期了——请以代码为准并提 issue。
