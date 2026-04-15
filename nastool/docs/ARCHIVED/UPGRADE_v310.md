# nastool v3.1.0 升级计划

## 核心目标

**AI 加速专项优化 + 告警通知系统**

---

## 背景

v3.0.7 完成了 NAS 适配层建设，v3.1.0 将聚焦：
1. AI 加速器性能调优（RKNPU / TensorRT / TVM）
2. 多渠道告警通知（邮件 / Webhook / Slack / 短信）
3. 增强报告能力（PDF / 定时报告 / 对比报告）
4. 代码质量提升（测试覆盖 / API 文档 / 集成测试）

---

## 升级任务清单

### P0 - AI 加速专项（3天工作量）

#### P0.1 RKNN 优化适配器
**目标**：Rockchip RK3588 NPU 推理性能调优

**文件**：`adapters/rockchip_rknn.py`（新建）

**功能**：
- RKNN SDK 版本检测（rknn-toolkit2）
- NPU 利用率监控（`cat /sys/class/devfreq/devfreq0/load`）
- 内存带宽检测
- 推理性能基准测试（ResNet50 / MobileNetV2）
- 功耗监控（`power_measure.sh`）

**RKNN 版本数据库**：
| 芯片 | 推荐 RKNN 版本 | 驱动版本 |
|------|---------------|----------|
| RK3588 | 2.0.0+ | 1.5.0+ |
| RK3588S | 2.0.0+ | 1.5.0+ |
| RK3576 | 2.1.0+ | 1.6.0+ |

**工时**：8小时

---

#### P0.2 TensorRT 调优适配器
**目标**：NVIDIA Jetson GPU 推理性能优化

**文件**：`adapters/nvidia_tensorrt.py`（新建）

**功能**：
- TensorRT 版本检测
- GPU 利用率 + 显存监控（`tegrastats`）
- INT8/FP16/FP32 精度建议
- Jetson_clocks 建议
- 推理性能基准测试

**工时**：6小时

---

#### P0.3 TVM 集成
**目标**：Apache TVM 跨平台深度学习编译器支持

**文件**：`adapters/tvm_backend.py`（新建）

**功能**：
- TVM 安装检测
- AutoTVM / AutoScheduler 配置
- 跨平台模型编译建议
- 性能对比报告

**工时**：6小时

---

### P1 - 告警通知系统（2天工作量）

#### P1.1 邮件告警
**目标**：SMTP 邮件通知

**文件**：`notifiers/email_notifier.py`（新建）

**功能**：
- SMTP 配置（TLS/SSL）
- 告警模板（critical / warning / info）
- 告警去重（同一问题 1 小时内不重复发送）
- 收件人分组（管理员 / 运维 / 开发）

**工时**：6小时

---

#### P1.2 Webhook 告警
**目标**：通用 HTTP Webhook

**文件**：`notifiers/webhook_notifier.py`（新建）

**功能**：
- POST JSON 格式告警
- 自定义 Header（Authorization / X-Signature）
- 重试机制（3次，指数退避）
- HMAC 签名验证

**工时**：4小时

---

#### P1.3 Slack/Discord 频道
**目标**：即时通讯平台告警

**文件**：`notifiers/slack_notifier.py`（新建）

**工时**：4小时

---

#### P1.4 短信告警
**目标**：Twilio / 阿里云短信

**文件**：`notifiers/sms_notifier.py`（新建）

**工时**：4小时

---

### P1 - 增强报告（1天工作量）

#### P1.5 PDF 报告生成
**目标**：格式化 PDF 报告

**文件**：`reporters/pdf_reporter.py`（新建）

**依赖**：`reportlab` 或 `weasyprint`

**内容**：
- 封面（设备名 / 日期 / 健康评分）
- 执行摘要
- 详细检查结果（表格）
- 问题修复建议
- 趋势图表

**工时**：8小时

---

#### P1.6 定时报告
**目标**：每日/每周自动生成并发送报告

**文件**：`schedulers/report_scheduler.py`（新建）

**功能**：
- Cron 表达式配置
- 报告生成 + 发送一体化
- 报告历史归档

**工时**：4小时

---

#### P1.7 对比报告
**目标**：修复前/修复后健康分对比

**文件**：`reporters/comparison_reporter.py`（新建）

**功能**：
- 读取历史记录
- 生成变化趋势
- 突出改进项

**工时**：4小时

---

### P2 - 代码质量（2天工作量）

#### P2.1 单元测试增强
**目标**：测试覆盖率从 40% → 80%

**工时**：12小时

**当前覆盖**：
- constants.py ✅
- exceptions.py ✅
- core/ ✅
- device.py ✅
- network.py ✅
- storage.py ✅

**需增加**：
- checks/ 所有检查项
- fixes/ 所有修复项
- adapters/ 所有适配器
- reporters/ 所有报告格式
- utils/ 核心工具

---

#### P2.2 API 文档
**目标**：OpenAPI 3.0 / Swagger 文档

**工时**：4小时

---

#### P2.3 集成测试
**目标**：GitHub Actions CI/CD

**工时**：6小时

---

## 文件结构规划

```
nastool/
├── adapters/
│   ├── rockchip_rknn.py    # 新建 - RKNN 优化
│   ├── nvidia_tensorrt.py  # 新建 - TensorRT 调优
│   └── tvm_backend.py       # 新建 - TVM 集成
│
├── notifiers/               # 新建 - 告警通知系统
│   ├── __init__.py
│   ├── base.py              # 抽象基类
│   ├── email_notifier.py    # 邮件
│   ├── webhook_notifier.py  # Webhook
│   ├── slack_notifier.py    # Slack
│   └── sms_notifier.py      # 短信
│
├── schedulers/              # 新建 - 定时任务
│   ├── __init__.py
│   └── report_scheduler.py  # 定时报告
│
├── reporters/
│   ├── pdf_reporter.py     # 新建 - PDF 报告
│   └── comparison_reporter.py  # 新建 - 对比报告
│
└── arm_diagnose.py         # 集成新功能
```

---

## 优先级与工时汇总

| 优先级 | 任务 | 工时 | 价值 |
|--------|------|------|------|
| P0.1 | RKNN 优化适配器 | 8h | ⭐⭐⭐⭐⭐ |
| P0.2 | TensorRT 调优适配器 | 6h | ⭐⭐⭐⭐ |
| P0.3 | TVM 集成 | 6h | ⭐⭐⭐ |
| P1.1 | 邮件告警 | 6h | ⭐⭐⭐⭐⭐ |
| P1.2 | Webhook 告警 | 4h | ⭐⭐⭐⭐ |
| P1.3 | Slack/Discord | 4h | ⭐⭐⭐ |
| P1.4 | 短信告警 | 4h | ⭐⭐ |
| P1.5 | PDF 报告 | 8h | ⭐⭐⭐⭐⭐ |
| P1.6 | 定时报告 | 4h | ⭐⭐⭐ |
| P1.7 | 对比报告 | 4h | ⭐⭐⭐ |
| P2.1 | 单元测试增强 | 12h | ⭐⭐⭐⭐ |
| P2.2 | API 文档 | 4h | ⭐⭐⭐ |
| P2.3 | CI/CD 集成测试 | 6h | ⭐⭐⭐⭐ |

**总计**：76 小时（约 9.5 个工作日）

---

## 里程碑

### Milestone 1 - AI 加速专项（Day 1-3）
- [ ] P0.1 RKNN 适配器
- [ ] P0.2 TensorRT 适配器
- [ ] P0.3 TVM 集成

**交付物**：AI 加速器性能优化建议 + 基准测试

---

### Milestone 2 - 告警通知（Day 4-5）
- [ ] P1.1 邮件告警
- [ ] P1.2 Webhook 告警
- [ ] P1.3 Slack/Discord
- [ ] P1.4 短信告警

**交付物**：多渠道告警系统

---

### Milestone 3 - 增强报告（Day 6-7）
- [ ] P1.5 PDF 报告
- [ ] P1.6 定时报告
- [ ] P1.7 对比报告

**交付物**：完整报告体系

---

### Milestone 4 - 质量提升（Day 8-9）
- [ ] P2.1 单元测试
- [ ] P2.2 API 文档
- [ ] P2.3 CI/CD

**交付物**：可维护性保障

---

## 商业化路径

### 阶段 1 - v3.1.0 免费功能（Month 1）
- Webhook 告警免费开放
- 推动用户接入自有告警系统

### 阶段 2 - v3.2.0 增值服务（Month 2-3）
- 邮件告警 + 定时报告（Pro 版本，$4.99/月）
- 企业版（无限设备 + 多渠道告警，$19.99/月）

### 阶段 3 - 生态建设（Month 4-6）
- 开放 notifier 插件 API
- 社区贡献告警渠道
- Grafana / Prometheus 集成

---

## 配置示例

### config.yaml 告警配置
```yaml
notifiers:
  email:
    enabled: true
    smtp_host: smtp.gmail.com
    smtp_port: 587
    smtp_user: alerts@example.com
    smtp_password: ${SMTP_PASSWORD}
    use_tls: true
    recipients:
      - admin@example.com
      - ops@example.com
    dedup_hours: 1

  webhook:
    enabled: true
    url: https://your-webhook-endpoint.com/alerts
    method: POST
    headers:
      Authorization: "Bearer ${WEBHOOK_TOKEN}"
      X-Signature: "${WEBHOOK_SIGNATURE}"
    retries: 3

  slack:
    enabled: false
    webhook_url: ${SLACK_WEBHOOK_URL}
    channel: "#alerts"

  sms:
    enabled: false
    provider: twilio
    account_sid: ${TWILIO_ACCOUNT_SID}
    auth_token: ${TWILIO_AUTH_TOKEN}
    from_number: "+1234567890"
    recipients:
      - "+0987654321"
```

### CLI 新增命令
```bash
# 测试告警
python3 arm_diagnose.py --test-notifier email
python3 arm_diagnose.py --test-notifier webhook

# 查看告警历史
python3 arm_diagnose.py --alert-history --days 7

# 定时报告
python3 arm_diagnose.py --schedule-report daily --time "09:00"
python3 arm_diagnose.py --schedule-report weekly --time "09:00" --day monday

# AI 加速基准测试
python3 arm_diagnose.py --ai-benchmark --adapter rknn
python3 arm_diagnose.py --ai-benchmark --adapter tensorrt
python3 arm_diagnose.py --ai-benchmark --adapter tvm
```

---

## 下一步行动

1. **确认优先级**：用户确认是否按此计划执行
2. **Milestone 1**：从 P0.1 RKNN 适配器开始
3. **同步 delivery 包**：v3.1.0 完成后同步 nastool-delivery

---

**计划制定时间**：2026-04-12
**预计完成时间**：2026-04-21
**版本目标**：v3.1.0
