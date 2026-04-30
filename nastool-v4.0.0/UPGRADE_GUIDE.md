# NASTool V4.1 升级指南

**版本**: V4.1
**发布日期**: 2026-04-27
**适用平台**: ARM设备

## 📋 目录

1. [升级准备](#1-升级准备)
2. [从V4.0升级](#2-从V40升级)
3. [从V3.x升级](#3-从V3x升级)
4. [配置迁移](#4-配置迁移)
5. [验证升级](#5-验证升级)
6. [回滚方案](#6-回滚方案)

## 1. 升级准备

### 1.1 系统要求

- **硬件**: ARM设备（RK3588、RK3568、Jetson等）
- **操作系统**: Linux (Ubuntu 20.04+, Debian 10+)
- **Python**: 3.8+
- **依赖**: numpy >= 1.20, scipy >= 1.7

### 1.2 备份数据

在升级前，建议备份以下数据：

```bash
# 备份配置文件
cp ~/.nastool/config.json ~/.nastool/config.json.bak

# 备份历史数据
cp -r ~/.nastool/history ~/.nastool/history.bak

# 备份报告文件
cp -r ~/.nastool/reports ~/.nastool/reports.bak
```

### 1.3 检查当前版本

```bash
# 检查当前版本
nastool --version

# 运行自检
nastool --self-test
```

## 2. 从V4.0升级

### 2.1 升级步骤

```bash
# 停止NASTool服务（如果使用systemd）
sudo systemctl stop nastool

# 进入NASTool目录
cd /path/to/nastool

# 更新代码
git pull

# 安装新依赖
pip install -r requirements.txt

# 运行升级脚本
python scripts/upgrade.py

# 启动服务
sudo systemctl start nastool
```

### 2.2 验证升级

```bash
# 检查版本
nastool --version

# 运行自检
nastool --self-test

# 执行测试检测
nastool --target localhost
```

## 3. 从V3.x升级

### 3.1 升级步骤

从V3.x版本升级需要重新安装：

```bash
# 停止旧版本
sudo systemctl stop nastool

# 备份配置
cp ~/.nastool/config.json ~/.nastool/config.json.v3.bak

# 移除旧版本
pip uninstall -y nastool

# 克隆新版本
git clone https://github.com/nastool/nastool.git
cd nastool

# 安装依赖
pip install -r requirements.txt

# 安装新版本
pip install -e .

# 运行升级脚本
python scripts/upgrade.py --from-v3

# 启动服务
sudo systemctl start nastool
```

### 3.2 配置迁移

从V3.x升级时，配置文件需要重新生成。升级脚本会尝试迁移部分配置，但建议手动检查和调整。

## 4. 配置迁移

### 4.1 配置文件变更

V4.1版本的配置文件结构发生了变化，主要变更：

| 旧配置 | 新配置 | 说明 |
|-------|-------|------|
| `thresholds` | `thresholds.{device_type}` | 按设备类型分配置 |
| `fusion_method` | `data_fusion.fusion_method` | 移至data_fusion部分 |
| `history_enabled` | `history.enabled` | 移至history部分 |

### 4.2 示例配置

```json
{
  "thresholds": {
    "rk3588": {
      "cpu_temp": {"warning": 70, "critical": 80},
      "gpu_temp": {"warning": 75, "critical": 85}
    },
    "jetson_xavier": {
      "cpu_temp": {"warning": 75, "critical": 85},
      "gpu_temp": {"warning": 80, "critical": 90}
    }
  },
  "data_fusion": {
    "outlier_detection": true,
    "fusion_method": "weighted_average",
    "min_sources": 2
  },
  "history": {
    "enabled": true,
    "retention_days": 30
  }
}
```

### 4.3 手动调整

升级后，建议检查以下配置：

1. **设备阈值**: 确保为您的设备类型配置了正确的阈值
2. **数据融合**: 根据需要调整融合方法和异常值检测设置
3. **历史存储**: 调整历史数据保留时间

## 5. 验证升级

### 5.1 基本验证

```bash
# 运行版本检查
nastool --version

# 运行自检
nastool --self-test

# 执行全面检测
nastool --target localhost
```

### 5.2 功能验证

```bash
# 测试多源数据融合
nastool --target localhost --check cpu_temp --verbose

# 测试设备识别
nastool --identify

# 测试历史数据
nastool --history --days 1

# 测试报告生成
nastool --target localhost --report --output test_report.txt
```

### 5.3 性能验证

```bash
# 测试执行时间
time nastool --target localhost

# 测试批量检测
time nastool --target-file targets.txt --parallel 4
```

## 6. 回滚方案

### 6.1 回滚到V4.0

```bash
# 停止服务
sudo systemctl stop nastool

# 恢复配置
cp ~/.nastool/config.json.bak ~/.nastool/config.json

# 恢复代码到V4.0
git checkout v4.0

# 安装旧依赖
pip install -r requirements.txt

# 启动服务
sudo systemctl start nastool
```

### 6.2 回滚到V3.x

```bash
# 停止服务
sudo systemctl stop nastool

# 卸载新版本
pip uninstall -y nastool

# 安装旧版本
pip install nastool==3.9.9

# 恢复配置
cp ~/.nastool/config.json.v3.bak ~/.nastool/config.json

# 启动服务
sudo systemctl start nastool
```

### 6.3 故障排除

如果升级后出现问题：

1. **检查日志**: `journalctl -u nastool`
2. **运行自检**: `nastool --self-test`
3. **验证配置**: `nastool --validate-config`
4. **检查依赖**: `pip check`

## 📞 支持

- **GitHub Issues**: [https://github.com/nastool/nastool/issues](https://github.com/nastool/nastool/issues)
- **Discord**: [https://discord.gg/nastool](https://discord.gg/nastool)
- **文档**: [https://docs.nastool.org](https://docs.nastool.org)

---

**最后更新**: 2026-04-27
**版本**: 1.0