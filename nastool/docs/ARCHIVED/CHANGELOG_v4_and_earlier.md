# nastool Changelog (v4.0.2 and earlier)

> 本目录为 v4.0.2 及更早版本的历史变更记录。
> 当前版本请查阅项目根目录的 `CHANGELOG.md`。

## [Unreleased] 鈥?nastools v4.0.2

### Added 鈥?妫€娴嬮」澶ф墿瀹癸紙P0锛夝煍?
**2026-04-14**: v4.0.2 P0 闃舵瀹屾垚锛?0 椤规柊澧炴娴?
**瀛樺偍鍋ュ悍 脳5**锛?- `storage/smart_health.py` 鈥?SMART 纭洏鍋ュ悍妫€娴嬶紙閲嶅垎閰嶆墖鍖?Pending/Uncorrectable锛?- `storage/hdd_temp.py` 鈥?HDD/SSD 娓╁害妫€娴嬶紙smartctl/hddtemp/nvme锛?- `storage/raid_status.py` 鈥?RAID 闃靛垪鐘舵€侊紙mdadm/btrfs/zfs锛?- `storage/docker_images.py` 鈥?Docker dangling 闀滃儚娓呯悊妫€娴?- `storage/storage_trend.py` 鈥?瀛樺偍绌洪棿瓒嬪娍鍒嗘瀽锛堝巻鍙蹭娇鐢ㄧ巼 + 棰勬祴锛?
**绯荤粺 脳3**锛?- `system/cpu_temp.py` 鈥?CPU 娓╁害妫€娴嬶紙thermal_zone/sensors 澶氭簮锛?- `system/uptime.py` 鈥?绯荤粺鍚姩鏃堕棿 + 璐熻浇璇勪及
- `system/docker_containers.py` 鈥?Docker 瀹瑰櫒杩愯鐘舵€?
**缃戠粶 脳2**锛?- `network/nic_speed.py` 鈥?缃戝崱 link speed 妫€娴嬶紙ip link/ethtool锛?- `network/dns_coverage.py` 鈥?DNS 瑕嗙洊妫€娴嬶紙/etc/resolv.conf锛?
**瀹夊叏 脳2**锛?- `security/login_failures.py` 鈥?SSH 鐧诲綍澶辫触娆℃暟妫€娴嬶紙鏆村姏鐮磋В璇嗗埆锛?- `security/ssl_cert.py` 鈥?SSL 璇佷功鏈夋晥鏈熸娴?
**NAS 绯荤粺 脳6**锛堟柊澧?`nas/` 鐩綍锛夛細
- `nas/dsm_version.py` 鈥?缇ゆ櫀 DSM / 濞佽仈閫?QTS 鐗堟湰妫€娴?- `nas/user_stats.py` 鈥?NAS 鐢ㄦ埛璐﹀彿缁熻 + 寮卞瘑鐮佹娴?- `nas/shared_perms.py` 鈥?鍏变韩鏂囦欢澶规潈闄愭娴?- `nas/ups_status.py` 鈥?UPS 杩炴帴鐘舵€?+ 鐢甸噺妫€娴嬶紙NUT/apcupsd锛?- `nas/log_disk.py` 鈥?/var/log 鏃ュ織纾佺洏绌洪棿妫€娴?- `nas/cron_conflicts.py` 鈥?瀹氭椂浠诲姟鍐茬獊妫€娴?
**鏋舵瀯**锛?- `checks/base.py` 鈥?鏂板 `CheckCategory.NAS` 鏋氫妇
- `checks/__init__.py` 鈥?鍏ㄩ儴 33 涓娴嬬被娉ㄥ唽
- 鎬昏锛?*33 涓娴嬫枃浠?*锛岃鐩?6 澶х被鍒?
---

## [Unreleased] 鈥?nastools v2.0

### Added 鈥?Relay Server (Phase 4-1) 馃殌

**2026-04-14**: nastools v2.0 璺ㄧ綉杩滅▼绠＄悊鍩虹璁炬柦

- **`relay_server/src/index.js`** 鈥?Fastify 涓诲叆鍙ｏ紝WebSocket + REST API
- **`relay_server/src/ws_handler.js`** 鈥?Agent/GUI WebSocket 澶勭悊鍣?  - Agent 杩炴帴姹犵鐞嗭紙鍦ㄧ嚎璁惧杩借釜锛?  - GUI 杩炴帴姹犵鐞嗭紙澶氬鎴风鏀寔锛?  - 鍛戒护杞彂锛坥nline 鐩存帴鍙?/ offline 鍏ラ槦锛?  - 鎶ュ憡瀹炴椂鎺ㄩ€侊紙broadcast to GUI锛?  - 蹇冭烦淇濇椿锛?0s interval锛?0s timeout锛?  - 鏂嚎閲嶈繛鑷姩琛ュ彂 pending 鍛戒护
- **`relay_server/src/routes.js`** 鈥?REST API 璺敱锛?1 涓鐐癸級
  - `/api/v1/auth/login` 鈥?GUI JWT 鐧诲綍
  - `/api/v1/devices` 鈥?璁惧鍒楄〃
  - `/api/v1/devices/:id/commands` 鈥?鍛戒护涓嬪彂/鏌ヨ
  - `/api/v1/devices/:id/reports/latest` 鈥?鏈€鏂版姤鍛?  - `/api/v1/devices/:id/deploy` 鈥?瑙﹀彂閮ㄧ讲
  - `/api/v1/keys/generate` 鈥?鐢熸垚 agent_key
  - `/api/v1/relay/status` 鈥?鏈嶅姟鐘舵€?  - `/health` 鈥?鍋ュ悍妫€鏌?- **`relay_server/src/db.js`** 鈥?SQLite 鏁版嵁搴撳眰锛坰ql.js WASM锛?  - 6 寮犺〃锛歛gents / sessions / commands / reports / files / deployments
  - 绾?JS 瀹炵幇锛學indows 鏃犻渶 VS Build Tools
- **`relay_server/ecosystem.config.js`** 鈥?PM2 閰嶇疆
- **`relay_server/README.md`** 鈥?浣跨敤鏂囨。
- **`relay_server/SPEC.md`** 鈥?瀹屾暣 API 瑙勮寖锛?5KB锛?
**WebSocket 鍗忚**锛?- Agent 鈫?`register` / `heartbeat` / `report` / `response` / `log`
- GUI 鈫?`command` / `file` / `heartbeat` / `disconnect`
- Relay 鈫?`register_ack` / `command` / `file` / `disconnect`

**閮ㄧ讲淇℃伅**锛?- 绔彛锛?8888锛圚TTP/WebSocket锛?- ECS 鍦板潃锛?20.77.249.3
- 榛樿 GUI锛歛dmin / relay-admin-2026

## [3.0.7] - 2026-04-12

### Added - NAS Backend Integration 馃彚

**P0 Core Adapters** - 缁熶竴 NAS 鍚庣鎺ュ彛

- **`adapters/base.py`** (15.7 KB) - 鎶借薄鍩虹被 NASBackend
  - 16 涓帴鍙ｆ柟娉曞畾涔?  - DeviceInfo / ScanPath / DiagnosticReport 鏁版嵁缁撴瀯
  - StandaloneAdapter 鐙珛妯″紡瀹炵幇

- **`adapters/synology.py`** (15.8 KB) - 缇ゆ櫀 ARM NAS 閫傞厤鍣?  - DSM API 鐧诲綍/鐧诲嚭
  - 璁惧娉ㄥ唽
  - 鎵弿璺緞鑾峰彇
  - ARM 鑺墖妫€娴嬶紙RTD1619B, Armada锛?
- **`adapters/qnap.py`** (13.2 KB) - 濞佽仈閫?ARM NAS 閫傞厤鍣?  - QTS API 闆嗘垚
  - 鏀寔 Annapurna Labs AL-314/AL-514 鑺墖
  - 鍏变韩鏂囦欢澶圭鐞?
- **`adapters/http_backend.py`** (10.3 KB) - AI-NAS HTTP 鍚庣
  - 鍚戝悗鍏煎鐜版湁 AI-NAS 鐢ㄦ埛
  - 璁惧娉ㄥ唽 API
  - 璇婃柇鎶ュ憡涓婁紶

**P1 Synology Deep Integration** - 缇ゆ櫀娣卞害闆嗘垚


---

## [Unreleased] — nastools v4.0.2

### Added — 检测项大扩容（P0）🔥

**2026-04-14**: v4.0.2 P0 阶段完成，20 项新增检测

**存储健康 ×5**：
- `storage/smart_health.py` — SMART 硬盘健康检测（重分配扇区/Pending/Uncorrectable）
- `storage/hdd_temp.py` — HDD/SSD 温度检测（smartctl/hddtemp/nvme）
- `storage/raid_status.py` — RAID 阵列状态（mdadm/btrfs/zfs）
- `storage/docker_images.py` — Docker dangling 镜像清理检测
- `storage/storage_trend.py` — 存储空间趋势分析（历史使用率 + 预测）

**系统 ×3**：
- `system/cpu_temp.py` — CPU 温度检测（thermal_zone/sensors 多源）
- `system/uptime.py` — 系统启动时间 + 负载评估
- `system/docker_containers.py` — Docker 容器运行状态

**网络 ×2**：
- `network/nic_speed.py` — 网卡 link speed 检测（ip link/ethtool）
- `network/dns_coverage.py` — DNS 覆盖检测（/etc/resolv.conf）

**安全 ×2**：
- `security/login_failures.py` — SSH 登录失败次数检测（暴力破解识别）
- `security/ssl_cert.py` — SSL 证书有效期检测

**NAS 系统 ×6**（新增 `nas/` 目录）：
- `nas/dsm_version.py` — 群晖 DSM / 威联通 QTS 版本检测
- `nas/user_stats.py` — NAS 用户账号统计 + 弱密码检测
- `nas/shared_perms.py` — 共享文件夹权限检测
- `nas/ups_status.py` — UPS 连接状态 + 电量检测（NUT/apcupsd）
- `nas/log_disk.py` — /var/log 日志磁盘空间检测
- `nas/cron_conflicts.py` — 定时任务冲突检测

**架构**：
- `checks/base.py` — 新增 `CheckCategory.NAS` 枚举
- `checks/__init__.py` — 全部 33 个检测类注册
- 总计：**33 个检测文件**，覆盖 6 大类别

**设备总覆盖**：51 款（群晖 13 + Jetson 9 + SOPHON 12 + RK3588 6 + QNAP 5 + 华硕 3 + 铁威马 2 + 其他 1）

---

### Added — 修复能力大扩容（5 → 15 种）🔥

**安全类（4个）**：
- `disable_root_login` — 禁用 SSH root 登录（PermitRootLogin no）
- `enable_fail2ban` — 安装并配置 fail2ban SSH 防护（自动封禁暴力破解）
- `enforce_password_policy` — 锁定弱密码用户账号
- `renew_ssl_cert` — 续期即将过期 SSL 证书（生成 365 天临时证书）

**存储类（4个）**：
- `cleanup_logs` — 清理 30 天以上 .gz 日志文件
- `cleanup_docker_images` — 清理 Docker dangling 镜像（docker image prune）
- `cleanup_tmp_space` — 清理 /tmp 和 /var/tmp 超过 7 天的临时文件
- `config_raid_recovery` — RAID 降级恢复向导（提供安全操作指引，非自动执行）

**系统类（1个）**：
- `setup_logrotate` — 配置 logrotate，防止日志无限增长

**NAS 类（1个）**：
- `config_ups_shutdown` — 安装并配置 NUT，实现 UPS 断电自动关机

**修复能力对比**：
| 版本 | Fix 数量 | 覆盖类别 |
|------|----------|---------|
| v4.0.1 | 5 种 | 系统/网络/存储/AI |
| v4.0.2 | 15 种 | 系统/网络/存储/AI/安全/NAS |

---

### Added — 设备覆盖扩展（38 → 51 款）

**新增配置文件** `profiles/new_devices.yaml`（6 584 字节，13 款新设备）：

| 品牌 | 型号 | 架构 | AI 类型 |
|------|------|------|---------|
| 威联通（QNAP，5款） | TS-264 / TS-464 / TS-673A / TS-873A / TS-h2490FU | x86_64 | GPU/CPU |
| 华硕 Asustor（3款） | Drivestor Pro AS7110T / Lockstor AS6508T / Nimbia AS3302T | x86_64/arm64 | CPU |
| 铁威马 TerraMaster（2款） | F4-423 / F5-422 | x86_64 | CPU |
| 树莓派（1款） | Raspberry Pi 4 Model B | arm64 | CPU |
| OrangePi（1款） | OrangePi 5 Plus | arm64 | NPU (RKNN) |
| Radxa（1款） | ROCK 5 ITX | arm64 | NPU (RKNN) |

**loader.py 重构**：
- 修复 detect_device 毁坏bug
- 新增 `_detect_qnap()` — /etc/nas.conf + hostname 检测威联通
- 新增 `_detect_terramaster()` — hostname 检测铁威马
- 更新 `_detect_rk3588()` — 支持 OrangePi 5 Plus / Radxa ROCK 5 ITX
- 统一 meta_keys 过滤集（新增 `total_new_devices`）

**设备总计**：51 款（群晖 13 + Jetson 9 + SOPHON 12 + RK3588 6 + QNAP 5 + 华硕 3 + 铁威马 2 + 其他 1）

---

### Added — 友好人类视角优化

**术语翻译** `utils/terminology.py`（6 607 字节）：
- 33 个检测项工程师术语 → 通俗语言翻译（"GPU 利用率" / "Docker 容器运行中"）
- 6 大类别中文标签（数据存储 / 系统运行 / 网络连接 / AI加速 / 安全防护 / NAS系统）
- 严重程度翻译（CRITICAL → 紧急）
- 风险等级翻译（low/medium/high → 低风险/中风险/高风险）
- `translate_result()` — 单个检测结果的通俗翻译
- `translate_category()` — 类别通俗名称
- `generate_suggestions()` — 自动生成"原因+操作+效果"建议列表

**友好人类报告** `reporters/friendly_reporter.py`（3 187 字节）：
- 彩色健康仪表盘（评分+等级+Grade 字母）
- 6 类别独立评分条（独立颜色+进度条）
- 紧急建议区（只看 CRITICAL/WARNING，限 5 条）
- 每条建议：问题描述 + 重要性 + 操作步骤 + 风险 + 预期效果
- 检查项表格（问题项/正常项，颜色区分）
- `build_compact_text()` — 终端重金属字符摘要

---

## [Unreleased] — nastools v2.0

### Added — Relay Server (Phase 4-1) 🔥

**2026-04-14**: nastools v2.0 跨网远程管理基础设施

- **`relay_server/src/index.js`** — Fastify 主入口，WebSocket + REST API
- **`relay_server/src/ws_handler.js`** — Agent/GUI WebSocket 处理层
  - Agent 连接池管理（在线设备映射）
  - GUI 连接池管理（多客户端支持）
  - 命令转发（online 直接发 / offline 入队列）
  - 报告实时推送（broadcast to GUI）
  - 心跳保活（30s interval / 120s timeout）
  - 断线重连自动重发 pending 命令
- **`relay_server/src/routes.js`** — REST API 路由（11 个端点）
  - `/api/v1/auth/login` — GUI JWT 登录
  - `/api/v1/devices` — 设备列表
  - `/api/v1/devices/:id/commands` — 命令下发/查询
  - `/api/v1/devices/:id/reports/latest` — 最新报告
  - `/api/v1/devices/:id/deploy` — 触发部署
  - `/api/v1/keys/generate` — 生成 agent_key
  - `/api/v1/relay/status` — 服务状态
  - `/health` — 健康检查
- **`relay_server/src/db.js`** — SQLite 数据库层（sql.js WASM）
  - 6 张表：agents / sessions / commands / reports / files / deployments
  - 纯 JS 实现，Windows 不需要 VS Build Tools
- **`relay_server/ecosystem.config.js`** — PM2 配置
- **`relay_server/README.md`** — 使用文档
- **`relay_server/SPEC.md`** — 完整 API 规范（5KB）

**WebSocket 协议**：
- Agent → `register` / `heartbeat` / `report` / `response` / `log`
- GUI → `command` / `file` / `heartbeat` / `disconnect`
- Relay → `register_ack` / `command` / `file` / `disconnect`

**部署信息**：
- 端口：18888（HTTP/WebSocket）
- ECS 地址：120.77.249.3
- 默认 GUI：admin / relay-admin-2026

---

## [3.0.7] - 2026-04-12

### Added — NAS Backend Integration 🔥

**P0 Core Adapters** — 统一 NAS 后端接口

- **`adapters/base.py`** (15.7 KB) — 抽象基类 NASBackend
  - 16 个接口方法定义
  - DeviceInfo / ScanPath / DiagnosticReport 数据结构
  - StandaloneAdapter 独立模式实现

- **`adapters/synology.py`** (15.8 KB) — 群晖 ARM NAS 适配器
  - DSM API 登录/登出
  - 设备注册
  - 扫描路径获取
  - ARM 芯片检测（RTD1619B, Armada）

- **`adapters/qnap.py`** (13.2 KB) — 威联通 ARM NAS 适配器
  - QTS API 集成
  - 支持 Annapurna Labs AL-314/AL-514 芯片
  - 共享文件夹管理

- **`adapters/http_backend.py`** (10.3 KB) — AI-NAS HTTP 后端
  - 向后兼容现有 AI-NAS 用户
  - 设备注册 API
  - 诊断报告上传
