# 0006. 运行时零第三方依赖

- 状态：生效
- 日期：2026-10-28（沿用 0.2.0 的决定并强化）
- 影响：部署方式、功能取舍、可移植性

## 背景

目标场景决定了这条约束：

**被检测的机器往往是「最不方便装东西」的那台。**

一台群晖、一台老 ARM 盒子、一台刚接手还没配好的二手 NAS——上面可能：

- 没有 pip，或者 pip 装了但不允许联网
- Python 版本旧（3.8、3.9）
- 系统 Python 受厂商保护，`pip install` 会破坏套件依赖
- 没有编译工具链，装不了带 C 扩展的包

前身项目需要 6 个 pip 包，结果在实际交付中反复卡在第一步：**装不上**。用户还没看到报告就先放弃了。

## 决策

**运行时依赖为零。** 只用标准库。通过以下方式替代第三方能力：

| 原本想用 | 实际做法 |
|---|---|
| `psutil` | 直接读 `/proc/meminfo`、`/proc/stat`、`/sys/class/thermal`；Windows 走 `wmic` / PowerShell |
| `requests` | `urllib.request`（webhook 上报、AINAS 接入） |
| `netifaces` | 解析 `ip addr` / `ifconfig` 输出 |
| `pysmart` | 调 `smartctl --json` 并解析 |
| `py-cpuinfo` | 读 `/proc/cpuinfo` + 平台特定文件（如 DSM 的 `syno_hw_version`） |
| `rich` / `colorama` | 手写 ANSI 转义 + 自己的中文宽度对齐（`_width` / `_pad`） |
| `pydantic` | `dataclasses` + 手写 `to_dict()` |
| `sqlalchemy` | `sqlite3`（历史库） |

**唯一的可选依赖是 `PyYAML`**，只在读取 `config.yaml` 形式的项目配置时需要，通过 `pip install -e ".[config]"` 按需安装，缺失时静默跳过。

## 后果

### 好处

- **单文件可跑**：`python -m nastool` 在任何有 Python 3.8+ 的机器上直接工作，包括离线环境
- 复制粘贴即可部署：一个目录拷过去就能跑，不需要建虚拟环境
- 不受厂商 Python 环境保护机制影响
- 依赖少了，出错的可能性也少——排查问题时不需要怀疑「是不是某个包版本不对」

### 代价（这是真实的、必须承受的）

- **代码量更大**。`collect/` 2,921 行里相当比例是在做第三方库本来会做的事：解析 `df -kP`、`ip addr`、`smartctl --json`、mdstat、`/proc/meminfo`
- **平台兼容要自己扛**。Windows 的 `wmic` 输出、中文编码、PowerShell 引号转义、GBK 解码，全部手写。实测踩过的坑：`Get-NetFirewallProfile | ConvertTo-Csv` 输出带引号导致 `,True` 匹配失败；`w32tm` 输出 GBK 解码成乱码
- **性能不如专用库**。`urllib` 没有连接池；`sqlite3` 直接写 SQL。对本项目影响可忽略
- **无法使用需要编译的先进能力**。例如本地向量搜索（`hnswlib`）、图像处理，这些功能就不做

### 缓解

- 命令执行统一走 `collect/util.py: run()`，集中处理编码回退（UTF-8 → mbcs → locale）、超时、异常吞掉
- 解析器独立成函数并配单元测试（`tests/test_parsers.py` 喂真实输出片段）
- 所有外部命令缺失时降级为 SKIP / UNKNOWN，工具本身绝不因此崩

## 值得记录的一条教训

零依赖的直接后果是「所有解析都是手写的」，而手写解析的错误往往**只在特定环境下暴露**。

两个实例：

1. `_cidr_to_netmask` 位移方向写反，`/24` 算成 `0.255.255.255`——在有线千兆的正常机器上从不触发，只在解析特定格式时才走那条分支
2. Windows 防火墙用 `,True` 匹配，但 `ConvertTo-Csv` 输出的是 `"True"`（带引号），于是所有 Windows 机器都报「防火墙未启用」——假阳性

处理方式不是「改用第三方库」，而是**给每个解析器配真实输出片段的测试**。降低的是「约定」的成本，不是「验证」的成本。

## 考虑过但否决的方案

**允许「少量、纯 Python」的依赖**（例如只用 `requests`，因为它是纯 Python 且几乎处处都有）。

否决理由：一旦开了口子，「少量」会变成 3 个、5 个。而且「几乎处处都有」在离线设备上不成立，在最需要它的场景里失效。零依赖是一条清晰的、可检查的红线；「少量依赖」不是。
