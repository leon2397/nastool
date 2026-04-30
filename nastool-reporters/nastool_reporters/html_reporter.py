#!/usr/bin/env python3
"""
HTML报告生成器 - 可视化诊断报告
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

class HTMLReporter:
    """HTML报告生成器"""
    
    def __init__(self):
        self.data = {}
    
    def load_data(self, data: Dict[str, Any]):
        """加载诊断数据"""
        self.data = data
    
    def generate_html(self, output_path: str = None) -> str:
        """生成HTML报告"""
        html = self._generate_header()
        html += self._generate_summary()
        html += self._generate_system_info()
        html += self._generate_network_info()
        html += self._generate_hardware_info()
        html += self._generate_dependencies_info()
        html += self._generate_footer()
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
        
        return html
    
    def _generate_header(self) -> str:
        """生成HTML头部"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NASTool 诊断报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f7fa; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .card {{ background: white; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); padding: 24px; margin-bottom: 20px; }}
        .card-title {{ font-size: 18px; font-weight: 600; color: #2d3748; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #e2e8f0; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }}
        .metric {{ background: #f8fafc; border-radius: 8px; padding: 16px; text-align: center; }}
        .metric-value {{ font-size: 28px; font-weight: 700; color: #667eea; }}
        .metric-label {{ font-size: 14px; color: #718096; margin-top: 4px; }}
        .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
        .status-ok {{ background: #c6f6d5; color: #22543d; }}
        .status-warning {{ background: #feebc8; color: #744210; }}
        .status-error {{ background: #fed7d7; color: #742a2a; }}
        .table {{ width: 100%; border-collapse: collapse; }}
        .table th, .table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        .table th {{ background: #f8fafc; font-weight: 600; color: #4a5568; }}
        .table tr:hover {{ background: #f8fafc; }}
        .progress-bar {{ height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 4px; }}
        .issue-item {{ background: #fff5f5; border-left: 4px solid #fc8181; padding: 12px; margin-bottom: 8px; border-radius: 0 4px 4px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #a0aec0; font-size: 14px; }}
        .score-circle {{ width: 120px; height: 120px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto; font-size: 32px; font-weight: 700; }}
        .score-high {{ background: linear-gradient(135deg, #68d391 0%, #48bb78 100%); color: white; }}
        .score-medium {{ background: linear-gradient(135deg, #f6e05e 0%, #ecc94b 100%); color: #744210; }}
        .score-low {{ background: linear-gradient(135deg, #fc8181 0%, #f56565 100%); color: white; }}
        .chip-badge {{ display: inline-block; padding: 4px 8px; background: #e6fffa; color: #319795; border-radius: 4px; font-size: 12px; margin-right: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 NASTool 系统诊断报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
"""
    
    def _generate_summary(self) -> str:
        """生成摘要部分"""
        overall_score = self.data.get('overall_score', 75)
        check_count = self.data.get('check_count', 0)
        pass_count = self.data.get('pass_count', 0)
        warning_count = self.data.get('warning_count', 0)
        error_count = self.data.get('error_count', 0)
        
        score_class = 'score-high' if overall_score >= 80 else 'score-medium' if overall_score >= 60 else 'score-low'
        
        return f"""        <div class="card">
            <div class="card-title">📊 诊断摘要</div>
            <div class="grid">
                <div class="metric">
                    <div class="{score_class} score-circle">{overall_score}</div>
                    <div class="metric-label">综合评分</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{check_count}</div>
                    <div class="metric-label">检测项总数</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #48bb78;">{pass_count}</div>
                    <div class="metric-label">通过</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #ecc94b;">{warning_count}</div>
                    <div class="metric-label">警告</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #f56565;">{error_count}</div>
                    <div class="metric-label">错误</div>
                </div>
            </div>
        </div>
"""
    
    def _generate_system_info(self) -> str:
        """生成系统信息部分"""
        system = self.data.get('system', {})
        python = self.data.get('python', {})
        
        return f"""        <div class="card">
            <div class="card-title">🖥️ 系统信息</div>
            <table class="table">
                <tr><th>项目</th><th>值</th></tr>
                <tr><td>操作系统</td><td>{system.get('os', '未知')}</td></tr>
                <tr><td>平台</td><td>{system.get('platform', '未知')}</td></tr>
                <tr><td>架构</td><td><span class="chip-badge">{system.get('architecture', '未知')}</span></td></tr>
                <tr><td>主机名</td><td>{system.get('hostname', '未知')}</td></tr>
                <tr><td>Python版本</td><td>{python.get('version', '未知')} <span class="status-badge {'status-ok' if python.get('ok') else 'status-error'}">{python.get('ok') and '支持' or '不支持'}</span></td></tr>
            </table>
        </div>
"""
    
    def _generate_network_info(self) -> str:
        """生成网络信息部分"""
        network = self.data.get('network', {})
        connectivity = network.get('connectivity', [])
        ping = network.get('ping_stability', {})
        
        return f"""        <div class="card">
            <div class="card-title">🌐 网络诊断</div>
            
            <h4 style="margin-bottom: 12px; color: #4a5568;">连接性测试</h4>
            <table class="table">
                <tr><th>目标</th><th>状态</th><th>延迟</th></tr>
                {''.join([f'<tr><td>{c.get("name")}</td><td><span class="status-badge {"status-ok" if c.get("connected") else "status-error"}">{c.get("connected") and "连接成功" or "连接失败"}</span></td><td>{c.get("latency_ms") or "-"}ms</td></tr>' for c in connectivity])}
            </table>
            
            <h4 style="margin-top: 20px; margin-bottom: 12px; color: #4a5568;">Ping稳定性</h4>
            <table class="table">
                <tr><th>项目</th><th>值</th></tr>
                <tr><td>目标</td><td>{ping.get('target', '未知')}</td></tr>
                <tr><td>发送/接收</td><td>{ping.get('sent', 0)}/{ping.get('received', 0)}</td></tr>
                <tr><td>丢包率</td><td>{ping.get('loss_rate', 0):.1f}%</td></tr>
                <tr><td>延迟范围</td><td>{ping.get('min_latency') or '-'}ms - {ping.get('max_latency') or '-'}ms</td></tr>
            </table>
        </div>
"""
    
    def _generate_hardware_info(self) -> str:
        """生成硬件信息部分"""
        hardware = self.data.get('hardware', {})
        devices = hardware.get('devices', [])
        
        if not devices:
            return f"""        <div class="card">
            <div class="card-title">🤖 AI硬件检测</div>
            <p style="color: #a0aec0;">未检测到AI加速硬件</p>
        </div>
"""
        
        return f"""        <div class="card">
            <div class="card-title">🤖 AI硬件检测</div>
            <p style="margin-bottom: 16px;">检测到 {hardware.get('device_count', 0)} 个设备，总算力 {hardware.get('total_tops', 0)} TOPS</p>
            
            <table class="table">
                <tr><th>设备</th><th>芯片</th><th>温度</th><th>功耗</th><th>健康状态</th></tr>
                {''.join([f'<tr><td>NPU {d.get("npu_id")}</td><td><span class="chip-badge">{d.get("chip_name")}</span></td><td>{d.get("temperature_c") or "-"}C</td><td>{d.get("power_w") or "-"}W</td><td><span class="status-badge {"status-ok" if d.get("health") == "OK" else "status-error"}">{d.get("health") or "未知"}</span></td></tr>' for d in devices])}
            </table>
        </div>
"""
    
    def _generate_dependencies_info(self) -> str:
        """生成依赖信息部分"""
        deps = self.data.get('dependencies', {})
        missing = deps.get('missing', [])
        
        return f"""        <div class="card">
            <div class="card-title">📦 依赖状态</div>
            <p>已安装: {deps.get('installed', 0)}/{deps.get('required', 0)}</p>
            
            {missing and f'<div style="margin-top: 12px;">' + ''.join([f'<div class="issue-item">❌ 缺失依赖: {m}</div>' for m in missing]) + '</div>' or ''}
        </div>
"""
    
    def _generate_footer(self) -> str:
        """生成页脚"""
        return """    </div>
    <div class="footer">
        <p>Generated by NASTool v4.2</p>
    </div>
</body>
</html>"""

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='生成HTML诊断报告')
    parser.add_argument('--input', '-i', required=True, help='输入JSON文件')
    parser.add_argument('--output', '-o', required=True, help='输出HTML文件')
    args = parser.parse_args()
    
    # 加载诊断数据
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 生成报告
    reporter = HTMLReporter()
    reporter.load_data(data)
    reporter.generate_html(args.output)
    
    print(f"✅ HTML报告已生成: {args.output}")

if __name__ == "__main__":
    main()
