import re

with open('tools/test_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 更新 full 模式的测试项
old_full_section = '''        if test_mode == 'full':
            # 添加所有测试项
            additional_tests.update({
                'CPU信息': self.test_cpu,
                '内存检查': self.test_memory,
                '存储检查': self.test_storage
            })'''

new_full_section = '''        if test_mode == 'full':
            # 添加所有测试项
            additional_tests.update({
                'CPU信息': self.test_cpu,
                '内存检查': self.test_memory,
                '存储检查': self.test_storage,
                '温度检测': self.test_temperature,
                '运行时间': self.test_uptime
            })'''

content = content.replace(old_full_section, new_full_section)

with open('tools/test_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 已更新测试选择逻辑")
