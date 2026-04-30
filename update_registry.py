import re

with open('tools/checker_registry.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 更新文件命名模式
old_pattern = """                # 支持多种命名模式
                if (filename.endswith('_check.py') or
                    filename.endswith('_checker.py') or
                    filename.endswith('_service.py')):
                    module_name = filename[:-3]
                    self._register_checker(category, module_name)"""

new_pattern = """                # 支持多种命名模式
                if (filename.endswith('_check.py') or
                    filename.endswith('_checker.py') or
                    filename.endswith('_service.py') or
                    filename.endswith('_status.py') or
                    filename.endswith('_disk.py') or
                    filename.endswith('_health.py')):
                    module_name = filename[:-3]
                    self._register_checker(category, module_name)"""

content = content.replace(old_pattern, new_pattern)

with open('tools/checker_registry.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 已更新检测器注册表")
