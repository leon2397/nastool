# NASTool v3.0 升级计划（多设备管理与实时协同版）

> 创建时间：2026-04-19
> 版本目标：v3.0
> 项目目录：`C:\tools416\`
> 前置条件：v2.0 Phase A+B+C 全部完成

---

## 一、升级方向

**从"单机检测工具"升级为"多设备协同平台"**，实现：
1. **多设备管理**：批量检测、对比分析、设备分组
2. **实时协同**：WebSocket 状态推送、告警通知
3. **历史追溯**：检测结果存储、趋势分析
4. **生态扩展**：插件系统、API 开放

---

## 二、项目现状分析

### v2.0 已有能力

| 能力 | 状态 | 说明 |
|------|------|------|
| 本地检测 | ✅ | 93项检测，6大分类 |
| RK3588/RK3568 | ✅ | NPU/DDR/thermal/benchmark/driver_ver |
| 远程检测 | ✅ | HTTP + Relay 两种模式（--target 参数）|
| 调优建议 | ✅ | 7维分析，3档配置 |
| RK专用报告 | ✅ | 加权评分 + 趋势分析 |

### Relay Server 可复用能力

| 能力 | 状态 | 说明 |
|------|------|------|
| WebSocket 协议 v2.0 | ✅ | 消息格式统一，错误码体系 |
| API v2 | ✅ | 批量命令、批量部署、API Key 认证 |
| Web Dashboard | ✅ | Vue3 + Tailwind，设备管理界面 |
| Agent 协议 | ✅ | 注册、心跳、命令、报告 |
| 离线队列 | ✅ | 离线设备命令缓存 |

### v3.0 需补充

| 能力 | 优先级 | 说明 |
|------|--------|------|
| **多设备批量检测** | 🔴 高 | 复用 Relay API v2 批量能力 |
| **设备分组管理** | 🔴 高 | 按类型/位置/项目分组 |
| **对比分析** | 🔴 高 | 设备间对比、历史对比 |
| **WebSocket 实时推送** | 🟡 中 | 复用 Relay WebSocket |
| **历史数据存储** | 🟡 中 | SQLite 本地存储 |
| **Web Dashboard 集成** | 🟡 中 | 扩展 Relay Dashboard |
| **插件系统** | 🟢 低 | 第三方检测项扩展 |
| **API 开放** | 🟢 低 | RESTful API |

---

## 三、阶段划分

### 🔴 Phase D：多设备管理（优先级最高）

#### D-1：设备注册与分组
- [ ] 设备注册表（SQLite）
- [ ] 设备分组（按类型/位置/项目）
- [ ] 设备标签系统
- [ ] 设备状态缓存

**复用 Relay 能力**：
- Relay Server 已有 `devices` 表 + API v2
- nastool 通过 `--target relay://` 复用

**CLI 扩展**：
```bash
nastool device list                    # 列出所有设备
nastool device add <host> --group prod # 添加设备到分组
nastool device tag <id> --tag rk3588   # 打标签
```

**预估工时**：3-4 小时

#### D-2：批量检测
- [ ] 多设备并发检测
- [ ] 检测任务队列
- [ ] 进度跟踪与报告聚合
- [ ] 异常设备自动标记

**复用 Relay 能力**：
- Relay API v2 已有 `/api/v2/agents/batch/commands`
- nastool 封装批量检测

**CLI 扩展**：
```bash
nastool --batch @devices.txt           # 批量检测
nastool --batch @prod --parallel 4     # 并发数限制
nastool --batch @all --output reports/ # 输出到目录
```

**预估工时**：4-5 小时

#### D-3：对比分析
- [ ] 设备间对比（同型号/同配置）
- [ ] 历史对比（同一设备不同时间）
- [ ] 差异高亮与排名
- [ ] 基线对比（vs 理想状态）

**CLI 扩展**：
```bash
nastool compare <id1> <id2>            # 两设备对比
nastool compare <id> --history 7d      # 历史对比（7天）
nastool baseline <id> --ideal          # vs 理想基线
```

**预估工时**：4-5 小时

---

### 🟡 Phase E：实时与历史

#### E-1：WebSocket 实时推送
- [ ] WebSocket 客户端集成（复用 Relay）
- [ ] 设备状态实时更新
- [ ] 检测进度实时推送
- [ ] 告警实时通知

**复用 Relay 能力**：
- Relay Server 已有 `ws_handler.js`（协议 v2.0）
- nastool 需实现 WebSocket 客户端

**消息类型**：
```
server:device_update  → 设备状态更新
server:alert          → 告警通知
server:progress       → 检测进度
```

**预估工时**：4-5 小时

#### E-2：历史数据存储
- [ ] SQLite 本地存储设计
- [ ] 检测结果持久化
- [ ] 历史趋势查询 API
- [ ] 数据导出（CSV/JSON）

**数据库设计**：
```sql
CREATE TABLE diagnosis_history (
    id INTEGER PRIMARY KEY,
    device_id TEXT,
    timestamp DATETIME,
    score INTEGER,
    critical_count INTEGER,
    warning_count INTEGER,
    report_json TEXT
);

CREATE INDEX idx_device_time ON diagnosis_history(device_id, timestamp);
```

**预估工时**：3-4 小时

#### E-3：Web Dashboard 集成
- [ ] 复用 Relay Web Dashboard
- [ ] 添加诊断报告页面
- [ ] 添加趋势分析图表
- [ ] 添加对比分析页面

**复用 Relay 能力**：
- Relay 已有 `web_dashboard/`（Vue3 + Tailwind）
- 扩展诊断相关页面

**预估工时**：6-8 小时

---

### 🟢 Phase F：生态扩展

#### F-1：插件系统
- [ ] 插件接口定义
- [ ] 插件加载机制（Python entry_points）
- [ ] 插件市场（本地）
- [ ] 示例插件（自定义检测项）

**插件接口**：
```python
class NastoolPlugin:
    name: str
    version: str
    def register_checks(self) -> List[CheckFunc]:
        ...
    def register_adapters(self) -> List[Adapter]:
        ...
```

**预估工时**：6-8 小时

#### F-2：API 开放
- [ ] RESTful API 设计
- [ ] API 认证（复用 Relay API Key）
- [ ] API 文档（OpenAPI/Swagger）
- [ ] SDK 封装（Python）

**复用 Relay 能力**：
- Relay 已有 API v2 + API Key 认证
- nastool 添加 `/api/v2/diagnosis/*` 端点

**预估工时**：4-5 小时

---

## 四、交付检查清单

```
🔴 Phase D - 多设备管理（11-14 小时）
□ D-1: 设备注册与分组
□ D-2: 批量检测
□ D-3: 对比分析

🟡 Phase E - 实时与历史（13-17 小时）
□ E-1: WebSocket 实时推送
□ E-2: 历史数据存储
□ E-3: Web Dashboard 集成

🟢 Phase F - 生态扩展（10-13 小时）
□ F-1: 插件系统
□ F-2: API 开放
```

**总预估工时**：34-44 小时（约 5-6 个工作日）

---

## 五、方案选择

### 方案 A：完整版（6 周）
- Phase D + E + F 全部实现
- 适合：作为独立产品运营

### 方案 B：核心版（4 周）
- Phase D + E（跳过 F）
- 适合：内部运维工具

### 方案 C：快速版（2 周）
- Phase D（跳过 E + F）
- 适合：快速验证多设备管理

### 推荐：方案 B（核心版）

**理由**：
1. Phase D（多设备）是核心能力
2. Phase E（实时）复用 Relay，成本低
3. Phase F（生态）可延后

---

## 六、技术选型

| 模块 | 技术选型 | 说明 |
|------|---------|------|
| 数据库 | SQLite | 轻量级，无需部署 |
| WebSocket | 复用 Relay ws_handler.js | 协议 v2.0 已定义 |
| Web Dashboard | 复用 Relay web_dashboard | Vue3 + Tailwind |
| 批量操作 | 复用 Relay API v2 | 已有批量命令/部署 |
| 插件 | Python entry_points | 标准机制 |

---

## 七、与 Relay Server 融合

### 融合架构

```
┌─────────────────────────────────────────────────────────────┐
│                    nastool v3.0                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ 批量检测    │  │ 对比分析    │  │ WebSocket 客户端    │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          └────────────────┴────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  REST API   │
                    │  WebSocket  │
                    └──────┬──────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Relay Server (ECS)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  API v2     │  │  WebSocket  │  │  Web Dashboard      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 融合点

| 能力 | Relay 状态 | nastool v3.0 |
|------|-----------|--------------|
| WebSocket | ✅ 已实现 | 客户端集成 |
| API v2 | ✅ 已实现 | 复用批量端点 |
| Web Dashboard | ✅ 已实现 | 扩展诊断页面 |
| API Key | ✅ 已实现 | 复用认证 |

---

## 八、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 多设备并发 | 中 | 异步检测，限制并发数 |
| Relay 融合复杂度 | 中 | 复用已有协议，减少新开发 |
| 历史数据膨胀 | 低 | 定期清理 + 压缩 |

---

## 九、下一步

1. **确认方案选择**（推荐方案 B）
2. **Phase D 启动**（多设备管理）
3. **Relay 融合验证**（API v2 + WebSocket）

---

## 十、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-04-19 | 初始版本，6模块架构，mock模式 |
| v2.0.0 | 2026-04-19 | RK3588/RK3568 核心 + 远程检测 + 调优 |
| v3.0.0 | - | 多设备管理 + 实时协同（规划中）|

---

_创建于 2026-04-19 12:00 GMT+8_
_更新于 2026-04-19 12:20 GMT+8（移除 AI 诊断，聚焦多设备管理）_
