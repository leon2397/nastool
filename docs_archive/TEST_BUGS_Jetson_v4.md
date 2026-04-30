# Jetson 真机 BUG 记录 (TEST_BUGS_Jetson_v4.md)

> 更新日期：2026-04-25
> 测试设备：Jetson Xavier NX (192.168.1.123)
> nastool 版本：4.0.0

---

## BUG 记录

### BUG-012: Python 版本检测错误

**严重程度**：P1 (Critical)
**现象**：
- nastool 显示：Python 版本: 3.12
- 实际值：`python3 --version` 显示 3.8.10

**根因分析**：
- nastool 使用 python3.9 运行（安装时指定的），但检测 python3 --version 时显示 3.8.10
- 原代码使用 `sys.version_info` 检测的是运行 nastool 的 Python 版本，而不是系统的默认 Python 版本

**修复方向**：
- 已修复：改为检测系统默认的 `python3 --version` 命令输出
- 修复文件：`nastool-core/nastool_core/checks/system/python_version.py`

**修复验证**：
- 直接调用 `PythonVersionCheck().run()` 返回正确的 3.8 版本
- 由于默认模式使用 mock 数据，需要在真实模式下验证

---

### BUG-013: 系统运行时间显示为 mock

**严重程度**：P2 (Warning)
**现象**：
- nastool 显示：`i 系统运行时间: mock`
- 实际值：uptime 显示系统已运行 2 days, 23:58

**根因分析**：
- 系统运行时间检测项标记为 mock 模式，未实现真实检测

**修复方向**：
- 在 system/uptime_check.py 或相关文件中实现真实系统运行时间检测

---

### BUG-014: USB 设备检测全部为 mock

**严重程度**：P2 (Warning)
**现象**：
- nastool 显示：
  - i USB 设备检测: mock
  - i USB 设备权限: mock
  - i USB 端口供电: mock
  - i USB 存储挂载: mock

**根因分析**：
- USB 检测功能尚未在 Jetson 上实现

**修复方向**：
- 实现 Jetson 兼容的 USB 检测功能

---

### BUG-015: Docker 检测显示 mock 但实际有容器

**严重程度**：P2 (Warning)
**现象**：
- nastool 显示：`i Docker Info: mock`
- 但同时显示：`[OK] Docker 容器: 12 containers (8 running, 4 stopped)`

**根因分析**：
- Docker Info 为 mock 模式，但 Docker 容器数量检测是真实的
- 说明 Docker 相关检测部分实现了，部分是 mock

**修复方向**：
- 实现 Docker Info 的真实检测

---

### BUG-016: Latency Check 显示为 mock

**严重程度**：P3 (Info)
**现象**：
- nastool 显示：`i Latency Check: mock`

**根因分析**：
- 延迟检测尚未实现真实模式

**修复方向**：
- 实现网络延迟检测功能

---

### BUG-017: 系统盘空间检测显示不正确

**严重程度**：P2 (Warning)
**现象**：
- nastool 显示：`[OK] 系统盘空间: NVMe 500GB (250GB used, 50%)`
- 实际值：`df -h` 显示 `/dev/nvme0n1p1  117G   83G   30G  74%`

**根因分析**：
- 系统盘空间检测逻辑不准确，显示的是固定值

**修复方向**：
- 实现真实的系统盘空间检测

---

### BUG-018: 网络带宽检测显示多个网卡

**严重程度**：P3 (Info)
**现象**：
- nastool 显示：`[OK] 网络带宽: eth0, eth1, eth2`
- 实际值：`ip addr show` 显示只有 eth0 是 UP 状态，eth1 是 DOWN 状态

**根因分析**：
- 检测逻辑可能不准确，未考虑网卡状态

**修复方向**：
- 优化网络带宽检测，只显示 UP 状态的网卡

---

### BUG-019: DNS 检测显示 Google/Cloudflare DNS 失败

**严重程度**：P2 (Warning)
**现象**：
- nastool 显示：`[!] DNS 配置: 2 of 5 passed。DNS 配置偏少，建议增加备用 DNS`

**根因分析**：
- 这是用户配置的警告，不是 BUG
- 当前配置了 223.5.5.5 和 114.114.114.114，未配置 Google/Cloudflare DNS

---

## 测试命令

```bash
ssh nvidia@192.168.1.123
nastool --full
python3 --version
uptime
docker ps
df -h
ip addr show
```

---

## 待修复列表

| BUG | 描述 | 严重程度 | 状态 |
|-----|------|----------|------|
| BUG-012 | Python 版本检测错误 | P1 | **已修复** |
| BUG-013 | 系统运行时间 mock | P2 | 待修复 |
| BUG-014 | USB 检测全部 mock | P2 | 待修复 |
| BUG-015 | Docker Info mock | P2 | 待修复 |
| BUG-016 | Latency Check mock | P3 | 待修复 |
| BUG-017 | 系统盘空间检测不正确 | P2 | 待修复 |
| BUG-018 | 网络带宽检测显示多余网卡 | P3 | 待修复 |
| BUG-019 | DNS 检测配置警告 | P2 | 非 BUG |

---

## 测试结果总结

**nastool --full 运行结果**：97分 / Grade A+
- 83 Passed
- 10 Warning
- 0 Critical
- 0 Info

**测试发现**：
1. 已修复 1 个 P1 级 BUG（Python 版本检测）
2. 发现 6 个待修复 BUG（2 个 P2，4 个 P3）
3. 1 个非 BUG 警告（DNS 配置）

**建议**：
- 优先修复 P2 级 BUG（系统运行时间、USB 检测、Docker Info、系统盘空间）
- 其次修复 P3 级 BUG（Latency Check、网络带宽检测）
- 考虑增加 Jetson 特有的检测项（如 Jetson 版本、GPU 状态等）
