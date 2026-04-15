# nastool v3.0.7 升级计划

## 核心目标

**适配 ARM 架构 NAS 管理系统** — 让 nastool 成为 ARM NAS 设备的通用诊断工具

---

## 背景

### 当前问题
- nastool 主要为 AI-NAS（ARM 设备）设计
- `--register` 只支持 AI-NAS 后端
- 其他 ARM NAS 用户无法利用诊断能力
- 商业化受限（群晖 ARM 机型 200万+ 用户）

### ARM NAS 市场分析
| NAS 系统 | ARM 机型 | ARM 用户基数 | 优先级 |
|----------|----------|--------------|--------|
| 群晖 Synology | J系列、部分 DS系列 | 200万+ | ⭐⭐⭐⭐⭐ |
| 威联通 QNAP | TS-231P3、TS-431KX | 80万+ | ⭐⭐⭐⭐ |
| 海康威视 | Mage系列 | 15万+ | ⭐⭐ |
| 华硕 ASUSTOR | AS11系列 | 5万+ | ⭐⭐ |

**说明**：
- 群晖 J 系列（J1010J、J4125 等）使用 Realtek ARM 芯片
- 威联通 TS-231P3 等使用 Annapurna Labs ARM 芯片
- 这些 ARM NAS 用户是 nastool 的核心目标市场

---

## 升级任务清单

### P0 - 核心适配层（3天工作量）

#### P0.1 抽象 NAS 后端接口
**目标**：统一的 NAS 后端适配接口

**文件**：`adapters/base.py`

```python
class NASBackend(ABC):
    """NAS 后端抽象基类"""
    
    @abstractmethod
    def register_device(self, device_info: dict) -> bool:
        """注册设备到 NAS 系统"""
        pass
    
    @abstractmethod
    def get_scan_paths(self) -> List[str]:
        """获取扫描路径列表"""
        pass
    
    @abstractmethod
    def upload_report(self, report: dict) -> bool:
        """上传诊断报告"""
        pass
    
    @abstractmethod
    def get_config(self) -> dict:
        """获取 NAS 配置"""
        pass
```

**工时**：4小时

---

#### P0.2 群晖 ARM NAS 适配器
**目标**：支持群晖 DSM API（ARM 机型）

**文件**：`adapters/synology.py`

**支持机型**：
- DS 系列（J1010J、J4125 等 ARM 芯片）
- RS 系列（ARM 入门款）
- Plus 系列（部分 ARM 机型）

**核心功能**：
- DSM API 认证（账号密码 / 2FA）
- 设备注册到群晖
- 获取共享文件夹列表
- 上传诊断报告到 FileStation
- ARM 芯片型号识别（Realtek RTD1619B 等）

**API 端点**：
- `dsm/auth/login` - 登录
- `dsm/core/setting` - 系统信息
- `dsm/filestation/list` - 共享文件夹
- `dsm/storagepool/info` - 存储池

**工时**：8小时

---

#### P0.3 威联通 ARM NAS 适配器
**目标**：支持威联通 QTS API（ARM 机型）

**文件**：`adapters/qnap.py`

**支持机型**：
- TS-231P3（Annapurna Labs AL-314 ARM）
- TS-431KX（Annapurna Labs AL-514 ARM）
- TS-233（Realtek RTD1619B ARM）

**核心功能**：
- QTS API 认证
- 设备注册
- 获取共享文件夹
- 上传报告
- ARM 芯片识别（Annapurna Labs 系列）

**工时**：6小时

---

#### P0.4 通用 HTTP 后端适配器
**目标**：支持任意 HTTP 后端（保留 AI-NAS 兼容）

**文件**：`adapters/http_backend.py`

**功能**：
- 当前 AI-NAS 后端逻辑迁移至此
- 支持自定义 API 端点配置
- 向后兼容现有用户

**工时**：2小时

---

### P1 - 群晖 ARM 深度集成（2天工作量）

#### P1.1 群晖套件中心集成（ARM 专版）
**目标**：可作为群晖套件安装，专为 ARM 机型打包

**文件**：`synology/package/`

**内容**：
- `INFO` - 套件元信息（arch=rtd1619b/armv8 等）
- `scripts/install` - 安装脚本
- `scripts/start` - 启动脚本
- `scripts/uninstall` - 卸载脚本
- `ui/index.html` - Web UI

**ARM 架构支持**：
- `rtd1619b` - Realtek RTD1619B（DS223j 等）
- `armv8` - 通用 ARMv8
- `armada37xx` - Marvell Armada（部分老款）

**工时**：8小时

---

#### P1.2 群晖任务计划集成
**目标**：集成到群晖任务计划

**功能**：
- 定时诊断任务
- 诊断报告自动保存到指定共享文件夹
- 邮件通知异常

**工时**：4小时

---

#### P1.3 群晖通知中心集成
**目标**：诊断异常推送到群晖通知中心

**工时**：4小时

---

### P2 - 威联通 ARM 深度集成（1天工作量）

#### P2.1 威联通 App Center 集成（ARM 专版）
**目标**：可作为威联通应用安装，专为 ARM 机型打包

**文件**：`qnap/package/`

**ARM 架构支持**：
- `arm-x41` - Annapurna Labs AL-314/AL-514
- `arm_64` - 通用 ARM64

**工时**：6小时

---

#### P2.2 威联通通知集成
**目标**：诊断异常推送

**工时**：2小时

---

### P3 - 独立模式增强（1天工作量）

#### P3.1 离线诊断模式增强
**目标**：不依赖任何 NAS 后端也能完整运行

**功能**：
- 本地报告存储（不依赖上传）
- 本地历史记录
- 本地配置管理

**工时**：4小时

---

#### P3.2 报告导出格式增强
**目标**：支持更多导出格式

**新增格式**：
- PDF 报告
- CSV 数据导出
- Markdown 报告

**工时**：4小时

---

### P4 - Web UI（可选，2天工作量）

#### P4.1 轻量级 Web 界面
**目标**：浏览器查看诊断结果

**技术栈**：Flask/FastAPI + 静态前端

**功能**：
- 诊断仪表盘
- 历史报告查看
- 配置管理
- 一键诊断按钮

**工时**：16小时

---

## 文件结构规划

```
nastool/
├── adapters/                    # NAS 后端适配器（新建）
│   ├── __init__.py
│   ├── base.py                  # 抽象基类
│   ├── registry.py              # 适配器注册表
│   ├── synology.py              # 群晖适配器
│   ├── qnap.py                  # 威联通适配器
│   ├── truenas.py               # TrueNAS 适配器
│   ├── unraid.py                # Unraid 适配器
│   └── http_backend.py          # 通用 HTTP 后端
│
├── synology/                    # 群晖套件包（新建）
│   ├── package/
│   │   ├── INFO
│   │   ├── scripts/
│   │   └── ui/
│   └── README.md
│
├── qnap/                        # 威联通应用包（新建）
│   ├── package/
│   └── README.md
│
├── checks/                      # 诊断检查（不变）
├── fixes/                       # 自动修复（不变）
├── utils/                       # 工具库（不变）
├── reporters/                   # 报告输出（增强）
│   ├── terminal.py
│   ├── json_reporter.py
│   ├── html_reporter.py
│   ├── pdf_reporter.py          # 新增
│   ├── csv_reporter.py          # 新增
│   └── markdown_reporter.py     # 新增
│
└── arm_diagnose.py              # 主入口（适配层集成）
```

---

## 优先级与工时汇总

| 优先级 | 任务 | 工时 | 价值 |
|--------|------|------|------|
| P0.1 | 抽象 NAS 后端接口 | 4h | ⭐⭐⭐⭐⭐ |
| P0.2 | 群晖 Synology 适配器 | 8h | ⭐⭐⭐⭐⭐ |
| P0.3 | 威联通 QNAP 适配器 | 6h | ⭐⭐⭐⭐ |
| P0.4 | 通用 HTTP 后端适配器 | 2h | ⭐⭐⭐ |
| P1.1 | 群晖套件中心集成 | 8h | ⭐⭐⭐⭐⭐ |
| P1.2 | 群晖任务计划集成 | 4h | ⭐⭐⭐ |
| P1.3 | 群晖通知中心集成 | 4h | ⭐⭐⭐ |
| P2.1 | 威联通 App Center 集成 | 6h | ⭐⭐⭐ |
| P2.2 | 威联通通知集成 | 2h | ⭐⭐ |
| P3.1 | 离线诊断模式增强 | 4h | ⭐⭐⭐⭐ |
| P3.2 | 报告导出格式增强 | 4h | ⭐⭐⭐ |
| P4.1 | 轻量级 Web 界面 | 16h | ⭐⭐⭐ |

**总计**：68 小时（约 8.5 个工作日）

---

## 里程碑

### Milestone 1 - 核心适配（Day 1-3）
- [ ] P0.1 抽象 NAS 后端接口
- [ ] P0.2 群晖适配器
- [ ] P0.3 威联通适配器
- [ ] P0.4 通用 HTTP 后端

**交付物**：支持 AI-NAS / 群晖 / 威联通 三种后端

---

### Milestone 2 - 群晖深度集成（Day 4-5）
- [ ] P1.1 群晖套件中心集成
- [ ] P1.2 群晖任务计划集成
- [ ] P1.3 群晖通知中心集成

**交付物**：群晖套件包（可上架套件中心）

---

### Milestone 3 - 威联通 + 独立模式（Day 6-7）
- [ ] P2.1 威联通 App Center 集成
- [ ] P2.2 威联通通知集成
- [ ] P3.1 离线诊断模式增强
- [ ] P3.2 报告导出格式增强

**交付物**：威联通应用包 + 独立模式增强

---

### Milestone 4 - Web UI（可选，Day 8-9）
- [ ] P4.1 轻量级 Web 界面

**交付物**：Web 仪表盘

---

## 商业化路径

### 阶段 1 - 免费推广（Month 1-3）
- 群晖套件中心上架（ARM 机型专版）
- 威联通 App Center 上架（ARM 机型专版）
- GitHub 开源推广
- 社区反馈收集（NAS 论坛、群晖社区）

### 阶段 2 - 增值服务（Month 4-6）
- Pro 版本（高级 AI 算力诊断 + 性能优化建议）
- 订阅制（$4.99/月）
- 企业版（多 ARM 设备统一管理）

### 阶段 3 - 生态建设（Month 7-12）
- 更多 ARM NAS 系统适配（海康威视、华硕 ASUSTOR）
- ARM 设备性能排行榜（社区数据）
- AI-NAS 与群晖/威联通互联互通

---

## 配置示例

### 群晖 ARM 配置（config.yaml）
```yaml
nas:
  type: synology
  host: https://nas.local:5001
  username: admin
  password: ${SYNOLOGY_PASSWORD}
  verify_ssl: false

synology:
  share: diagnostics    # 报告保存的共享文件夹
  notify: true          # 启用通知
  arch: rtd1619b        # ARM 架构（自动检测或手动指定）
```

### 威联通 ARM 配置
```yaml
nas:
  type: qnap
  host: https://nas.local:8081
  username: admin
  password: ${QNAP_PASSWORD}

qnap:
  share: diagnostics
  notify: true
  arch: arm-x41         # Annapurna Labs ARM
```

### AI-NAS 配置（向后兼容）
```yaml
nas:
  type: http
  backend_url: https://qizhiainas.com
  device_name: my-device
  register: true
```

---

## CLI 用法变化

```bash
# 指定 NAS 类型
python arm_diagnose.py --nas synology --register
python arm_diagnose.py --nas qnap --register
python arm_diagnose.py --nas http --register

# 配置向导自动识别
python arm_diagnose.py --setup
# → 选择 NAS 类型：1) Synology  2) QNAP  3) AI-NAS  4) 独立模式

# 群晖专用命令
python arm_diagnose.py --synology-auth     # 群晖认证
python arm_diagnose.py --synology-shares   # 列出共享文件夹

# 威联通专用命令
python arm_diagnose.py --qnap-auth         # 威联通认证
```

---

## 风险与对策

| 风险 | 对策 |
|------|------|
| 群晖 ARM 机型 API 差异 | 分架构测试 + 兼容层 |
| 威联通 ARM API 文档不全 | 抓包分析 + 社区协作 |
| 套件审核周期长 | 提前准备 + 沟通 |
| 认证安全 | 环境变量存储密码 + 不明文保存 |
| ARM 芯片多样性 | 自动检测芯片型号 + 适配建议 |

---

## ARM 芯片支持列表

### 已支持（v3.0.6）
| 芯片 | 品牌 | 用途 |
|------|------|------|
| Jetson Xavier NX | NVIDIA | AI 边缘计算 |
| Jetson Nano | NVIDIA | AI 边缘计算 |
| RK3588 | 瑞芯微 | 开发板/迷你主机 |
| RK3576 | 瑞芯微 | 开发板 |
| 昇腾 310 | 华为 | AI 推理 |

### v3.0.7 新增支持
| 芯片 | 品牌 | NAS 机型 |
|------|------|----------|
| RTD1619B | Realtek | 群晖 DS223j、威联通 TS-233 |
| AL-314 | Annapurna Labs | 威联通 TS-231P3 |
| AL-514 | Annapurna Labs | 威联通 TS-431KX |
| Armada 3720 | Marvell | 群晖 DS118（老款 ARM）|

---

## 下一步行动

1. **确认优先级**：用户确认是否按此计划执行
2. **开始 P0.1**：创建 `adapters/base.py` 抽象基类
3. **群晖 API 调研**：熟悉 DSM API 文档
4. **原型验证**：先实现群晖适配器原型

---

**计划制定时间**：2026-04-12
**预计完成时间**：2026-04-20
**版本目标**：v3.0.7
