# nastool-adapters

设备适配层模块，提供各种设备的检测和管理功能。

## 功能

- HTTP 设备检测（支持连接池和重试机制）
- SSH 设备检测（支持批量命令执行和性能优化）
- 各种设备的专用适配器（Synology、QNAP、Jetson、Rockchip、Ascend、Sophon等）
- 网络请求重试和连接池管理

## 目录结构

- `nastool_adapters/`
  - `utils/` - 工具类（重试机制、连接池）
  - `ascend/` - 华为Ascend NPU适配器
  - `jetson/` - NVIDIA Jetson设备适配器
  - `http_detector.py` - HTTP设备检测器
  - `ssh_detector.py` - SSH设备检测器
  - `nas_client.py` - NAS设备客户端
  - `registry.py` - 适配器注册表

## 安装

```bash
pip install -e .
```

## 依赖

- `requests` - HTTP请求
- `urllib3` - HTTP连接池
- `paramiko` - SSH连接

## 使用示例

### HTTP检测器

```python
from nastool_adapters.http_detector import HTTPDetector

# 创建HTTP检测器
detector = HTTPDetector(timeout=30)

# 检测设备状态
result = detector.check_device("http://192.168.1.1:8000")
print(f"设备状态: {'在线' if result else '离线'}")

# 执行API测试
api_result = detector.test_api("http://192.168.1.1:8000/api/health")
print(f"API测试: {api_result}")
```

### SSH检测器

```python
from nastool_adapters.ssh_detector import SSHDetector

# 创建SSH检测器
detector = SSHDetector(
    host="192.168.1.1",
    port=22,
    username="admin",
    password="password"
)

# 批量执行命令
commands = [
    "uname -a",
    "df -h",
    "free -m"
]
results = detector.batch_exec(commands)
for cmd, output in results.items():
    print(f"命令: {cmd}\n输出: {output}\n")
```

### 重试机制

```python
from nastool_adapters.utils.retry import retry, RetryConfig

# 使用重试装饰器
@retry(max_attempts=3, delay=2, backoff=1.5)
def fetch_data(url):
    """获取数据，失败时自动重试"""
    import requests
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

# 使用
result = fetch_data("http://api.example.com/data")
```

### HTTP连接池

```python
from nastool_adapters.utils.pool import create_http_pool, DEFAULT_POOL_CONFIG

# 创建连接池
pool = create_http_pool(DEFAULT_POOL_CONFIG)

# 使用连接池发送请求
response = pool.request(
    "GET",
    "http://api.example.com/data",
    timeout=10
)
print(response.data.decode('utf-8'))
```

## 配置选项

### HTTP检测器配置
- `timeout` - 超时时间（秒）
- `retries` - 重试次数
- `pool_size` - 连接池大小

### SSH检测器配置
- `host` - 主机地址
- `port` - SSH端口
- `username` - 用户名
- `password` - 密码
- `key_path` - 密钥文件路径
- `timeout` - 超时时间（秒）

## 性能优化

- **HTTP连接池**：复用HTTP连接，减少连接建立开销
- **SSH批量执行**：减少SSH连接次数，提高命令执行效率
- **智能重试**：对网络错误进行自动重试，提高可靠性
- **超时管理**：防止命令执行卡住

## 注意事项

- SSH连接需要正确的用户名和密码或密钥文件
- HTTP检测需要目标设备运行API服务
- 批量执行命令时，注意命令的执行顺序和依赖关系

## 许可证

MIT