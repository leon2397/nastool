# 变更日志

## 未发布 — 前身设计资产提取

从归档中抢救前身项目的设计资料，整理为可执行的路线图。**不改动产品代码**。

### 新增文档
- `docs/CHECKS-ROADMAP.md`：前身 92 个检测器的完整清单，逐项标注当前实现状态（已实现 20 / 部分 8 / 未实现 64，已实现 22%、含部分覆盖约 26%）
- `docs/DESIGN-NOTES.md`：从 14 篇原始文档提炼的设计要点——准确性保障层（数据融合 / 一致性验证 / 置信度）、`--profile` 场景化检测与动态权重、按芯片型号的自适应阈值、带风险等级的行动计划、修复引擎的四级风险模型、12 条真机 BUG 教训
- `reference/README.md`：前身项目全貌（1,086 文件 / 1,817 函数类 / 6 子包 / v7.1.0-beta）、可复用资产、刻意排除项

### 新增参考代码（`reference/legacy/code/`，不参与构建、不参与打包）
- `compare.py`（729 行）：历史库 schema、趋势判定、理想基线——纯标准库，可直接移植
- `scan.py`（627 行）：网段扫描与设备类型识别
- `batch.py`（420 行）：多设备并行诊断调度
- `upnp_discovery.py`（149 行）：SSDP/UPnP 局域网发现
- `scan_ports.py`（46 行）：多线程端口探测

### 说明
- 前身项目的业务内核（`nastool-core` / `-common` / `-fixes`）已随归档丢失，参考代码依赖这些不存在的包，**不可直接运行**
- 下列内容刻意未提取：`main.py`（纯壳）、`nastool_agent.py`（远程执行 shell）、硬编码 SSH 凭据的诊断脚本、带默认管理令牌的 Jetson 安装脚本、依赖 relay 服务端的 WebSocket 客户端

---

## 0.2.0 — 首个独立版本（通用 NAS 化）

从 AINAS 项目的 `tools/nastool` 中独立出来，成为不依赖任何后端的通用 NAS 检测工具。

### 新增
- **NAS 平台识别**（`core/platform_detect.py`）：群晖 DSM、威联通 QTS、TrueNAS、unRAID、铁威马 TOS、绿联 UGOS、OMV、CasaOS、飞牛 fnOS、Proxmox、OpenWrt、通用 Linux / Windows / macOS；并识别 Docker / LXC / K8s / 虚拟机
- **RAID 检测**：`/proc/mdstat`（含降级与重建进度）、ZFS `zpool`、Btrfs 设备错误计数
- **SMART 检测**：健康结论、温度、通电时长、重映射/待定扇区
- **服务与端口探测**（`core/services.py`）：常见 NAS 服务对照、Docker 容器清单、风险端口提示
- **健康评分**（`core/scoring.py`）：存储 40 / 网络 25 / 系统 20 / 服务 15，A-D 等级，问题清单带修复建议
- **连接器层**（`nastool/connectors/`）：`webhook` 通用上报、`ainas` 可选接入；默认完全离线
- **HTML 报告重写**：单文件、零外部依赖、可打印
- **打包**：`pyproject.toml`，`pip install -e .` 后可用 `nastool` 命令；`python -m nastool` 也可直接跑
- **测试**：18 项，覆盖解析器、评分与端到端报告生成

### 通用化改造
- 存储路径默认值不再写死 `/home/nvidia`，改为自动挑选 NAS 数据盘（并验证可写）
- 移除 AI-NAS 专属 config.yaml 探测，改为通用 `--config` / `NASTOOL_CONFIG` 提示
- 网络检测从「NAS 后端连通性」改为通用「对端 host:port 可达性」
- AI 能力改为加分项：不再因为没装 PyTorch 而判整机不健康
- 新增 AMD ROCm、Google Coral Edge TPU 识别
- 设备采集补齐 Windows / macOS 实现（原先在非 Linux 上一片未知）

### 修复
- `core/network.py`：`_cidr_to_netmask` 位移方向错误，`/24` 会算成 `0.255.255.255`
- `core/network.py`：`get_interfaces()` 使用 `os.path.exists` 但顶层缺 `import os`
- `core/storage.py`：字段名 `4k_read_iops` / `4k_write_iops` 是非法 Python 标识符，整个包无法 import
- `reporters/terminal.py`：访问不存在的 `report.device` 属性
- `reporters/html_reporter.py`：模板占位符 `{nas_class}` 与传参 `nas_cls` 键名不一致
- 非 Linux 环境下 `/dev`、`/sys/class/thermal` 的 `listdir` 缺少存在性保护
- Windows 中文输出乱码（`text=True` 固定编码）→ 统一 UTF-8 优先 + locale 回退；PowerShell 调用改为参数列表
- 评分与结论可能矛盾（A 级 + 严重问题）→ 存在严重问题时总分封顶 59

### 移除
- `nastool_agent.py`（可远程执行任意 shell 的 relay 客户端）
- `jetson_install.py` / `jetson_patch.py`（带默认管理令牌的管理端点）
