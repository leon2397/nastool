# nastool Roadmap

> 🍓 ARM device diagnostic toolkit roadmap

---

## ⚠️ 开发铁律（最高优先级）

> **测试与调试分离原则**
>
> 1. **真实测试时，遇到 BUG → 先记录到 CHANGELOG.md 的「已知问题」栏，不当场修改**
> 2. 测试阶段结束后，统一安排时间集中处理记录下来的 BUG
> 3. 禁止在测试过程中修改代码，防止：引入新问题、破坏测试上下文、打断测试节奏
> 4. 例外：致命崩溃（数据丢失、安全漏洞）→ 立即修复但记录原因
>
> **目的**：保持测试的完整性，避免修 A 引 B，确保每个版本发布前都有干净的测试报告。

---

## Current Version: v7.0

**Release Date**: 2026-04-15
**Next**: v8.0（打包发布 + 真机验证）

---

## v5.1.0 (Planned)

### P0 — 智能修复增强
| Feature | Status |
|---------|--------|
| 报告中标注「需人工处理」分类 | ⬜ |
| fix 自动化安全审计 | ⬜ |
| config_ups_shutdown bool bug 修复 | ⬜ |

### P1 — 清理技术债
| Feature | Status |
|---------|--------|
| 清理 `core/` 死代码（5 个 `_health.py`）| ⬜ |
| 统一版本号（constants.py / docstring / MEMO）| ⬜ |
| 添加 VERSION.txt | ⬜ |
| 更新 reporters/health_dashboard.py 过时注释 | ⬜ |

### P2 — 质量提升
| Feature | Status |
|---------|--------|
| 单元测试覆盖率 40% → 80% | ⬜ |
| CI/CD 集成 | ⬜ |

### P3 — 功能扩展
| Feature | Status |
|---------|--------|
| 邮件告警（SMTP）| ⬜ |
| Webhook 告警 | ⬜ |
| PDF 报告 | ✅ v7.0 完成 |

---

## v6.0.0 ✅ 已完成（见 v6.0-hwjet）

Fleet Management: 多设备仪表盘、集中配置推送、健康历史、告警聚合。

---

## v7.0.0 ✅ 已完成（2026-04-15）

多平台适配：Rockchip / SOPHON / 昇腾 / Jetson
产品化：PDF+Logo / 健康权重配置 / 修复引擎 v2.0
Relay Server：API Key + RBAC 鉴权体系

---

## v8.0.0 (Next)

- 打包发布 nastools-v7.0.zip
- 真机验证（昇腾 + Jetson）
- GUI 产品化（PyInstaller）

---

## Completed

| Version | Date | Highlights |
|---------|------|-----------|
| **v7.0** | 2026-04-15 | 多平台适配：Rockchip/SOPHON；修复引擎 v2.0；权重配置化；PDF+Logo；Relay Server RBAC |
| **v6.0-hwjet** | 2026-04-15 | 昇腾+Jetson 双平台诊断，20款设备，38测试通过 |
| **v5.0.4** | 2026-04-15 | 智能修复推荐系统（交互式 fix UI）|
| **v5.0.3** | 2026-04-15 | USB 连接检测模块（+4 checks）|
| **v5.0.2** | 2026-04-14 | 健康评分 v2 + 术语翻译 + 86项检测 |
| **v5.0.1** | 2026-04-14 | 修复扩容 5→15 + 设备覆盖 51款 |
| **v5.0.0** | 2026-04-14 | 架构升级：checks/ 模块化 |
| v3.0.7 | 2026-04-12 | NAS 适配器体系（群晖/威联通）|
| v3.0.6 | 2026-04-12 | 智能摘要 + 好用优先 |
| v3.0.5 | 2026-04-12 | 稳定性保护（safe_import/timeout）|
| v3.0.4 | 2026-04-12 | 进度条 + 导出 + 快速诊断 |
| v3.0.3 | 2026-04-12 | constants + exceptions 统一 |
| v3.0.2 | 2026-04-12 | 类型注解 + mypy |
| v3.0.1 | 2026-04-12 | config + logger + i18n |
| v3.0.0 | 2026-04-12 | profiles + daemon + web + API |
| v2.0.0 | 2026-04-12 | 28 checks + 4 fixes |
| v1.0.0 | 2026-04-10 | 基础诊断 + ARM 检测 |

---

## nastools v2.0 — 跨网远程管理

> Relay Server + ARM Agent，跨 NAT 远程管理 ARM NAS

### Phase 完成状态

```
Phase 4-1 ✅ 基础设施（Relay Server，Node.js + Fastify + sql.js）
Phase 4-2 ✅ 双模式连接 + GUI 集成
Phase 4-3 ✅ 远程操作（命令/文件/升级）
Phase 4-4 ✅ 多设备管理 UI
Phase 4-5 ✅ 批量部署
Phase 4-6 ✅ 报告导出 + 趋势图
─────────────────────────────────────────
nastools v2.0.0 ✅ Release (2026-04-14)
```

**架构**：
```
nastools GUI ←──WS──→ Relay Server (ECS:18888) ←──WS──→ ARM Agent (NAS)
                          ↕ REST API
                    SQLite DB
```
