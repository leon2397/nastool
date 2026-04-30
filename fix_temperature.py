import re

with open('tools/test_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 更新温度检测方法
old_temperature = '''    def test_temperature(self, device):
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
            return {"status": "error", "details": str(e)}'''

new_temperature = '''    def test_temperature(self, device):
        """测试设备温度"""
        try:
            import psutil
            import platform
            
            # Windows系统特殊处理
            if platform.system() == "Windows":
                try:
                    # 使用WMIC获取温度（Windows专用）
                    import subprocess
                    result = subprocess.run(
                        ["wmic", "cpu", "get", "Temperature"],
                        capture_output=True, text=True, timeout=10
                    )
                    lines = result.stdout.strip().split('\\n')
                    if len(lines) > 1:
                        temp_str = lines[1].strip()
                        if temp_str.isdigit():
                            temp = int(temp_str)
                            status = "pass" if temp < 80 else ("warning" if temp < 90 else "fail")
                            return {"status": status, "details": f"CPU温度: {temp}°C"}
                except:
                    pass
                return {"status": "info", "details": "Windows系统温度检测不可用"}
            
            # Linux系统使用psutil
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
            return {"status": "error", "details": str(e)}'''

content = content.replace(old_temperature, new_temperature)

with open('tools/test_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 已修复温度检测兼容性问题")
