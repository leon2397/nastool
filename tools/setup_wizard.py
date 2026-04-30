#!/usr/bin/env python3
"""NASTool 配置向导"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SetupWizard:
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
        self.settings_path = os.path.join(self.config_dir, 'settings.json')
        os.makedirs(self.config_dir, exist_ok=True)
    
    def run(self):
        """运行配置向导"""
        print('='*60)
        print('🚀 NASTool 配置向导')
        print('='*60)
        print('\n欢迎使用NASTool配置向导！')
        print('本向导将帮助您完成首次配置。\n')
        
        # 检查现有配置
        if os.path.exists(self.settings_path):
            print('⚠️ 发现已有配置文件')
            choice = input('是否重新配置? [y/N]: ').strip().lower()
            if choice != 'y':
                print('取消配置')
                return
        
        # 开始配置
        settings = {}
        
        # 基础配置
        print('\n--- 基础配置 ---')
        settings['default_test_mode'] = self._ask_choice(
            '默认测试模式',
            [('quick', '快速诊断'), ('full', '完整诊断'), ('network', '网络专项'), ('hardware', '硬件专项')],
            'quick'
        )
        
        settings['parallel_test'] = self._ask_yes_no('是否启用并行测试?', True)
        settings['max_parallel'] = int(input('最大并行数 (默认: 5): ') or '5')
        
        # 报告配置
        print('\n--- 报告配置 ---')
        settings['auto_export_report'] = self._ask_yes_no('测试完成后自动导出报告?', False)
        settings['report_format'] = self._ask_choice(
            '默认报告格式',
            [('json', 'JSON'), ('html', 'HTML')],
            'json'
        )
        
        # 网络配置
        print('\n--- 网络配置 ---')
        settings['default_subnet'] = input('默认扫描子网 (默认: 192.168.1.): ') or '192.168.1.'
        settings['ping_count'] = int(input('Ping测试次数 (默认: 3): ') or '3')
        
        # 保存配置
        self._save_settings(settings)
        
        print('\n🎉 配置完成!')
        print('='*60)
        self._show_settings(settings)
    
    def _ask_choice(self, prompt, options, default):
        """询问选择"""
        print(f'{prompt}:')
        for i, (key, desc) in enumerate(options, 1):
            default_marker = ' (默认)' if key == default else ''
            print(f'  {i}. {desc}{default_marker}')
        
        while True:
            choice = input('输入选择: ').strip()
            if choice == '':
                return default
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                return options[int(choice)-1][0]
            print('无效选择，请重试')
    
    def _ask_yes_no(self, prompt, default):
        """询问是/否"""
        default_text = 'Y/n' if default else 'y/N'
        choice = input(f'{prompt} [{default_text}]: ').strip().lower()
        if choice == '':
            return default
        return choice == 'y'
    
    def _save_settings(self, settings):
        """保存配置"""
        with open(self.settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        print(f'✅ 配置已保存到 {self.settings_path}')
    
    def _show_settings(self, settings):
        """显示配置"""
        print('\n当前配置:')
        for key, value in settings.items():
            print(f'  {key}: {value}')
    
    def get_settings(self):
        """获取配置"""
        if os.path.exists(self.settings_path):
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._get_default_settings()
    
    def _get_default_settings(self):
        """获取默认配置"""
        return {
            'default_test_mode': 'quick',
            'parallel_test': True,
            'max_parallel': 5,
            'auto_export_report': False,
            'report_format': 'json',
            'default_subnet': '192.168.1.',
            'ping_count': 3
        }

def main():
    """命令行接口"""
    wizard = SetupWizard()
    
    import argparse
    parser = argparse.ArgumentParser(description='NASTool 配置向导')
    parser.add_argument('--show', action='store_true', help='显示当前配置')
    
    args = parser.parse_args()
    
    if args.show:
        settings = wizard.get_settings()
        print('='*60)
        print('📋 当前配置')
        print('='*60)
        for key, value in settings.items():
            print(f'  {key}: {value}')
        print('='*60)
    else:
        wizard.run()

if __name__ == '__main__':
    main()
