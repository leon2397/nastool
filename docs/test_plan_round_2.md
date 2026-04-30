# NASTool 真机测试计划 - 第二轮

> 测试轮次: Round 2
> 测试日期: 2026-04-25
> 测试目标: 192.168.1.123 (Jetson Xavier NX)
> 测试人员: ___________
> 测试状态: 待执行
> 测试基础: Round 1 已完成，所有 BUG 已修复

---

## 一、测试范围

### 1.1 检测模块清单（4.0 版本）

| 模块 | 检测项数量 | 测试优先级 |
|------|-----------|-----------|
| System (系统) | 14 | P0 |
| Network (网络) | 13 | P0 |
| Storage (存储) | 11 | P0 |
| AI (AI框架) | 17 | P0 |
| Security (安全) | 10 | P1 |
| NAS (NAS服务) | 8 | P1 |
| USB (USB设备) | 4 | P2 |
| **总计** | **~77** | - |

### 1.2 测试模式

- [x] Quick Mode (快速模式, ~3秒, 跳过性能测试)
- [x] Full Mode (完整模式, 包含性能基准测试)
- [ ] Mock Mode (模拟模式, 用于验证报告功能)

---

## 二、测试执行步骤

### Step 1: 环境检查
```bash
# 1. 确认目标设备可连接
ping 192.168.1.123

# 2. 确认HTTP API可访问
curl http://192.168.1.123:8000/health

# 3. 记录环境信息
- 设备型号: ___________
- 操作系统: ___________
- Python版本: ___________
- 网络环境: ___________
```

### Step 2: 执行测试
```bash
# 运行快速模式测试
python test_remote.py

# 运行完整模式测试（如果需要）
python test_remote_full.py
```

### Step 3: BUG记录
- 测试过程中发现任何 BUG，立即记录到 `bugs_round_2.json`
- 不要中断测试去修复 BUG

### Step 4: 生成报告
- 测试完成后，整理测试结果
- 生成本轮测试报告

---

## 三、测试检查项（4.0 版本）

### 3.1 System 系统检测
- [ ] Python版本检测
- [ ] Pip安装检测
- [ ] 系统库检测
- [ ] 内存检测
- [ ] 定时任务检测
- [ ] 系统日志检测
- [ ] 进程数量检测
- [ ] 软件包更新检测
- [ ] 系统磁盘空间检测
- [ ] CPU温度检测
- [ ] 系统运行时间检测
- [ ] Docker容器检测
- [ ] 内核版本检测
- [ ] Python库检测

### 3.2 Network 网络检测
- [ ] 互联网访问检测
- [ ] DNS缓存检测
- [ ] DNS解析检测
- [ ] DNS覆盖检测
- [ ] MTU检测
- [ ] 代理检测
- [ ] WiFi检测
- [ ] 带宽检测
- [ ] 延迟检测
- [ ] 路由检测
- [ ] 端口冲突检测
- [ ] NAS后端检测
- [ ] 网卡速度检测

### 3.3 Storage 存储检测
- [ ] 磁盘空间检测
- [ ] Inode检测
- [ ] IO等待检测
- [ ] 路径存在检测
- [ ] 写入速度检测
- [ ] ZFS健康检测
- [ ] SMART健康检测
- [ ] 硬盘温度检测
- [ ] RAID状态检测
- [ ] Docker镜像检测
- [ ] 存储趋势检测

### 3.4 AI 框架检测
- [ ] GPU检测
- [ ] NVIDIA驱动版本
- [ ] TensorFlow版本
- [ ] Keras版本
- [ ] CUDNN版本
- [ ] OpenVINO版本
- [ ] PaddlePaddle检测
- [ ] Triton服务器检测
- [ ] MLflow检测
- [ ] GPU内存检测
- [ ] GPU利用率检测
- [ ] NVIDIA容器工具包检测
- [ ] ONNX模型检测
- [ ] OneDNN版本检测
- [ ] TorchServe检测
- [ ] TensorFlow Serving检测
- [ ] Kubeflow检测

### 3.5 Security 安全检测
- [ ] OpenSSL版本
- [ ] 防火墙检测
- [ ] SSH Root登录检测
- [ ] SSH配置检测
- [ ] Fail2ban检测
- [ ] ClamAV检测
- [ ] 端口扫描
- [ ] SELinux检测
- [ ] SSL证书检测
- [ ] SSL证书天数

### 3.6 NAS 服务检测
- [ ] DSM版本
- [ ] 用户统计
- [ ] 共享权限
- [ ] UPS状态
- [ ] 日志磁盘
- [ ] 定时任务冲突
- [ ] SMB服务
- [ ] NFS服务

### 3.7 USB 设备检测
- [ ] USB设备检测
- [ ] USB存储检测
- [ ] USB权限检测
- [ ] USB电源检测

---

## 四、BUG记录规范

### 4.1 严重等级定义

| 等级 | 定义 | 示例 |
|------|------|------|
| P0 - 阻断性 | 导致结果错误或工具崩溃 | 评分系统失效、乱码输出 |
| P1 - 关键 | 信息错误或重要功能缺失 | 检测失败、误报 |
| P2 - 次要 | 检测不准确 | 数值偏差、超时 |
| P3 - 改进 | 不影响正确性 | 建议优化 |

### 4.2 记录字段

```json
{
  "bug_id": "BUG-R2-XXX",
  "severity": "P0/P1/P2/P3",
  "module": "System/Network/Storage/AI/Security/NAS/USB",
  "title": "BUG标题",
  "description": "详细描述",
  "reproduce_steps": ["步骤1", "步骤2"],
  "expected_result": "预期结果",
  "actual_result": "实际结果",
  "environment": {
    "device": "设备型号",
    "os": "操作系统",
    "python": "Python版本"
  },
  "timestamp": "2026-04-25T10:00:00",
  "screenshot": "截图路径",
  "log": "日志路径",
  "status": "open/fixed/verified"
}
```

---

## 五、测试完成标准

- [ ] 所有检测项执行完毕
- [ ] BUG记录完整（如有）
- [ ] 测试报告生成
- [ ] 环境信息记录完整

---

## 六、签名确认

| 角色 | 姓名 | 日期 | 签名 |
|------|------|------|------|
| 测试执行人 | | | |
| 测试审核人 | | | |

