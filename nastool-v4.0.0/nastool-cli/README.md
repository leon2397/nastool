# nastool-cli

命令行工具模块，提供各种诊断和管理命令。

## 功能

- 设备诊断
- 批量操作
- 结果比较
- Jetson设备安装和补丁
- WebSocket客户端

## 目录结构

- `nastool_cli/`
  - `commands/` - 命令模块
    - `device.py` - 设备相关命令
    - `diagnose.py` - 诊断相关命令
  - `main.py` - 主入口
  - `main_v4.py` - v4版本主入口
  - `batch.py` - 批量操作
  - `compare.py` - 结果比较
  - `ws_client.py` - WebSocket客户端

## 安装

```bash
pip install -e .
```

## 依赖

- `click` - 命令行参数解析
- `websocket-client` - WebSocket客户端
- `tabulate` - 表格输出

## 使用示例

### 基本用法

```bash
# 显示帮助
nastool --help

# 版本信息
nastool --version
```

### 设备诊断

```bash
# 执行完整诊断
nastool device diagnose

# 执行特定检查
nastool device check --category system

# 检查远程设备
nastool device check-remote --host 192.168.1.1 --port 8000
```

### 批量操作

```bash
# 批量诊断多个设备
nastool batch diagnose --devices devices.txt

# 批量执行命令
nastool batch exec --command "df -h" --devices devices.txt
```

### 结果比较

```bash
# 比较两次诊断结果
nastool compare reports/report1.json reports/report2.json

# 生成差异报告
nastool compare reports/report1.json reports/report2.json --output diff.html
```

### Jetson设备操作

```bash
# 安装Jetson相关软件
nastool jetson install

# 应用Jetson补丁
nastool jetson patch
```

## 命令详解

### device 命令

- `diagnose` - 执行完整诊断
- `check` - 执行特定检查
- `check-remote` - 检查远程设备
- `info` - 显示设备信息

### batch 命令

- `diagnose` - 批量诊断设备
- `exec` - 批量执行命令
- `report` - 批量生成报告

### compare 命令

- 比较两个诊断报告的差异
- 支持JSON和HTML输出

### jetson 命令

- `install` - 安装Jetson软件
- `patch` - 应用Jetson补丁

## 配置文件

CLI工具使用 `~/.nastool/config.yaml` 作为配置文件：

```yaml
# 配置文件示例
server:
  host: 192.168.1.1
  port: 8000
  api_key: your_api_key

devices:
  - name: device1
    host: 192.168.1.100
    port: 22
    username: admin
    password: password
  - name: device2
    host: 192.168.1.101
    port: 22
    username: admin
    key_path: ~/.ssh/id_rsa
```

## 环境变量

- `NASTOOL_CONFIG` - 配置文件路径
- `NASTOOL_API_KEY` - API密钥
- `NASTOOL_SERVER` - 服务器地址

## 输出格式

- `--format` - 输出格式（json、text、table）
- `--output` - 输出文件路径

## 示例：批量诊断

1. 创建设备列表文件 `devices.txt`：

```
192.168.1.100:8000
192.168.1.101:8000
192.168.1.102:8000
```

2. 执行批量诊断：

```bash
nastool batch diagnose --devices devices.txt --output reports/
```

3. 查看结果：

```bash
ls reports/
```

## 示例：比较报告

```bash
# 执行第一次诊断
nastool device diagnose --output report1.json

# 执行第二次诊断
nastool device diagnose --output report2.json

# 比较差异
nastool compare report1.json report2.json --output diff.html
```

## 性能优化

- **并行执行**：批量操作支持并行执行
- **超时管理**：命令执行有超时限制
- **错误处理**：完善的错误处理机制

## 扩展命令

可以通过添加新的命令模块扩展CLI功能：

```python
# nastool_cli/commands/custom.py
import click
from nastool_cli.main import cli

@cli.command('custom')
def custom_command():
    """自定义命令"""
    click.echo('执行自定义命令')
```

## 许可证

MIT