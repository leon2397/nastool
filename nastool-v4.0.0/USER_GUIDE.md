# NASTool V4.1 用户指南

**版本**: V4.1
**发布日期**: 2026-04-27
**适用平台**: ARM设备

## 📋 目录

1. [简介](#1-简介)
2. [新功能特性](#2-新功能特性)
3. [安装指南](#3-安装指南)
4. [快速开始](#4-快速开始)
5. [配置说明](#5-配置说明)
6. [使用示例](#6-使用示例)
7. [常见问题](#7-常见问题)
8. [故障排除](#8-故障排除)

## 1. 简介

NASTool是一款专为ARM设备设计的检测工具，用于监控和分析设备的健康状态。V4.1版本大幅提升了检测数据的准确性和可靠性，通过多源数据融合、自适应阈值和数据验证等技术，为用户提供更加准确的设备状态评估。

### 主要功能

- **多源数据检测**: 支持多种数据源，提高检测准确性
- **自适应阈值**: 根据设备类型和环境动态调整阈值
- **数据融合**: 智能融合多个数据源的结果
- **异常值检测**: 自动识别和过滤异常数据
- **置信度评分**: 综合评估检测结果的可靠性
- **历史数据分析**: 支持历史数据存储和趋势分析

## 2. 新功能特性

### 2.1 多源数据验证系统

- **数据源扩展**: 支持thermal_zone、sensors、hwmon、vcgencmd等多种数据源
- **数据融合**: 支持8种融合方法（加权平均、中位数、均值等）
- **异常值检测**: 支持Z-score、IQR、MAD三种检测算法
- **一致性验证**: 检查数据的时间、值、趋势和源一致性

### 2.2 自适应阈值系统

- **设备识别**: 自动识别RK3588、Jetson等多种ARM设备
- **专用阈值**: 为不同设备类型配置专用的温度和性能阈值
- **动态调整**: 根据环境因素动态调整阈值

### 2.3 校准机制

- **校准因子**: 支持设备特定的校准因子
- **标准工具比对**: 与lm-sensors、ipmitool等标准工具比对
- **校准流程**: 提供完整的校准指南

### 2.4 环境感知系统

- **环境数据采集**: 记录检测时的CPU负载、内存使用等环境数据
- **条件检测**: 在特定条件下进行检测，提高结果可靠性
- **环境标记**: 将环境数据与检测结果关联

### 2.5 历史数据分析

- **历史存储**: 支持30天历史数据存储
- **趋势分析**: 分析设备状态的长期趋势
- **历史对比**: 比较不同时间点的检测结果
- **趋势图表**: 直观展示设备状态变化

## 3. 安装指南

### 3.1 系统要求

- **硬件**: ARM设备（RK3588、RK3568、Jetson等）
- **操作系统**: Linux (Ubuntu 20.04+, Debian 10+)
- **Python**: 3.8+
- **依赖**: numpy >= 1.20, scipy >= 1.7

### 3.2 安装步骤

```bash
# 克隆仓库
git clone https://github.com/nastool/nastool.git
cd nastool

# 安装依赖
pip install -r requirements.txt

# 安装NASTool
pip install -e .
```

### 3.3 验证安装

```bash
# 运行版本检查
nastool --version

# 运行自检
nastool --self-test
```

## 4. 快速开始

### 4.1 基本检测

```bash
# 执行全面检测
nastool --target localhost

# 输出JSON格式结果
nastool --target localhost --json

# 生成详细报告
nastool --target localhost --report
```

### 4.2 特定检测项

```bash
# 仅检测CPU温度
nastool --target localhost --check cpu_temp

# 仅检测网络状态
nastool --target localhost --check network

# 仅检测存储健康
nastool --target localhost --check storage
```

### 4.3 批量检测

```bash
# 从文件读取目标列表
nastool --target-file targets.txt

# 并行检测多个目标
nastool --target-file targets.txt --parallel 4
```

## 5. 配置说明

### 5.1 配置文件

主要配置文件位于 `~/.nastool/config.json`：

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

### 5.2 环境变量

| 环境变量 | 描述 | 默认值 |
|---------|------|--------|
| NASTOOL_CONFIG | 配置文件路径 | ~/.nastool/config.json |
| NASTOOL_LOG_LEVEL | 日志级别 | info |
| NASTOOL_HISTORY_DIR | 历史数据目录 | ~/.nastool/history |

## 6. 使用示例

### 6.1 日常监控

```bash
# 每天执行一次检测并保存结果
0 0 * * * nastool --target localhost --report --output /var/log/nastool/daily_report.txt

# 每小时检测CPU温度并记录
0 * * * * nastool --target localhost --check cpu_temp --json >> /var/log/nastool/cpu_temp.log
```

### 6.2 故障诊断

```bash
# 详细诊断网络问题
nastool --target localhost --check network --verbose

# 分析存储健康状态
nastool --target localhost --check storage --report

# 查看历史趋势
nastool --target localhost --history --days 7
```

### 6.3 批量设备管理

```bash
# 检测所有设备并生成汇总报告
nastool --target-file devices.txt --report --output all_devices_report.txt

# 仅检测异常设备
nastool --target-file devices.txt --only-failed
```

## 7. 常见问题

### 7.1 检测结果不准确

**问题**: 检测结果与实际情况不符

**解决方案**:
- 确保使用了多个数据源
- 运行校准流程：`nastool --calibrate`
- 检查设备识别是否正确：`nastool --identify`

### 7.2 检测速度慢

**问题**: 检测过程耗时较长

**解决方案**:
- 减少检测项：`nastool --check cpu_temp,network`
- 禁用历史存储：`nastool --no-history`
- 调整并行度：`nastool --parallel 2`

### 7.3 数据源不可用

**问题**: 某些数据源显示不可用

**解决方案**:
- 安装必要的依赖：`sudo apt install lm-sensors`
- 检查权限：确保有读取传感器的权限
- 尝试使用备用数据源

## 8. 故障排除

### 8.1 日志分析

```bash
# 查看详细日志
nastool --target localhost --verbose 2>&1 > debug.log

# 分析错误信息
grep -i error debug.log
```

### 8.2 自检流程

```bash
# 运行完整自检
nastool --self-test

# 检查数据源可用性
nastool --check-sources

# 验证配置
nastool --validate-config
```

### 8.3 常见错误

| 错误信息 | 可能原因 | 解决方案 |
|---------|---------|---------|
| No data sources available | 数据源不可用 | 安装必要的依赖 |
| Device not identified | 设备识别失败 | 检查设备信息或手动指定设备类型 |
| Calibration failed | 校准失败 | 确保标准工具已安装 |
| History storage error | 历史存储错误 | 检查目录权限和磁盘空间 |

## 📞 支持

- **GitHub Issues**: [https://github.com/nastool/nastool/issues](https://github.com/nastool/nastool/issues)
- **Discord**: [https://discord.gg/nastool](https://discord.gg/nastool)
- **文档**: [https://docs.nastool.org](https://docs.nastool.org)

---

**最后更新**: 2026-04-27
**版本**: 1.0