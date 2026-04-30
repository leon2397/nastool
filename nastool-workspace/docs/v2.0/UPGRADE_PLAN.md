# NASTool v2.0 升级计划（RK3588/RK3568 重点版）

> 创建时间：2026-04-19
> 版本目标：v2.0
> 项目目录：`C:\tools416\`
> 重点方向：Rockchip RK3588/RK3568 设备检测与诊断

---

## 一、目标

**Rockchip RK3588/RK3568 设备检测与诊断能力增强**，构建完整的端侧 AI 设备诊断工具链。

---

## 二、阶段划分

### 🔴 Phase A：RK3588/RK3568 核心能力增强（优先级最高）

#### A-1：完善 RK3588 检测项
- [ ] 添加 RK3588 NPU 利用率检测（`/sys/class/rknpu*/utilization`）
- [ ] 添加 NPU 内存使用检测
- [ ] 添加 RK3588 特有的 MP4/MPS 状态检测

#### A-2：添加 RK3568 专项支持
- [ ] 创建 RK3568 专用检测（对比 RK3588 差异）
- [ ] RK3568 NPU 频率表（vs RK3588）
- [ ] RK3568 视频编解码能力差异

#### A-3：RKNN 推理基准测试
- [ ] 集成 rknn-benchmark（RK3588 专用）
- [ ] 添加 MobileNet/ResNet 推理测试
- [ ] 性能评分系统（对比 Jetson Nano）

#### A-4：驱动与固件检测
- [ ] rknn-toolkit2 版本检测
- [ ] rknn-runtime 版本检测
- [ ] rockchip 驱动版本检测

---

### 🟡 Phase B：连接与远程能力

#### B-1：HTTP API 远程检测
- [x] 创建 HTTP 后端适配器（参考 nas_client.py）
- [x] 支持远程 RK 设备检测结果上传
- [x] CLI `--target` 参数

#### B-2：Relay Server 集成
- [x] 通过 relay_server 中继 RK 设备检测
- [x] 实现跨网段设备发现
- [ ] WebSocket 实时状态推送（v2.1 规划）

---

### 🟢 Phase C：工具链与生态

#### C-1：性能调优建议
- [x] 基于检测结果给出调优建议
- [x] CPU/DDR/NPU 频率自动推荐
- [x] 散热方案建议

#### C-2：报告增强
- [x] 生成 RK 专用诊断报告
- [x] 对比历史数据（趋势分析）
- [x] JSON/Markdown/纯文本多格式输出

---

## 三、交付检查清单

```
🔴 Phase A - 核心能力（6-8 小时）
✅ A-1: RK3588 NPU 利用率/内存检测
✅ A-2: RK3568 专项支持
✅ A-3: RKNN 推理基准测试
✅ A-4: 驱动与固件检测

🟡 Phase B - 连接能力（4-6 小时）
✅ B-1: HTTP API 远程检测
✅ B-2: Relay Server 集成

🟢 Phase C - 生态增强（3-4 小时）
✅ C-1: 性能调优建议
✅ C-2: 报告增强
```

---

## 四、关键差异化（vs Jetson）

| 特性 | Jetson (NVIDIA) | RK3588/RK3568 |
|------|-----------------|---------------|
| NPU 驱动 | nvidia-smi | /dev/rknpu |
| SDK | TensorRT | RKNN Toolkit2 |
| 推理框架 | TensorRT/ONNX | RKNN/ONNX |
| 视频编解码 | NVENC/NVDEC | V4L2 |
| 存储 | eMMC/SD | eMMC/SD/NVMe |
| 参考文档 | 丰富 | 较少 |

---

## 五、现有资源

### 已有适配器和检测项

| 类型 | 数量 | 具体内容 |
|------|------|----------|
| **适配器** | 1 | `rockchip.py` - RK3588/RK356x 专项适配 |
| **检测项** | 4+ | `gpu_detected.py` (rknpu), `version_checker.py` (rknn_version), 等 |
| **Benchmark** | 1 | `benchmark.py` - 支持 ONNX/TensorRT/ACL/MindSpore |

### 当前 RK 检测能力

| 检查项 | 位置 | 状态 |
|--------|------|------|
| `/dev/rknpu` 节点检测 | rockchip.py | ✅ 已实现 |
| NPU 固件版本 | rockchip.py | ✅ 已实现 |
| RKNN SDK 版本 | version_checker.py | ✅ 已实现 |
| RKNN Runtime | version_checker.py | ✅ 已实现 |
| DDR 带宽/频率 | rockchip.py | ✅ 已实现 |
| GPU 状态/频率 | rockchip.py | ✅ 已实现 |
| V4L2 视频编解码 | rockchip.py | ✅ 已实现 |
| 温度监控 | rockchip.py | ✅ 已实现 |

---

## 六、工作量估算

| 阶段 | 工作量 | 说明 |
|------|--------|------|
| Phase A | 6-8 小时 | 核心检测能力增强 |
| Phase B | 4-6 小时 | 远程连接能力 |
| Phase C | 3-4 小时 | 工具链与生态 |
| **总计** | **13-18 小时** | v2.0 完整功能 |

---

## 七、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-04-19 | 初始版本，6模块架构，mock模式 |
| v2.0.0 | - | RK3588/RK3568 核心增强（规划中） |