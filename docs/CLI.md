# 命令行参考

> 全部参数的权威说明。快速上手看 [README](../README.md)，参数背后的规则看对应专题。
>
> `nastool --help` 的输出永远与本文一致；两者冲突以 `--help` 为准。

---

## 1. 全部参数

### 检测范围

| 参数 | 默认 | 说明 |
|---|---|---|
| `--storage-path PATH` | 自动挑选 | 要体检的数据路径。不指定时：Linux 先按 `/volume1` `/volume2` `/share/CACHEDEV1_DATA` `/mnt/user` `/tank` `/vol1` 等常见 NAS 挂载点顺序找**可写**的；都不存在则选可用空间最大的可写挂载点；Windows 选 D–Z 中可用空间最大的盘；最后回退到用户目录 / 当前目录 |
| `--peer HOST:PORT` | 无 | 对端 TCP 可达性检查。可重复，也可用逗号分隔：`--peer a:445,b:22` |
| `-p, --profile {nas,verify,dev,ai}` | `nas` | 检测场景，决定**权重、阈值、检测范围**。见 [PROFILES.md](PROFILES.md) |
| `--only PATTERN` | 无 | 只跑匹配的检查项，支持通配：`storage.*`、`*.smart_*`。可重复。**会绕过场景的分类过滤** |
| `--skip PATTERN` | 无 | 跳过匹配的检查项。可重复 |
| `--enable {分类}` | 无 | 在当前场景上追加分类。追加的分类若原权重为 0，拿保底权重 **8** |
| `--no-speed-test` | 关 | 跳过 50MB 读写测速（机械盘上可省数十秒） |
| `--no-smart` | 关 | 跳过 SMART 读取 |
| `--no-ai` | 关 | 跳过 AI 算力探测与推理测试 |
| `--no-internet` | 关 | 跳过外网连通性检查 |

### 报告输出

| 参数 | 默认 | 说明 |
|---|---|---|
| `-o, --output {terminal,json,html,all}` | `terminal` | 输出格式 |
| `--out-dir DIR` | `.` | 报告文件保存目录（`json` / `html` / `all` 时生效） |
| `--output-file PATH` | 无 | 指定单个输出文件路径。**仅当 `-o json` 或 `-o html` 时生效**；`-o all` 时忽略 |
| `-v, --verbose` | 关 | 显示全部检查项与每项证据，并追加「设备清单」段 |
| `--no-color` | 关 | 禁用 ANSI 颜色 |
| `-q, --quiet` | 关 | 不打印进度与横幅，只输出报告本身 |

### 历史与对比

| 参数 | 默认 | 说明 |
|---|---|---|
| `--save-history` | 关 | 把本次结果存入历史库 |
| `--history-db PATH` | `~/.nastool/history.db` | 历史库路径 |
| `--history [N]` | 20 | 列出最近 N 次记录后**退出**（不执行检测）。省略 N 时用 20 |
| `--compare [ID]` | `latest` | 与历史记录逐项对比。省略 ID 时对比该主机上一次记录 |
| `--prune-history DAYS` | 无 | 删除超过 N 天的记录后**退出** |

注意：`--compare` 隐含保存——它会先取上一次记录做对比，**再**把本次结果存进去，所以连续跑不会丢失历史。

### 自描述

| 参数 | 说明 |
|---|---|
| `--list-checks` | 列出全部检测项（ID / 名称 / 依赖 / 平台）后退出 |
| `--version` | 打印版本 |
| `-h, --help` | 打印帮助 |

### 上报（可选，默认完全离线）

| 参数 | 默认 | 说明 |
|---|---|---|
| `--push {none,webhook,ainas}` | `none` | 上报通道 |
| `--push-url URL` | 无 | webhook 接收地址（`--push webhook` 时必填） |
| `--push-token TOKEN` | 无 | webhook 鉴权 token |
| `--push-header NAME` | `Authorization` | token 放在哪个请求头 |
| `--nas-host HOST` | `127.0.0.1` | AINAS 地址 |
| `--nas-port PORT` | `8000` | AINAS 端口 |
| `--device-name NAME` | 主机名 | 上报时的设备名 |

---

## 2. 退出码

| 码 | 含义 |
|---|---|
| `0` | 无任何 FAIL |
| `1` | 存在至少一项 FAIL |
| `2` | 参数错误、历史库打不开、或检测过程抛异常 |

### ⚠ 退出码只看 FAIL，不看等级

这是最容易被误用的地方：

```python
return EXIT_OK if report.healthy else EXIT_PROBLEM   # healthy = 没有 FAIL
```

也就是说：

| 报告 | 等级 | 退出码 |
|---|---|---|
| 98 分，1 项 WARN | A | **0** |
| 74 分，盲区 60% 触发封顶，无 FAIL | C | **0** |
| 59 分，1 项 SMART 失败 | D | **1** |

第三行才是「有严重问题」。**盲区封顶只降等级，不改变退出码**——这是有意的：盲区大表示「没查清楚」，不等于「确认有故障」，不该让 cron 半夜报警。

如果 CI 需要按等级门禁，请消费 JSON：

```bash
nastool -q -o json || exit 1
python -c "
import json,sys
r=json.load(open('nastool_report.json'))
sys.exit(0 if r['score']['grade'] in ('A','B') else 1)"
```

---

## 3. 典型用法

### 日常体检

```bash
nastool
```

### 出三份报告存档

```bash
nastool -p verify -o all --out-dir ./reports
# → reports/nastool_report.json
#   reports/nastool_report.html
#   （终端输出直接打在屏幕上）
```

`-o all` 不生成终端文件——终端报告只打印，不落盘。

### 二手验机

```bash
nastool -p verify -v --save-history
```

`verify` 场景把安全权重提到 18，阈值放宽避免误报。`-v` 让你看到 SMART 通电时长、坏道计数这些议价依据。

### 只看存储与安全

```bash
nastool --only storage.* --only security.* -v
```

### 定时巡检

```bash
# 每天 3 点跑一次，有严重问题就发邮件
0 3 * * * /usr/local/bin/nastool -q -o json --save-history \
          --out-dir /var/log/nastool || mail -s "NAS 异常" admin@example.com
```

配合 `--prune-history 90` 每月清理一次：

```bash
0 4 1 * * /usr/local/bin/nastool --prune-history 90
```

### 追踪一块盘的老化

```bash
nastool --only "storage.smart_*" -v --save-history
# 每隔一段时间再跑，然后：
nastool --compare latest --only "storage.smart_*"
```

### 验证备份服务器可达

```bash
nastool --peer 192.168.1.10:445 --peer 192.168.1.20:22 -q
```

### 排查一台不是本机的机器

nastool 需要在**被检测的机器上**运行（不是远程探测工具）。通过 SSH 过去跑：

```bash
ssh user@nas 'python3 -m nastool -v' | tee nas-check.txt
```

---

## 4. 输出文件命名

| `-o` | 产物 |
|---|---|
| `terminal` | 无文件，只打印 |
| `json` | `<out-dir>/nastool_report.json`（或 `--output-file`） |
| `html` | `<out-dir>/nastool_report.html`（或 `--output-file`） |
| `all` | 上述两个文件 + 终端打印 |

目录不存在会自动创建。

---

## 5. 通配符规则

`--only` / `--skip` 使用 `fnmatch` 语义（大小写敏感）：

| 模式 | 匹配 |
|---|---|
| `storage.*` | 全部存储项 |
| `*.smart_*` | 所有分类下名含 `smart_` 的项 |
| `storage.smart_health` | 精确一项 |
| `network.peer_*` | `peer_reach` |
| `usb.*` | 全部外设项 |

`--only` 与 `--skip` 同时给出时，**先 only 再 skip**：

```bash
nastool --only "storage.*" --skip "*.smart_*"    # 存储类里除 SMART 之外的全部
```

---

## 6. 环境依赖

| 依赖 | 用途 | 缺失时 |
|---|---|---|
| Python ≥ 3.9 | 运行 | — |
| `smartctl` | SMART 检测 | 相关 4 项标 SKIP |
| `lsblk` | 物理盘识别 | `storage.physical_disks` → UNKNOWN |
| `zpool` / `btrfs` | 阵列检测 | 该路径不可用，mdstat 仍有效 |
| `ss` / `netstat` | 端口清单 | 服务类多项 → UNKNOWN |
| `ip` / `ifconfig` | 网卡 | 网络类 → UNKNOWN |
| `openssl` | 证书解析 | 安全证书类 → SKIP |
| `timedatectl` | 时间同步 | 回退读 NTP 配置文件 |
| `docker` | 容器清单 | `services.docker` → SKIP |
| `nvidia-smi` / `rocm-smi` | AI 加速器 | 该芯片探测失败，其余继续 |

**没有一个依赖是硬性要求。** 缺什么都只是降低覆盖度，不会让工具跑不起来。

`PyYAML` 是唯一可选第三方包，只用于读取 `config.yaml` 形式的项目配置（`pip install -e ".[config]"`）。

---

## 7. 已知行为细节

这些不是 bug，但值得知道：

| 现象 | 原因 |
|---|---|
| `-o all` 时 `--output-file` 被忽略 | 一个文件路径没法同时装 JSON 和 HTML |
| `--history` / `--prune-history` 不跑检测 | 它们是独立的查询/维护动作，执行后直接退出 |
| `--compare` 会顺带保存 | 否则每次对比都要写两个参数 |
| `--enable` 不出现在 `meta.options` 里 | 它反映在 `score.categories[]`（多出一个权重 8 的分类） |
| `--only` 会越过场景范围 | 显式指定优先于场景默认，但权重/阈值仍按场景算 |
| 单项检查最长 60 秒 | `RunOptions.check_timeout`，仅 POSIX 生效；Windows 依赖各采集器自身的 subprocess 超时 |
| `--history-db` 请用绝对路径 | 默认的 `~/.nastool/history.db` 由程序展开；**自己指定时 `~` 只在 shell 里才展开**，通过 API 传参请写绝对路径 |

---

## 8. 相关代码

| 文件 | 职责 |
|---|---|
| `nastool/cli.py` | 参数定义、流程编排、退出码 |
| `nastool/__main__.py` | `python -m nastool` 入口 |
| `nastool/engine.py` | `RunOptions` 与执行 |
