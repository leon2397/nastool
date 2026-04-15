# nastool hw-jet v6.0 产品计划

> 文档版本：1.0  
> 制定日期：2026-04-15  
> 负责人：桔子2  
> 版本代号：hw-jet（华为 Huawei + Jetson）

---

## 一、产品定位

### 1.1 核心定位

**hw-jet = 华为昇腾 + Jetson 双平台 AI 边缘诊断专业版**

一款工具，覆盖两款主流 AI 边缘计算平台（昇腾 + Jetson），自动识别设备型号，一键输出专业级诊断报告。

### 1.2 目标用户

- AI 推理部署工程师
- 机器人开发者
- 边缘计算运维工程师
- 自动驾驶 / 智能摄像头从业者

### 1.3 核心价值

> 插上就能跑，不用指定型号，自动识别华为昇腾或 Jetson，输出专业诊断结论

### 1.4 版本命名

| 项目 | 说明 |
|------|------|
| 版本名 | hw-jet |
| 版本号 | v6.0-hwjet |
| 全称 | nastool hw-jet v6.0 |
| 定位 | 双平台旗舰版 |
| 交付形式 | pip install nastool + 一键安装脚本 |
| 真机验证 | ✅ 昇腾设备可用 + ✅ Jetson Xavier NX 可用 |

---

## 二、设备覆盖

### 2.1 华为昇腾（4类，覆盖10款）

| 类别 | 包含型号 | 定位 | 检测逻辑 |
|------|---------|------|---------|
| **Atlas 200系** | Atlas 200I A2 / 200DK A2 / 200 (一代) | 嵌入式旗舰 | 同一套 |
| **Atlas 300系** | Atlas 300I Pro / 300I Duo / 300V 寿光卡 / 300I 寿光卡 | 推理卡 | 同一套 |
| **Atlas 500系** | Atlas 500 A2 | 边缘小站 | 同一套 |
| **Atlas A2 Lite系** | Atlas A2 智能小站 / A2 边缘计算网关 | 新代际Lite | 同一套 |

**昇腾工具链检测范围**：npu-smi / CANN / ACL / MindSpore / TF-Ascend / PyTorch-Ascend / ONNX

### 2.2 Jetson（6类，覆盖10款）

| 类别 | 包含型号 | GPU架构 | 检测逻辑 |
|------|---------|---------|---------|
| **Orin AGX** | Orin AGX 64GB / 32GB | Ada | 同一套 |
| **Orin NX** | Orin NX 16GB / 8GB | Ada | 同一套 |
| **Orin Nano** | Orin Nano 8GB / 4GB | Ada | 同一套 |
| **AGX Xavier** | AGX Xavier 64GB / 32GB | Volta | 同一套 |
| **Xavier NX** | Xavier NX（唯一）| Volta | 同一套 |
| **Nano/TX2** | Nano 4GB / TX2 | Maxwell/Pascal | 同一套（老架构）|

**Jetson工具链检测范围**：tegrastats / JetPack / CUDA / cuDNN / TensorRT / ONNX Runtime

### 2.3 覆盖总览

```
hw-jet v6.0 覆盖设备
├── 昇腾 4类 × 10款
│   ├── Atlas 200系（嵌入式模组/开发板）
│   ├── Atlas 300系（PCIe推理卡）
│   ├── Atlas 500系（边缘小站）
│   └── Atlas A2 Lite系（新代际边缘）
└── Jetson 6类 × 10款
    ├── Orin AGX（Ada旗舰）
    ├── Orin NX（Ada高端）
    ├── Orin Nano（Ada入门）
    ├── AGX Xavier（Volta旗舰）
    ├── Xavier NX（Volta主流）
    └── Nano/TX2（Maxwell/Pascal入门）
```

---

## 三、功能矩阵

### 3.1 昇腾专项检测

| 检测项 | Atlas 200系 | Atlas 300系 | Atlas 500系 | Atlas A2 Lite系 |
|--------|:-----------:|:-----------:|:-----------:|:--------------:|
| npu-smi 解析 | ✅ | ✅ | ✅ | ✅ |
| CANN 版本探测 | ✅ | ✅ | ✅ | ✅ |
| ACL 运行时 | ✅ | ✅ | ✅ | ✅ |
| MindSpore 版本 | ✅ | ✅ | ✅ | ✅ |
| TF-Ascend / PyTorch-Ascend | ✅ | ✅ | ✅ | ✅ |
| NPU 推理基准（MobileNetV2）| ✅ | ✅ | ✅ | ✅ |
| NPU 利用率 | ✅ | ✅ | ✅ | ✅ |
| NPU 内存 | ✅ | ✅ | ✅ | ✅ |
| NPU 温度 | ✅ | ✅ | ✅ | ✅ |
| NPU 功耗 | ✅ | ✅ | ✅ | ✅ |
| CANN 工具链完整度 | ✅ | ✅ | ✅ | ✅ |

### 3.2 Jetson 专项检测

| 检测项 | Orin AGX | Orin NX | Orin Nano | AGX Xavier | Xavier NX | Nano/TX2 |
|--------|:--------:|:--------:|:---------:|:----------:|:---------:|:--------:|
| tegrastats 解析 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| JetPack 版本 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CUDA 版本 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| cuDNN 版本 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| TensorRT 版本 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ONNX Runtime | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GPU 推理基准（MobileNetV2）| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GPU 利用率 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GPU 显存 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 温度（全thermal_zone）| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 电源模式（nvpmodel）| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 3.3 通用检测（昇腾 + Jetson 共享）

| 检测项 | 说明 |
|--------|------|
| 系统资源 | CPU / 内存 / SWAP / 进程数 / inode |
| 存储健康 | SMART / lsblk / 磁盘 IO |
| 网络连通性 | 网口 / IP / 延迟 / DNS |
| Docker | 版本 / 镜像数 / 容器数 / 异常容器 |
| 安全检测 | openssh / 防火墙 / 用户列表 / 固件更新 |
| 包更新 | apt update 可更新数量 |

### 3.4 差异化亮点

| 功能 | 说明 |
|------|------|
| **跨平台推理对比** | 昇腾 NPU vs Jetson GPU，同一 MobileNetV2 模型横向 PK |
| **健康评分** | 百分制，昇腾/Jetson 各自独立基线 |
| **推理性能基线** | 20 款设备的 MobileNetV2 延迟/吞吐数据库 |
| **智能修复建议** | 针对具体型号缺省组件的操作建议 |
| **历史趋势** | SQLite 本地历史记录，/report 查看对比 |

---

## 四、实施计划

### 4.1 总策略

**昇腾优先，Jetson 紧随。交替开发，互相复用。**

- 真机验证：昇腾设备 ✅ + Jetson Xavier NX ✅

### 4.2 详细排期（6周，Day 1-30）

#### 第1周：昇腾核心检测（Day 1-5）

| Day | 任务 | 产出 |
|-----|------|------|
| 1 | 目录搭建 + 昇腾识别引擎 | `adapters/ascend/` 目录骨架，4类设备识别（npu-smi输出/设备树）|
| 2 | npu-smi 解析引擎 | 4类设备的npu-smi输出格式全覆盖，单卡/多卡/不同算力 |
| 3 | CANN + ACL 版本探测 | /usr/local/Ascend/... 多版本路径探测，工具链完整度 |
| 4 | MindSpore + TF-Ascend + PyTorch-Ascend | 推理框架可用性检测，昇腾接入状态 |
| 5 | 昇腾通用检测接入 | 温度/功耗/存储/网络/安全 接入统一检测框架 |

#### 第2周：昇腾推理基准 + Jetson识别框架（Day 6-10）

| Day | 任务 | 产出 |
|-----|------|------|
| 6-7 | ACL 推理基准测试 | MobileNetV2 在昇腾上的延迟/吞吐，4类分别测 |
| 7 | 昇腾健康评分系统 | 百分制，NPU利用率/带宽/温度/功耗 4维度 |
| 8 | Jetson 识别引擎 | 6类设备型号识别，设备树路径（Orin/Xavier/Nano/TX2）|
| 9 | Jetson 检测框架 | tegrastats 解析/GPU监控/温度/电源模式/thermal_zone |
| 10 | Jetson 通用检测接入 | system/storage/network/security 接入统一检测框架 |

#### 第3周：Jetson全系专项（Day 11-15）

| Day | 任务 | 产出 |
|-----|------|------|
| 11 | JetPack / CUDA / cuDNN / TensorRT 检测 | 6类多版本路径探测（JetPack 4.x~6.x）|
| 12 | JetPack 4.x~6.x 兼容性 | 老架构（Nano/TX2）与新架构（Orin/Xavier）差异化检测 |
| 13 | Jetson 推理基准 | MobileNetV2 在6类GPU上的延迟/吞吐，6条基线数据 |
| 14 | Jetson 健康评分 | 百分制，GPU利用率/温度/功耗/推理性能 4维度 |
| 15 | 跨平台推理对比 | 昇腾 NPU vs Jetson GPU，同模型横向 PK 报告 |

#### 第4周：统一报告系统（Day 16-20）

| Day | 任务 | 产出 |
|-----|------|------|
| 16-17 | HTML 报告生成器 | 仪表盘风格，昇腾/Jetson 两套配色+图标，自动识别型号 |
| 18 | Markdown 技术报告导出 | 一键生成，支持分享 |
| 19 | 健康评分白皮书 | 20款设备基线数据文档，评分标准说明 |
| 20 | CLI 完整化 | `--device auto/jetson/ascend/hw` `----full/--fast` `----report` `----json` |

#### 第5周：安装 + 测试 + 真机验证（Day 21-25）

| Day | 任务 | 产出 |
|-----|------|------|
| 21-22 | pip 安装脚本 | 依赖检测 + 昇腾驱动检查 + Jetson JetPack 检查 |
| 23-24 | 单元测试 + 集成测试 | 20款设备 mock 数据，`tests/mock_adapters/` |
| 25 | **昇腾真机验证** | 在真实昇腾设备上验证全量检测 |
| 25 | **Jetson真机验证** | 在 Jetson Xavier NX 上验证全量检测 |

#### 第6周：文档 + 发布（Day 26-30）

| Day | 任务 | 产出 |
|-----|------|------|
| 26-27 | 用户手册 | 安装指南 + 使用教程 + 故障排查 |
| 27-28 | 型号支持矩阵 | 20款设备检测能力对照表（每类一行）|
| 29 | 发布包生成 | `nastool-hwjet-v6.0.tar.gz` + SHA256 |
| 30 | **正式发布** | hw-jet v6.0 双平台旗舰版 |

### 4.3 里程碑

| 里程碑 | 日期 | 验收条件 |
|--------|------|---------|
| M1：昇腾核心完成 | Day 5 | Atlas 4类设备全检测，npu-smi解析正确 |
| M2：Jetson全系完成 | Day 15 | 6类设备全检测，推理基准数据完整 |
| M3：统一报告上线 | Day 20 | HTML报告+评分系统+CLI完整 |
| M4：真机验证完成 | Day 25 | 昇腾+Jetson 双平台实测通过 |
| M5：**正式发布** | Day 30 | 发布包+文档+支持矩阵完整 |

---

## 五、技术架构

### 5.1 目录结构

```
nastool/
├── arm_diagnose.py              # 入口（--device auto/jetson/ascend/hw）
├── adapters/                    # 设备适配层
│   ├── __init__.py             # 适配器注册与加载
│   ├── base.py                 # 适配器基类
│   ├── detector.py             # 设备指纹识别（昇腾+Jetson共用了
│   ├── ascend/                 # ★ 华为昇腾适配器
│   │   ├── __init__.py
│   │   ├── common.py           # 昇腾通用检测（npu-smi/CANN/ACL）
│   │   ├── atlas_200.py        # Atlas 200系（嵌入式）
│   │   ├── atlas_300.py        # Atlas 300系（推理卡）
│   │   ├── atlas_500.py        # Atlas 500系（边缘小站）
│   │   └── atlas_a2_lite.py    # Atlas A2 Lite系
│   └── jetson/                 # ★ Jetson适配器
│       ├── __init__.py
│       ├── common.py           # Jetson通用检测（tegrastats/CUDA）
│       ├── orin_agx.py         # Orin AGX
│       ├── orin_nx.py          # Orin NX
│       ├── orin_nano.py        # Orin Nano
│       ├── agx_xavier.py       # AGX Xavier
│       ├── xavier_nx.py        # Xavier NX
│       └── nano_tx2.py         # Nano / TX2
├── checks/                      # 检测执行层（通用）
│   ├── system/
│   ├── storage/
│   ├── network/
│   ├── security/
│   └── docker/
├── inference/                   # ★ 推理基准测试（昇腾+Jetson共用）
│   ├── __init__.py
│   ├── ascend_benchmark.py      # ACL MobileNetV2 昇腾推理
│   ├── jetson_benchmark.py      # TensorRT MobileNetV2 Jetson推理
│   └── cross_platform.py        # 跨平台对比报告
├── scoring/                     # ★ 健康评分系统
│   ├── __init__.py
│   ├── ascend_scorer.py         # 昇腾评分（4维度）
│   └── jetson_scorer.py         # Jetson评分（4维度）
├── reports/                     # ★ 报告生成器
│   ├── __init__.py
│   ├── html_report.py           # HTML仪表盘
│   └── markdown_report.py       # Markdown技术报告
├── core/
│   ├── safety.py
│   ├── ai_accel.py
│   └── health_scorer.py         # 统一评分入口
├── utils/
│   ├── quick_diagnose.py
│   └── terminology.py
└── tests/
    ├── mock_adapters/           # 20款设备mock数据
    │   ├── ascend/
    │   │   ├── atlas_200.json
    │   │   ├── atlas_300.json
    │   │   ├── atlas_500.json
    │   │   └── atlas_a2_lite.json
    │   └── jetson/
    │       ├── orin_agx.json
    │       ├── orin_nx.json
    │       ├── orin_nano.json
    │       ├── agx_xavier.json
    │       ├── xavier_nx.json
    │       └── nano_tx2.json
    └── test_adapters/
        ├── test_ascend.py
        └── test_jetson.py
```

### 5.2 设备识别流程

```
arm_diagnose.py
    ↓
[自动识别]
    ↓
┌─────────────────────────────────────────┐
│  1. 检查 npu-smi 命令是否存在            │
│     → 存在 → 昇腾设备 → 进入 ascend/    │
│     → 不存在 → 进入 jetson/              │
│                                          │
│  2. 昇腾设备进一步识别型号：              │
│     npu-smi -i all -L                    │
│     → Atlas 200系 / 300系 / 500系 / A2  │
│                                          │
│  3. Jetson 设备进一步识别型号：           │
│     读 /sys/firmware/devicetree/base/model
│     → Orin AGX / Orin NX / Orin Nano / │
│       AGX Xavier / Xavier NX / Nano    │
└─────────────────────────────────────────┘
    ↓
[加载对应适配器]  ← 每个适配器实现自己的专项检测
    ↓
[统一报告输出]
```

---

## 六、真机验证计划

### 6.1 可用真机

| 设备 | 状态 | 验证内容 |
|------|------|---------|
| 华为昇腾（型号待确认）| ✅ 可用 | 全量昇腾检测 + ACL推理基准 |
| Jetson Xavier NX | ✅ 可用 | 全量Jetson检测 + TensorRT推理基准 |

### 6.2 验证清单

**昇腾验证**：
- [ ] npu-smi 正确识别型号
- [ ] CANN 版本读取正确
- [ ] MindSpore / TF-Ascend / PyTorch-Ascend 检测正常
- [ ] NPU 推理基准测试跑通（MobileNetV2）
- [ ] 健康评分正常输出

**Jetson 验证**：
- [ ] 设备树正确识别 Xavier NX
- [ ] tegrastats 实时解析正确
- [ ] CUDA / TensorRT 版本正确
- [ ] GPU 推理基准测试跑通（MobileNetV2）
- [ ] 健康评分正常输出

---

## 七、交付物清单

| 产出 | 说明 | 目标日期 |
|------|------|---------|
| hw-jet v6.0 安装包 | `nastool-hwjet-v6.0.tar.gz` | Day 30 |
| pip 安装包 | `nastool-hwjet-v6.0-py3-none-any.whl` | Day 30 |
| HTML 诊断报告 | 仪表盘，自动识别昇腾/Jetson型号 | Day 20 |
| 推理性能对比报告 | 昇腾 vs Jetson，MobileNetV2 横向 PK | Day 15 |
| 健康评分白皮书 | 20款设备基线数据文档 | Day 19 |
| 用户手册 | 安装指南 + 使用教程 + 故障排查 | Day 27 |
| 型号支持矩阵 | 20款设备检测能力对照表 | Day 28 |
| 真机验证报告 | 昇腾 + Jetson 双平台实测记录 | Day 25 |

---

## 八、技术风险与预案

| 风险 | 概率 | 影响 | 预案 |
|------|------|------|------|
| 昇腾工具链版本差异大 | 高 | 中 | 多版本路径探测，graceful fallback |
| 昇腾推理框架未安装 | 中 | 低 | 推理基准跳过，显示 WARNING 不崩溃 |
| Jetson 老架构（Nano/TX2）缺少工具 | 中 | 中 | graceful fallback，兼容旧版 tegrastats |
| 昇腾真机型号与预期不符 | 低 | 中 | 根据实际型号调整适配器，mock 数据兜底 |
| JetPack 4.x 兼容性 | 低 | 中 | Nano/TX2 使用老版 tegrastats 格式 |
| 发布延期 | 中 | 中 | 按优先级分批交付（M1→M2→M3→M5）|

---

## 九、里程碑回顾

| 里程碑 | 目标日期 | 状态 |
|--------|---------|------|
| M1：昇腾核心完成 | Day 5 | ⏳ 待开始 |
| M2：Jetson全系完成 | Day 15 | ⏳ 待开始 |
| M3：统一报告上线 | Day 20 | ⏳ 待开始 |
| M4：真机验证完成 | Day 25 | ⏳ 待开始 |
| M5：正式发布 | Day 30 | ⏳ 待开始 |

---

*本文档为 nastool hw-jet v6.0 正式计划，按此执行。*
