#!/usr/bin/env python3
"""
统一的测试执行入口
提供完整的API测试套件执行和报告生成
"""
import sys
import os
import subprocess
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRunner:
    """测试执行器"""
    
    def __init__(self, test_dir: str = None):
        self.test_dir = test_dir or os.path.dirname(os.path.abspath(__file__))
        self.reports_dir = os.path.join(os.path.dirname(self.test_dir), "data", "test_reports")
        self.ensure_reports_dir()
    
    def ensure_reports_dir(self):
        """确保报告目录存在"""
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def run_all_tests(self, coverage: bool = True, verbose: bool = True) -> Dict:
        """运行所有测试用例"""
        print("🚀 开始执行完整的API测试套件...")
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建pytest命令
        cmd = ["python", "-m", "pytest"]
        cmd.extend(["-v"] if verbose else [])
        
        # 添加覆盖率参数
        if coverage:
            cmd.extend([
                "--cov=app",
                "--cov-report=html:" + os.path.join(self.reports_dir, f"coverage_html_{timestamp}"),
                "--cov-report=json:" + os.path.join(self.reports_dir, f"coverage_{timestamp}.json"),
                "--cov-report=term"
            ])
        
        # 添加JUnit XML报告
        junit_file = os.path.join(self.reports_dir, f"junit_{timestamp}.xml")
        cmd.extend(["--junitxml=" + junit_file])
        
        # 添加JSON报告（如果有pytest-json-report插件）
        json_file = os.path.join(self.reports_dir, f"results_{timestamp}.json")
        cmd.extend(["--json-report", "--json-report-file=" + json_file])
        
        # 指定测试目录
        cmd.append(self.test_dir)
        
        print(f"执行命令: {' '.join(cmd)}")
        
        try:
            # 执行测试
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
            
            # 生成综合报告
            report = self.generate_summary_report(
                timestamp=timestamp,
                junit_file=junit_file,
                json_file=json_file,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
            
            return report
            
        except Exception as e:
            print(f"❌ 测试执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    def run_specific_tests(self, test_pattern: str, **kwargs) -> Dict:
        """运行特定模式的测试"""
        print(f"🎯 运行特定测试: {test_pattern}")
        
        cmd = ["python", "-m", "pytest", "-v"]
        cmd.extend(["-k", test_pattern])
        cmd.append(self.test_dir)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_by_priority(self, priority: str = "P0") -> Dict:
        """按优先级运行测试"""
        priority_patterns = {
            "P0": "test_*_success or test_get_* or test_create_* or test_login_*",
            "P1": "test_*_performance or test_*_concurrent",
            "security": "test_*_security or test_*_injection or test_*_xss",
            "e2e": "test_*_workflow or test_*_complete"
        }
        
        pattern = priority_patterns.get(priority, priority)
        return self.run_specific_tests(pattern)
    
    def generate_summary_report(self, timestamp: str, junit_file: str, json_file: str,
                              stdout: str, stderr: str, return_code: int) -> Dict:
        """生成综合测试报告"""
        print("📊 生成测试报告...")
        
        # 解析JUnit XML报告
        junit_stats = self.parse_junit_report(junit_file)
        
        # 解析JSON报告（如果存在）
        json_stats = self.parse_json_report(json_file)
        
        # 生成HTML报告
        html_report = self.generate_html_report(
            timestamp, junit_stats, json_stats, stdout, stderr
        )
        
        # 生成汇总报告
        summary_report = {
            "timestamp": timestamp,
            "success": return_code == 0,
            "return_code": return_code,
            "statistics": junit_stats or json_stats,
            "reports": {
                "html": html_report,
                "junit": junit_file if os.path.exists(junit_file) else None,
                "json": json_file if os.path.exists(json_file) else None
            },
            "output": {
                "stdout": stdout,
                "stderr": stderr
            }
        }
        
        # 保存汇总报告
        summary_file = os.path.join(self.reports_dir, f"summary_{timestamp}.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 测试报告已生成: {summary_file}")
        return summary_report
    
    def parse_junit_report(self, junit_file: str) -> Optional[Dict]:
        """解析JUnit XML报告"""
        if not os.path.exists(junit_file):
            return None
        
        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            return {
                "total": int(root.attrib.get("tests", 0)),
                "passed": int(root.attrib.get("tests", 0)) - int(root.attrib.get("failures", 0)) - int(root.attrib.get("errors", 0)),
                "failed": int(root.attrib.get("failures", 0)),
                "errors": int(root.attrib.get("errors", 0)),
                "skipped": int(root.attrib.get("skipped", 0)),
                "time": float(root.attrib.get("time", 0.0))
            }
        except Exception as e:
            print(f"⚠️  解析JUnit报告失败: {e}")
            return None
    
    def parse_json_report(self, json_file: str) -> Optional[Dict]:
        """解析JSON报告"""
        if not os.path.exists(json_file):
            return None
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            summary = data.get("summary", {})
            return {
                "total": summary.get("total", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "errors": summary.get("error", 0),
                "skipped": summary.get("skipped", 0),
                "time": data.get("duration", 0.0)
            }
        except Exception as e:
            print(f"⚠️  解析JSON报告失败: {e}")
            return None
    
    def generate_html_report(self, timestamp: str, junit_stats: Dict,
                           json_stats: Dict, stdout: str, stderr: str) -> str:
        """生成HTML可视化报告"""
        stats = junit_stats or json_stats or {}
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API测试报告 - {timestamp}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .stats-container {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); flex: 1; min-width: 200px; }}
        .stat-number {{ font-size: 2em; font-weight: bold; margin-bottom: 5px; }}
        .passed {{ color: #4CAF50; }}
        .failed {{ color: #f44336; }}
        .skipped {{ color: #ff9800; }}
        .total {{ color: #2196F3; }}
        .section {{ background: white; margin: 20px 0; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .progress-bar {{ background: #f0f0f0; border-radius: 10px; overflow: hidden; height: 20px; margin: 10px 0; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #4CAF50, #8BC34A); transition: width 0.3s ease; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        .error {{ color: #d32f2f; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 AI文档测试系统 - API测试报告</h1>
        <p>生成时间: {timestamp}</p>
    </div>
    
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-number total">{stats.get('total', 0)}</div>
            <div>总测试数</div>
        </div>
        <div class="stat-card">
            <div class="stat-number passed">{stats.get('passed', 0)}</div>
            <div>通过</div>
        </div>
        <div class="stat-card">
            <div class="stat-number failed">{stats.get('failed', 0)}</div>
            <div>失败</div>
        </div>
        <div class="stat-card">
            <div class="stat-number skipped">{stats.get('skipped', 0)}</div>
            <div>跳过</div>
        </div>
    </div>
    
    <div class="section">
        <h2>📈 测试通过率</h2>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {(stats.get('passed', 0) / max(stats.get('total', 1), 1)) * 100}%"></div>
        </div>
        <p>通过率: {(stats.get('passed', 0) / max(stats.get('total', 1), 1) * 100):.1f}% ({stats.get('passed', 0)}/{stats.get('total', 0)})</p>
        <p>执行时间: {stats.get('time', 0):.2f}秒</p>
    </div>
    
    <div class="section">
        <h2>📋 测试覆盖范围</h2>
        <ul>
            <li>✅ 系统API测试 (SystemView)</li>
            <li>✅ 认证API测试 (AuthView)</li>
            <li>✅ 任务API测试 (TaskView)</li>
            <li>✅ 用户API测试 (UserView)</li>
            <li>✅ AI输出API测试 (AIOutputView)</li>
            <li>✅ 问题反馈API测试 (IssueView)</li>
            <li>✅ 任务日志API测试 (TaskLogView)</li>
            <li>✅ E2E端到端流程测试</li>
            <li>✅ 权限隔离测试</li>
            <li>✅ 并发处理测试</li>
            <li>✅ 性能测试</li>
            <li>✅ 安全测试</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>🔧 测试执行详情</h2>
        <h3>标准输出:</h3>
        <pre>{stdout}</pre>
        {f'<h3 class="error">错误输出:</h3><pre class="error">{stderr}</pre>' if stderr else ''}
    </div>
    
    <div class="section">
        <h2>📁 报告文件</h2>
        <ul>
            <li>HTML报告: coverage_html_{timestamp}/index.html</li>
            <li>JUnit XML: junit_{timestamp}.xml</li>
            <li>JSON报告: results_{timestamp}.json</li>
            <li>汇总报告: summary_{timestamp}.json</li>
        </ul>
    </div>
</body>
</html>
        """
        
        html_file = os.path.join(self.reports_dir, f"report_{timestamp}.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_file
    
    def install_dependencies(self):
        """安装测试依赖"""
        print("📦 安装测试依赖...")
        
        deps = [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0", 
            "pytest-xvfb>=2.0.0",
            "pytest-json-report>=1.5.0",
            "requests>=2.28.0",
            "websocket-client>=1.0.0"
        ]
        
        for dep in deps:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                             check=True, capture_output=True)
                print(f"✅ 已安装: {dep}")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  安装失败: {dep} - {e}")
    
    def check_server_status(self, base_url: str = None):
        """检查服务器状态"""
        if base_url is None:
            from app.core.config import get_settings
            settings = get_settings()
            base_url = settings.server_external_url
        
        try:
            import requests
            response = requests.get(f"{base_url}/", timeout=5)
            if response.status_code == 200:
                print(f"✅ 服务器运行正常: {base_url}")
                return True
            else:
                print(f"⚠️  服务器状态异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 无法连接到服务器: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI文档测试系统 API测试执行器")
    parser.add_argument("--coverage", action="store_true", default=True, help="启用代码覆盖率检查")
    parser.add_argument("--no-coverage", action="store_true", help="禁用代码覆盖率检查")
    parser.add_argument("--verbose", "-v", action="store_true", default=True, help="详细输出")
    parser.add_argument("--pattern", "-k", help="测试模式过滤")
    parser.add_argument("--priority", choices=["P0", "P1", "security", "e2e"], help="按优先级运行测试")
    parser.add_argument("--install-deps", action="store_true", help="安装测试依赖")
    parser.add_argument("--check-server", action="store_true", help="检查服务器状态")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # 安装依赖
    if args.install_deps:
        runner.install_dependencies()
        return
    
    # 检查服务器
    if args.check_server:
        runner.check_server_status()
        return
    
    # 执行测试
    coverage = args.coverage and not args.no_coverage
    
    if args.pattern:
        result = runner.run_specific_tests(args.pattern)
        print("测试结果:", "通过" if result["success"] else "失败")
        print(result["stdout"])
        if result["stderr"]:
            print("错误:", result["stderr"])
    
    elif args.priority:
        result = runner.run_by_priority(args.priority)
        print("测试结果:", "通过" if result["success"] else "失败")
        print(result["stdout"])
        if result["stderr"]:
            print("错误:", result["stderr"])
    
    else:
        # 运行完整测试套件
        result = runner.run_all_tests(coverage=coverage, verbose=args.verbose)
        
        if result.get("success"):
            print("🎉 所有测试执行完成!")
            stats = result.get("statistics", {})
            print(f"📊 测试统计: {stats.get('passed', 0)}/{stats.get('total', 0)} 通过")
            print(f"📁 报告位置: {result.get('reports', {}).get('html', '无')}")
        else:
            print("❌ 测试执行失败!")
            if result.get("error"):
                print(f"错误: {result['error']}")
        
        return 0 if result.get("success", False) else 1


if __name__ == "__main__":
    sys.exit(main())