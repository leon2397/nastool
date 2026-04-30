

---

## NASTool v2.0 升级计划（2026-04-19 启动）

> 目标：Rockchip RK3588/RK3568 设备检测与诊断能力增强

### 阶段进度

| 阶段 | 任务 | 状态 | 交付物 |
|------|------|------|--------|
| Phase A | RK3588/RK3568 核心能力增强 | 进行中 | 增强的检测项 |
| Phase B | 连接与远程能力 | 待开始 | HTTP 适配器 + CLI --target |
| Phase C | 工具链与生态 | 待开始 | 调优建议 + 报告增强 |

### Phase A 详细任务

- [ ] A-1: RK3588 NPU 利用率/内存检测
- [ ] A-2: RK3568 专项支持
- [ ] A-3: RKNN 推理基准测试
- [ ] A-4: 驱动与固件检测

### 关键差异化

| 特性 | Jetson (NVIDIA) | RK3588/RK3568 |
|------|-----------------|---------------|
| NPU 驱动 | nvidia-smi | /dev/rknpu |
| SDK | TensorRT | RKNN Toolkit2 |
| 推理框架 | TensorRT/ONNX | RKNN/ONNX |

### 文档位置

- 详细计划：nastool-workspace/docs/v2.0/UPGRADE_PLAN.md
