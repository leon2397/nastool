# gui package
try:
    from .app import NastoolsApp
except ImportError:
    pass  # 避免循环导入
