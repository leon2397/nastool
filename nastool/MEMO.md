# nastool 开发备忘录

> 记录日常开发进度、决策、问题与经验
> 日期：2026-04-15
> 当前版本：**v5.0.4**（开发中）

---

## 项目结构

```
D:\armtool415\
├── nastool/              # 诊断引擎（Python，v5.0.4，223文件/40K行）
│   ├── arm_diagnose.py   # 主入口，CLI
│   ├── checks/           # 90项检测（7类）
│   ├── fixes/            # 18个修复模块
│   ├── reporters/        # 7种报告器
│   └── core/             # 核心模块（含死代码，见下）
├── nastools_pkg/         # Windows GUI 封装层（v2.0）
├── relay_server/         # Relay Server（Node.js，v1.0）
└── nastools-v2.0.0/      # 发布包
```

---

## 版本历史

| 版本 | 日期 | 核心更新 |
|------|------|----------|
| v5.0.4 | 2026-04-15 | 智能修复推荐系统（交互式 fix UI）|
| v5.0.3 | 2026-04-15 | USB 连接检测模块（4项新增，82→86项）|
| v5.0.2 | 2026-04-14 | 健康评分系统 v2（health_scorer + 仪表盘 + 术语翻译）|
| v5.0.1 | 2026-04-14 | 检测项扩容（33项，80→86项）|
| v5.0.0 | 2026-04-14 | 从 v3.0.7 直接跃升至 v5.0.0 架构升级 |
| v3.0.7 | 2026-04-12 | NAS 适配器体系（群晖/威联通/AI-NAS）|

---

## v5.0.4 智能修复推荐系统

**状态**：✅ P0 完成（2026-04-15）
**Commit**：`58bf1d5`

### 设计原则

- 定位为「诊断工具」而非「运维自动化平台」
- 高危修复（RAID操作、禁用root）不自动执行
- 建立「智能推荐」机制而非「自动闭环」
- 只推荐不强制，用户自主决策

### 新增文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `fixes/fix_recommendations.py` | 7,237 B | 检测→修复映射表 |
| `fixes/interactive_fix.py` | 7,962 B | 交互式修复 UI |

### 修复建议映射

```
degraded --fix
  🔒 安全类（3项可修复）
    [1] SSL证书即将过期 → renew_ssl_cert
    [2] SSH允许root登录 → disable_root_login
    [3] 登录失败攻击检测 → enable_fail2ban

  🐳 Docker类（1项可修复）
    [4] 镜像占用过高 → cleanup_docker_images

  🩺 需人工处理（67项）— 折叠显示
请输入编号执行修复：[1,2,5]
```

### 本次修复的 Bug

| Bug | 原因 | 修复 |
|-----|------|------|
| `arm_diagnose.py` 旧 `--fix` 代码块替换失败 | CRLF + PowerShell 解析 | 改用 Python 脚本直接替换 |
| `CheckSeverity` 比较逻辑错误 | `.value` 返回字符串非整数 | 用 enum 本身比较 |
| `BMAG` 颜色变量未定义 | 拼写错误 | 修正常量名 |
| `os.geteuid()` Windows 不存在 | Unix 特有 API | 添加 `os.name == 'nt'` 分支 |

---

## v5.0.3 USB 连接检测模块

**Commit**：`16b6705`
**统计**：82项 → 86项（+4 USB检测）

| check_id | 检测内容 | Severity |
|----------|---------|----------|
| `usb_devices` | USB 设备列表 | INFO |
| `usb_storage_mount` | USB 存储挂载状态 | WARNING |
| `usb_permissions` | USB 设备权限 | WARNING |
| `usb_power` | USB 端口供电健康 | WARNING |

---

## v5.0.2 健康评分系统 v2

**Commit**：`4e0acd5` + `8e0e82a`

### 健康评分引擎 `utils/health_scorer.py`

- 三层权重体系：critical=3x / important=2x / standard=1x / info=0x
- 7类独立评分：存储/系统/网络/AI/安全/NAS/USB
- 加权综合分：weighted_sum / total_weight
- 6级评分制：A+/A/A-/B+/B/C/D/F
- 相比上次分数变化追踪（↑↓）

### 健康仪表盘 `reporters/health_dashboard.py`

- 彩色大字体评分（🌟 Excellent / ✅ Good / ⚠️ Warning / 🔴 Critical）
- ASCII 进度条（64字符宽度）
- 7类分类评分条
- 紧急事项列表

### 术语翻译层 `utils/terminology.py`

- 90个检测项工程师→通俗语言翻译
- 7大类别中文标签
- 严重程度/风险等级翻译
- `translate_result()` / `generate_suggestions()`

---

## nastools v2.0 路线图

```
Phase 4-1 ✅ 基础设施（Relay Server，Node.js + Fastify + sql.js）
Phase 4-2 ✅ 双模式连接 + GUI 集成
Phase 4-3 ✅ 远程操作（命令/文件/升级）
Phase 4-4 ✅ 多设备管理 UI（批量选择/详情面板/历史/自动刷新）
Phase 4-5 ✅ 批量部署（多设备并行部署+进度追踪）
Phase 4-6 ✅ 报告导出+趋势图（CSV导出/趋势统计图）
─────────────────────────────────────────
nastools v2.0.0 ✅ Release Complete (2026-04-14)
```

---

## 遗留问题（未解决）

### Issue #3 — 版本号混乱（仅讨论，未执行）

| 来源 | 版本 | 状态 |
|------|------|------|
| `constants.py` `__version__` | 4.2.0 | ❌ 旧了（死代码，仅测试引用）|
| `arm_diagnose.py` docstring | v4.2.0 | ❌ 旧了 |
| `arm_diagnose.py` 内部 `__version__` | 5.0.2 | ✅ 正确 |
| MEMO.md 当前版本 | v5.0.2 | ⚠️ 需更新至 v5.0.4 |
| `--version` 输出 | nastool 5.0.2 | ✅ 正确 |
| VERSION.txt | 不存在 | ❌ 缺失 |

### Issue #4 — 旧代码残留（仅讨论，未执行）

`core/` 目录中有一批 `_health.py` 旧架构文件：

| 文件 | 状态 |
|------|------|
| `core/nas_health.py` | 死代码，无任何 import |
| `core/network_health.py` | 死代码，无任何 import |
| `core/security_health.py` | 死代码，无任何 import |
| `core/storage_health.py` | 死代码，无任何 import |
| `core/system_health.py` | 死代码，无任何 import |
| `core/device.py` | 死代码，仅测试引用 |
| `core/safety.py` | 死代码，无引用 |
| `core/upnp_scanner.py` | 死代码，无引用 |

`core/` 中仍在用的模块：version_check / config_loader / ai_accel / network / storage

`reporters/health_dashboard.py` 中 `v4.0.2 图形化看板` 是过时注释，文件本身正常运行。

### Issue #5 — `config_ups_shutdown` fix 有 bug

`fixes/nas/config_ups_shutdown.py` 中有 `bool` 类型错误（原有 bug，P0 不影响运行）。

---

## 技术约定

- **Heredoc 传输 Bug**：PowerShell `cat >>` 中 `\n` 被解析为实际换行符，会破坏 Python 代码
  → 用 git / SCP 压缩包 / write 工具传输含换行字符串
- **PowerShell 不支持 `&&`**：需用分步执行
- **Windows `os.geteuid()`**：Unix 专用，需加 `os.name == 'nt'` 分支

---

## 下一步

1. ~~修复建议智能推荐~~ → ✅ v5.0.4 P0 完成
2. ~~报告标注「需人工处理」~~ → P1 可选
3. nastools GUI 添加 Nastool 检测模式 → P2
4. nastools GitHub 发布 → P3
