#!/usr/bin/env python3
"""
批量任务创建性能调试脚本
分析FastAPI会话16秒阻塞的根本原因
"""
import time
import asyncio
import threading
from app.core.database import SessionLocal, get_independent_db_session, close_independent_db_session
from app.core.db_monitor import get_monitor
from app.services.concurrency_service import concurrency_service

def test_db_session_creation():
    """测试数据库会话创建性能"""
    print("🔍 测试数据库会话创建性能...")
    
    times = []
    for i in range(10):
        start = time.time()
        session = SessionLocal()
        try:
            # 执行健康检查
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
            session.commit()
        except Exception as e:
            print(f"❌ 会话 {i} 健康检查失败: {e}")
        finally:
            session.close()
        
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        print(f"会话 {i}: {elapsed:.1f}ms")
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    print(f"📊 会话创建统计: 平均 {avg_time:.1f}ms, 最大 {max_time:.1f}ms")

async def test_concurrent_db_sessions():
    """测试并发数据库会话创建"""
    print("🔍 测试并发数据库会话创建...")
    
    async def create_session_task(task_id: int):
        start = time.time()
        session = get_independent_db_session()
        try:
            from sqlalchemy import text
            # 模拟一些数据库操作
            session.execute(text("SELECT COUNT(*) FROM tasks"))
            result = session.fetchone()
            await asyncio.sleep(0.1)  # 模拟处理时间
            
        except Exception as e:
            print(f"❌ 并发会话 {task_id} 失败: {e}")
        finally:
            close_independent_db_session(session, f"并发测试-{task_id}")
        
        elapsed = (time.time() - start) * 1000
        print(f"并发会话 {task_id}: {elapsed:.1f}ms")
        return elapsed
    
    # 创建12个并发会话（模拟批量创建12个任务）
    start_time = time.time()
    results = await asyncio.gather(
        *[create_session_task(i) for i in range(12)],
        return_exceptions=True
    )
    total_time = (time.time() - start_time) * 1000
    
    successful_results = [r for r in results if not isinstance(r, Exception)]
    avg_time = sum(successful_results) / len(successful_results) if successful_results else 0
    
    print(f"📊 并发会话测试: 总耗时 {total_time:.1f}ms, 平均单会话 {avg_time:.1f}ms")

def test_concurrency_check_performance():
    """测试并发检查的性能"""
    print("🔍 测试并发检查性能...")
    
    from app.models.user import User
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # 模拟用户对象
        user = db.query(User).first()
        if not user:
            print("❌ 没有找到测试用户")
            return
        
        times = []
        for i in range(10):
            start = time.time()
            try:
                allowed, status_info = concurrency_service.check_concurrency_limits(
                    db, user, requested_tasks=12, raise_exception=False
                )
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
                print(f"并发检查 {i}: {elapsed:.1f}ms, 允许: {allowed}")
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                print(f"并发检查 {i} 失败: {elapsed:.1f}ms, 错误: {e}")
        
        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)
            print(f"📊 并发检查统计: 平均 {avg_time:.1f}ms, 最大 {max_time:.1f}ms")
    
    finally:
        db.close()

def test_connection_pool_behavior():
    """测试连接池行为"""
    print("🔍 测试连接池行为...")
    
    print("测试开始")
    
    sessions = []
    try:
        # 创建多个会话观察连接池行为
        for i in range(15):
            start = time.time()
            session = SessionLocal()
            elapsed = (time.time() - start) * 1000
            sessions.append(session)
            print(f"创建会话 {i}: {elapsed:.1f}ms")
            print(f"创建会话 {i}")
            
            if elapsed > 1000:  # 超过1秒的会话创建
                print(f"⚠️ 会话 {i} 创建耗时过长: {elapsed:.1f}ms")
    
    finally:
        # 关闭所有会话
        for i, session in enumerate(sessions):
            start = time.time()
            session.close()
            elapsed = (time.time() - start) * 1000
            print(f"关闭会话 {i}: {elapsed:.1f}ms")
            print(f"关闭会话 {i}")

async def test_full_batch_simulation():
    """完整模拟批量任务创建流程"""
    print("🔍 完整模拟批量任务创建流程...")
    
    from app.models.user import User
    
    # 获取FastAPI会话（模拟请求开始）
    session_start = time.time()
    from app.core.database import get_db
    
    db_generator = get_db()
    db = next(db_generator)
    
    try:
        # 1. 获取用户（模拟认证）
        auth_start = time.time()
        user = db.query(User).first()
        auth_time = (time.time() - auth_start) * 1000
        print(f"📝 用户认证耗时: {auth_time:.1f}ms")
        
        if not user:
            print("❌ 没有找到测试用户")
            return
        
        # 2. 并发检查（模拟批量创建前的检查）
        concurrency_start = time.time()
        allowed, status_info = concurrency_service.check_concurrency_limits(
            db, user, requested_tasks=12, raise_exception=False
        )
        concurrency_time = (time.time() - concurrency_start) * 1000
        print(f"🔒 并发检查耗时: {concurrency_time:.1f}ms, 允许: {allowed}")
        
        # 3. 模拟批量任务创建的并发数据库操作
        batch_start = time.time()
        
        async def simulate_task_creation(task_id: int):
            """模拟单个任务创建"""
            task_start = time.time()
            independent_session = get_independent_db_session()
            try:
                # 模拟任务创建的数据库操作
                from sqlalchemy import text
                independent_session.execute(text("SELECT COUNT(*) FROM tasks"))
                independent_session.execute(text("SELECT COUNT(*) FROM users"))
                
                # 模拟文件保存和数据库插入
                await asyncio.sleep(0.05)  # 模拟I/O操作
                
                independent_session.commit()
                
            except Exception as e:
                print(f"❌ 模拟任务 {task_id} 创建失败: {e}")
                independent_session.rollback()
            finally:
                close_independent_db_session(independent_session, f"模拟任务-{task_id}")
            
            task_time = (time.time() - task_start) * 1000
            return task_time
        
        # 并发创建12个任务
        semaphore = asyncio.Semaphore(5)  # 匹配实际的max_concurrent
        
        async def controlled_create(task_id: int):
            async with semaphore:
                return await simulate_task_creation(task_id)
        
        results = await asyncio.gather(
            *[controlled_create(i) for i in range(12)],
            return_exceptions=True
        )
        
        batch_time = (time.time() - batch_start) * 1000
        print(f"⚡ 批量任务创建模拟耗时: {batch_time:.1f}ms")
        
        # 分析结果
        successful_times = [r for r in results if not isinstance(r, Exception)]
        if successful_times:
            avg_task_time = sum(successful_times) / len(successful_times)
            max_task_time = max(successful_times)
            print(f"📊 单任务创建统计: 平均 {avg_task_time:.1f}ms, 最大 {max_task_time:.1f}ms")
        
        failed_count = len([r for r in results if isinstance(r, Exception)])
        print(f"📊 任务创建结果: 成功 {len(successful_times)}, 失败 {failed_count}")
        
    except Exception as e:
        print(f"❌ 完整流程模拟失败: {e}")
        
    finally:
        # 关闭FastAPI会话
        try:
            next(db_generator, None)  # 触发finally块
        except StopIteration:
            pass
        
        session_time = (time.time() - session_start) * 1000
        print(f"🎯 FastAPI会话总耗时: {session_time:.1f}ms")
        
        # 打印最终的连接池状态
        get_monitor().print_status("测试完成")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 批量任务创建性能调试分析")
    print("=" * 60)
    
    # 1. 测试基础会话性能
    test_db_session_creation()
    print()
    
    # 2. 测试连接池行为
    test_connection_pool_behavior()
    print()
    
    # 3. 测试并发检查性能
    test_concurrency_check_performance()
    print()
    
    # 4. 测试并发会话创建
    asyncio.run(test_concurrent_db_sessions())
    print()
    
    # 5. 完整流程模拟
    asyncio.run(test_full_batch_simulation())
    
    print("=" * 60)
    print("🎯 调试分析完成")
    print("=" * 60)