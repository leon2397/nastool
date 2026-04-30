#!/usr/bin/env python3
"""友好错误处理模块"""

import sys
import traceback
import json

class FriendlyError(Exception):
    """友好错误类"""
    def __init__(self, message, suggestion=None, error_code=None):
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion
        self.error_code = error_code
    
    def to_dict(self):
        """转换为字典"""
        return {
            'message': self.message,
            'suggestion': self.suggestion,
            'error_code': self.error_code
        }
    
    def __str__(self):
        """字符串表示"""
        result = f'❌ {self.message}'
        if self.suggestion:
            result += f'\n💡 建议: {self.suggestion}'
        if self.error_code:
            result += f'\n📋 错误码: {self.error_code}'
        return result

class ErrorHandler:
    """错误处理器"""
    
    ERROR_MAP = {
        'ModuleNotFoundError': {
            'pattern': 'No module named',
            'message': '缺少必要的依赖模块',
            'suggestion': '请运行 pip install -r requirements.txt 安装依赖',
            'error_code': 'E001'
        },
        'ConnectionRefusedError': {
            'pattern': 'Connection refused',
            'message': '连接被拒绝',
            'suggestion': '请检查目标设备是否开机、网络是否通畅、防火墙是否允许连接',
            'error_code': 'E002'
        },
        'TimeoutError': {
            'pattern': 'timed out',
            'message': '连接超时',
            'suggestion': '请检查网络连接或增加超时时间设置',
            'error_code': 'E003'
        },
        'paramiko.ssh_exception.AuthenticationException': {
            'pattern': 'Authentication failed',
            'message': 'SSH认证失败',
            'suggestion': '请检查用户名和密码是否正确',
            'error_code': 'E004'
        },
        'FileNotFoundError': {
            'pattern': 'No such file or directory',
            'message': '文件或目录不存在',
            'suggestion': '请检查路径是否正确',
            'error_code': 'E005'
        },
        'PermissionError': {
            'pattern': 'Permission denied',
            'message': '权限不足',
            'suggestion': '请以管理员身份运行或检查文件权限',
            'error_code': 'E006'
        },
        'json.JSONDecodeError': {
            'pattern': 'Expecting value|Invalid JSON',
            'message': 'JSON格式错误',
            'suggestion': '请检查配置文件格式是否正确',
            'error_code': 'E007'
        },
        'ValueError': {
            'pattern': 'invalid literal for int|could not convert string to float',
            'message': '参数类型错误',
            'suggestion': '请确保输入的参数类型正确',
            'error_code': 'E008'
        }
    }
    
    @staticmethod
    def analyze_error(exc):
        """分析错误并返回友好提示"""
        exc_type = type(exc).__name__
        exc_str = str(exc)
        
        # 查找匹配的错误类型
        for error_type, info in ErrorHandler.ERROR_MAP.items():
            if error_type in exc_type or info['pattern'] in exc_str:
                return FriendlyError(
                    message=info['message'],
                    suggestion=info['suggestion'],
                    error_code=info['error_code']
                )
        
        # 默认返回原始错误
        return FriendlyError(
            message=f'发生未知错误: {exc_str}',
            suggestion='请检查日志或联系开发者',
            error_code='E999'
        )
    
    @staticmethod
    def handle_exception(exc, show_details=False):
        """处理异常并输出友好提示"""
        friendly_error = ErrorHandler.analyze_error(exc)
        
        print()
        print('='*60)
        print('⚠️  发生错误')
        print('='*60)
        print(friendly_error)
        print('='*60)
        
        if show_details:
            print('\n📝 详细错误信息:')
            traceback.print_exc()
        
        return friendly_error
    
    @staticmethod
    def log_error(exc, context=None):
        """记录错误日志"""
        friendly_error = ErrorHandler.analyze_error(exc)
        log_entry = {
            'error_type': type(exc).__name__,
            'message': str(exc),
            'friendly_message': friendly_error.message,
            'suggestion': friendly_error.suggestion,
            'error_code': friendly_error.error_code,
            'context': context,
            'traceback': traceback.format_exc()
        }
        
        # 写入日志文件
        try:
            with open('error.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception:
            pass
        
        return log_entry

def main():
    """测试友好错误处理"""
    print('测试友好错误处理...\n')
    
    # 模拟各种错误
    test_cases = [
        ModuleNotFoundError("No module named 'nonexistent_module'"),
        ConnectionRefusedError("Connection refused"),
        TimeoutError("timed out"),
        PermissionError("Permission denied"),
        ValueError("invalid literal for int() with base 10: 'abc'"),
        Exception("Some unknown error")
    ]
    
    for exc in test_cases:
        print(f'原始错误: {exc}')
        friendly_error = ErrorHandler.analyze_error(exc)
        print(friendly_error)
        print()

if __name__ == '__main__':
    main()
