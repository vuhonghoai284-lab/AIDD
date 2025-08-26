#!/usr/bin/env python3
"""
高并发压力测试运行脚本

使用方法:
  python run_stress_tests.py                    # 运行所有压力测试
  python run_stress_tests.py --concurrent       # 只运行并发测试
  python run_stress_tests.py --performance      # 只运行性能基准测试
  python run_stress_tests.py --resource         # 只运行资源竞争测试
  python run_stress_tests.py --quick            # 快速测试模式
  python run_stress_tests.py --report           # 生成详细报告
"""

import argparse
import subprocess
import sys
import time
import os
from datetime import datetime
from pathlib import Path


def run_pytest_command(test_path: str, markers: str = None, extra_args: list = None) -> tuple:
    """
    运行pytest命令
    
    Args:
        test_path: 测试文件路径
        markers: pytest标记
        extra_args: 额外参数
    
    Returns:
        (return_code, output)
    """
    cmd = ["python", "-m", "pytest"]
    
    if markers:
        cmd.extend(["-m", markers])
    
    cmd.extend([
        test_path,
        "-v", 
        "--tb=short",
        "--disable-warnings"
    ])
    
    if extra_args:
        cmd.extend(extra_args)
    
    print(f"🚀 执行命令: {' '.join(cmd)}")
    print("="*60)
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30分钟超时
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        print(f"\n⏱️ 测试耗时: {duration:.2f}秒")
        print(f"🎯 返回码: {result.returncode}")
        
        return result.returncode, result.stdout
        
    except subprocess.TimeoutExpired:
        print("❌ 测试超时 (30分钟)")
        return 1, "Test timed out after 30 minutes"
    
    except Exception as e:
        print(f"❌ 执行测试时出错: {e}")
        return 1, str(e)


def run_concurrent_tests(quick_mode: bool = False):
    """运行并发测试"""
    print("🔄 开始并发任务执行测试...")
    
    extra_args = []
    if quick_mode:
        # 快速模式：减少并发数量和测试时间
        extra_args = ["-k", "not test_mixed_concurrent_operations"]
    
    return run_pytest_command(
        "tests/stress/test_concurrent_task_execution.py",
        "stress",
        extra_args
    )


def run_performance_tests(quick_mode: bool = False):
    """运行性能基准测试"""
    print("📊 开始性能基准测试...")
    
    extra_args = []
    if quick_mode:
        # 快速模式：只运行基础性能测试
        extra_args = ["-k", "test_task_creation_benchmark or test_task_query_benchmark"]
    
    return run_pytest_command(
        "tests/stress/test_performance_benchmarks.py",
        "stress",
        extra_args
    )


def run_resource_tests(quick_mode: bool = False):
    """运行资源竞争测试"""
    print("🔒 开始资源竞争测试...")
    
    extra_args = []
    if quick_mode:
        # 快速模式：只运行ID唯一性测试
        extra_args = ["-k", "test_concurrent_task_id_generation"]
    
    return run_pytest_command(
        "tests/stress/test_resource_contention.py", 
        "stress",
        extra_args
    )


def generate_report(test_results: dict):
    """生成测试报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"stress_test_report_{timestamp}.md"
    
    print(f"\n📝 生成测试报告: {report_file}")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 高并发压力测试报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 测试概述\n\n")
        f.write("本报告包含了系统在高并发情况下的性能表现和稳定性测试结果。\n\n")
        
        f.write("## 测试结果\n\n")
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, (return_code, output) in test_results.items():
            total_tests += 1
            status = "✅ 通过" if return_code == 0 else "❌ 失败"
            if return_code == 0:
                passed_tests += 1
            
            f.write(f"### {test_name}\n\n")
            f.write(f"**状态**: {status}\n\n")
            
            if return_code == 0:
                # 从输出中提取关键指标
                lines = output.split('\n')
                metrics_lines = [line for line in lines if '📊' in line or 'passed' in line]
                if metrics_lines:
                    f.write("**关键指标**:\n")
                    for line in metrics_lines[-10:]:  # 最后10行指标
                        if line.strip():
                            f.write(f"- {line.strip()}\n")
                    f.write("\n")
            else:
                f.write(f"**错误信息**:\n```\n{output}\n```\n\n")
        
        f.write("## 总结\n\n")
        f.write(f"- **总测试数**: {total_tests}\n")
        f.write(f"- **通过测试**: {passed_tests}\n")
        f.write(f"- **失败测试**: {total_tests - passed_tests}\n")
        f.write(f"- **成功率**: {passed_tests/total_tests*100:.1f}%\n\n")
        
        if passed_tests == total_tests:
            f.write("🎉 所有压力测试均已通过！系统在高并发场景下表现良好。\n")
        else:
            f.write("⚠️ 部分测试失败，请检查系统性能和稳定性。\n")
        
        f.write(f"\n---\n")
        f.write(f"*报告由 run_stress_tests.py 自动生成*\n")
    
    print(f"📄 报告已保存到: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="运行高并发压力测试")
    parser.add_argument("--concurrent", action="store_true", help="只运行并发测试")
    parser.add_argument("--performance", action="store_true", help="只运行性能基准测试")
    parser.add_argument("--resource", action="store_true", help="只运行资源竞争测试")
    parser.add_argument("--quick", action="store_true", help="快速测试模式")
    parser.add_argument("--report", action="store_true", help="生成详细报告")
    
    args = parser.parse_args()
    
    # 确保在正确的目录下
    if not Path("tests/stress").exists():
        print("❌ 错误: 请在包含 tests/stress 目录的项目根目录下运行此脚本")
        sys.exit(1)
    
    print("🎯 高并发压力测试开始")
    print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.quick:
        print("⚡ 运行模式: 快速测试")
    print("="*60)
    
    test_results = {}
    
    try:
        # 运行选定的测试
        if args.concurrent or not any([args.concurrent, args.performance, args.resource]):
            print("\n" + "="*60)
            return_code, output = run_concurrent_tests(args.quick)
            test_results["并发任务执行测试"] = (return_code, output)
        
        if args.performance or not any([args.concurrent, args.performance, args.resource]):
            print("\n" + "="*60)
            return_code, output = run_performance_tests(args.quick)
            test_results["性能基准测试"] = (return_code, output)
        
        if args.resource or not any([args.concurrent, args.performance, args.resource]):
            print("\n" + "="*60)
            return_code, output = run_resource_tests(args.quick)
            test_results["资源竞争测试"] = (return_code, output)
        
        # 汇总结果
        print("\n" + "="*60)
        print("📊 测试结果汇总:")
        
        all_passed = True
        for test_name, (return_code, _) in test_results.items():
            status = "✅ 通过" if return_code == 0 else "❌ 失败"
            print(f"   {test_name}: {status}")
            if return_code != 0:
                all_passed = False
        
        if args.report:
            generate_report(test_results)
        
        print("\n" + "="*60)
        if all_passed:
            print("🎉 所有压力测试通过！")
            sys.exit(0)
        else:
            print("⚠️ 部分测试失败，请检查日志")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 运行测试时出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()