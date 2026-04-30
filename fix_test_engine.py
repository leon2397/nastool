import re

with open('tools/test_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 在 test_gpu 方法后添加新方法
new_methods = '''

    def test_temperature(self, device):
        """测试设备温度"""
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                # 尝试获取CPU温度（支持多种平台）
                cpu_temp = temps.get("coretemp") or temps.get("cpu_thermal") or temps.get("thermal_zone0")
                if cpu_temp:
                    temp = cpu_temp[0].current
                    status = "pass" if temp < 80 else ("warning" if temp < 90 else "fail")
                    return {"status": status, "details": f"CPU温度: {temp:.1f}°C"}
            return {"status": "info", "details": "无法获取温度信息"}
        except Exception as e:
            return {"status": "error", "details": str(e)}

    def test_uptime(self, device):
        """测试系统运行时间"""
        try:
            import psutil
            import datetime
            uptime = psutil.boot_time()
            uptime_delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(uptime)
            days = uptime_delta.days
            hours = uptime_delta.seconds // 3600
            minutes = (uptime_delta.seconds % 3600) // 60
            return {"status": "pass", "details": f"运行时间: {days}天 {hours}小时 {minutes}分钟"}
        except Exception as e:
            return {"status": "error", "details": str(e)}
'''

# 在 test_gpu 方法后插入
pattern = r"(    def test_gpu\(self, device\):.*?return \{'status': 'error', 'details': str\(e\)\})"
replacement = r"\1" + new_methods

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('tools/test_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 已添加缺失的测试方法")
