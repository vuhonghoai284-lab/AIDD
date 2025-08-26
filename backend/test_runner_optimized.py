#!/usr/bin/env python3
"""
优化的测试执行器
支持分层测试执行和性能监控
"""
import subprocess
import sys
import time
import argparse
from typing import List, Dict, Any

class OptimizedTestRunner:
    """优化的pytest测试运行器"""
    
    def __init__(self):
        self.test_categories = {
            'fast': {
                'description': '快速单元测试 (< 30秒)',
                'markers': 'unit and not slow and not integration',
                'timeout': 30
            },
            'unit': {
                'description': '所有单元测试',
                'markers': 'unit and not stress and not e2e',
                'timeout': 60
            },
            'integration': {
                'description': '集成测试',
                'markers': 'integration and not stress',
                'timeout': 120
            },
            'api': {
                'description': 'API接口测试',
                'paths': ['tests/test_*api*.py'],
                'timeout': 90
            },
            'auth': {
                'description': '认证相关测试',
                'markers': 'auth',
                'timeout': 60
            },
            'task': {
                'description': '任务相关测试（不含压力测试）',
                'markers': 'task and not stress and not load',
                'timeout': 120
            },
            'performance': {
                'description': '性能测试',
                'markers': 'performance',
                'timeout': 180
            },
            'stress': {
                'description': '压力和负载测试',
                'markers': 'stress or load',
                'timeout': 300
            },
            'e2e': {
                'description': '端到端测试',
                'markers': 'e2e',
                'timeout': 240
            }
        }
    
    def run_category(self, category: str, extra_args: List[str] = None) -> Dict[str, Any]:
        """运行指定类别的测试"""
        if category not in self.test_categories:
            raise ValueError(f"未知测试类别: {category}")
        
        config = self.test_categories[category]
        print(f"\n🚀 执行 {category} 测试: {config['description']}")
        
        # 构建pytest命令
        cmd = [
            sys.executable, '-m', 'pytest',
            '--tb=short',
            '--disable-warnings', 
            '-v',
            '--maxfail=5',
            '--durations=5',
            '-q'
        ]
        
        # 添加标记过滤
        if 'markers' in config:
            cmd.extend(['-m', config['markers']])
        
        # 添加路径过滤  
        if 'paths' in config:
            cmd.extend(config['paths'])
        
        # 添加额外参数
        if extra_args:
            cmd.extend(extra_args)
        
        # 执行测试
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config['timeout']
            )
            duration = time.time() - start_time
            
            return {
                'category': category,
                'success': result.returncode == 0,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                'category': category,
                'success': False,
                'duration': duration,
                'error': f'测试超时 ({config["timeout"]}s)',
                'returncode': -1
            }
    
    def run_fast_suite(self) -> Dict[str, Any]:
        """运行快速测试套件"""
        print("⚡ 执行快速测试套件...")
        
        # 只运行标记为fast的测试
        cmd = [
            sys.executable, '-m', 'pytest',
            '--tb=line',
            '--disable-warnings',
            '-q',
            '--maxfail=3',
            '-x',  # 遇到失败立即停止
            '-m', 'fast or (unit and not slow and not integration)',
            'tests/unit/',
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        duration = time.time() - start_time
        
        return {
            'category': 'fast_suite',
            'success': result.returncode == 0,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    
    def run_smoke_tests(self) -> Dict[str, Any]:
        """运行冒烟测试"""
        print("💨 执行冒烟测试...")
        
        smoke_tests = [
            'tests/test_system_api.py::TestSystemAPI::test_root_endpoint',
            'tests/test_model_initialization.py::TestModelInitialization::test_test_mode_models_config',
            'tests/test_auth_api.py::TestAuthAPI::test_system_admin_login_success',
            'tests/test_task_api.py::TestTaskCRUDAPI::test_create_task_success',
        ]
        
        cmd = [
            sys.executable, '-m', 'pytest',
            '--tb=line',
            '--disable-warnings',
            '-v',
            '--maxfail=1',
            '-x',
        ] + smoke_tests
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        duration = time.time() - start_time
        
        return {
            'category': 'smoke',
            'success': result.returncode == 0,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    
    def run_parallel_if_available(self, category: str) -> Dict[str, Any]:
        """如果可能，使用并行执行"""
        try:
            import pytest_xdist
            extra_args = ['-n', 'auto', '--dist', 'loadfile']
            print(f"🔥 使用并行执行 {category} 测试")
            return self.run_category(category, extra_args)
        except ImportError:
            print(f"📝 串行执行 {category} 测试 (pytest-xdist未安装)")
            return self.run_category(category)
    
    def print_results(self, results: List[Dict[str, Any]]):
        """打印测试结果摘要"""
        print("\n" + "="*60)
        print("📊 测试执行摘要")
        print("="*60)
        
        total_duration = 0
        total_success = 0
        
        for result in results:
            status = "✅ 成功" if result['success'] else "❌ 失败"
            duration = result['duration']
            total_duration += duration
            if result['success']:
                total_success += 1
                
            print(f"{status} | {result['category']:15} | {duration:6.1f}s")
            
            if not result['success'] and result.get('error'):
                print(f"     错误: {result['error']}")
        
        print("-" * 60)
        print(f"总计: {total_success}/{len(results)} 成功, 耗时: {total_duration:.1f}s")
        
        if total_success == len(results):
            print("🎉 所有测试通过!")
        else:
            print("⚠️  有测试失败，请检查输出")
    
    def run_progressive_tests(self):
        """渐进式测试执行"""
        print("🚀 开始渐进式测试执行...")
        results = []
        
        # 1. 冒烟测试
        smoke_result = self.run_smoke_tests()
        results.append(smoke_result)
        if not smoke_result['success']:
            print("❌ 冒烟测试失败，停止执行")
            self.print_results(results)
            return False
        
        # 2. 快速单元测试
        fast_result = self.run_fast_suite()
        results.append(fast_result)
        if not fast_result['success']:
            print("❌ 快速测试失败，停止执行")
            self.print_results(results)
            return False
            
        # 3. API测试
        api_result = self.run_category('api')
        results.append(api_result)
        
        # 4. 任务相关测试（不包含压力测试）
        if api_result['success']:
            task_result = self.run_category('task')
            results.append(task_result)
        
        self.print_results(results)
        return all(r['success'] for r in results)


def main():
    parser = argparse.ArgumentParser(description='优化的pytest测试执行器')
    parser.add_argument('mode', nargs='?', default='progressive',
                       choices=['progressive', 'smoke', 'fast', 'unit', 'integration', 
                               'api', 'auth', 'task', 'performance', 'stress', 'e2e', 'full'],
                       help='测试执行模式')
    parser.add_argument('--parallel', action='store_true', help='启用并行执行')
    parser.add_argument('--timeout', type=int, help='自定义超时时间')
    
    args = parser.parse_args()
    
    runner = OptimizedTestRunner()
    
    if args.mode == 'progressive':
        success = runner.run_progressive_tests()
        sys.exit(0 if success else 1)
    elif args.mode == 'smoke':
        result = runner.run_smoke_tests()
    elif args.mode == 'fast':
        result = runner.run_fast_suite()
    elif args.mode == 'full':
        # 执行所有测试类别
        results = []
        for category in ['unit', 'integration', 'api', 'auth', 'task']:
            if args.parallel:
                result = runner.run_parallel_if_available(category)
            else:
                result = runner.run_category(category)
            results.append(result)
        runner.print_results(results)
        sys.exit(0 if all(r['success'] for r in results) else 1)
    else:
        if args.parallel:
            result = runner.run_parallel_if_available(args.mode)
        else:
            result = runner.run_category(args.mode)
    
    if args.mode not in ['progressive', 'full']:
        runner.print_results([result])
        sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()