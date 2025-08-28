#!/usr/bin/env python3
"""
FastAPI数据库会话阻塞问题调试
重点分析16秒阻塞的根本原因
"""
import time
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor

def test_get_db_generator():
    """测试get_db生成器的行为"""
    print("🔍 测试get_db生成器性能...")
    
    from app.core.database import get_db
    
    times = []
    for i in range(10):
        start = time.time()
        
        # 模拟FastAPI的依赖注入调用
        db_generator = get_db()
        try:
            db = next(db_generator)
            # 模拟数据库操作
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            
        except Exception as e:
            print(f"❌ get_db测试 {i} 失败: {e}")
        finally:
            try:
                next(db_generator, None)  # 触发finally块
            except StopIteration:
                pass
        
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        print(f"get_db测试 {i}: {elapsed:.1f}ms")
    
    if times:
        avg_time = sum(times) / len(times)
        max_time = max(times)
        print(f"📊 get_db统计: 平均 {avg_time:.1f}ms, 最大 {max_time:.1f}ms")

def test_concurrent_fastapi_sessions():
    """测试并发FastAPI会话（模拟真实场景）"""
    print("\n🔍 测试并发FastAPI会话...")
    
    results = []
    
    def simulate_fastapi_request(request_id: int):
        """模拟单个FastAPI请求"""
        from app.core.database import get_db
        
        start = time.time()
        try:
            # 模拟FastAPI请求处理
            db_generator = get_db()
            db = next(db_generator)
            
            try:
                # 模拟并发检查
                from app.services.concurrency_service import concurrency_service
                from app.models.user import User
                
                user = db.query(User).first()
                if user:
                    allowed, status_info = concurrency_service.check_concurrency_limits(
                        db, user, requested_tasks=12, raise_exception=False
                    )
                
                # 模拟其他数据库操作
                from sqlalchemy import text
                db.execute(text("SELECT COUNT(*) FROM tasks"))
                
                # 模拟任务分页查询
                time.sleep(0.05)  # 模拟查询时间
                
            finally:
                try:
                    next(db_generator, None)  # 触发finally块
                except StopIteration:
                    pass
                    
        except Exception as e:
            print(f"❌ 模拟请求 {request_id} 失败: {e}")
        
        elapsed = (time.time() - start) * 1000
        results.append(elapsed)
        print(f"FastAPI请求 {request_id}: {elapsed:.1f}ms")
        return elapsed
    
    # 使用线程模拟并发FastAPI请求
    threads = []
    start_time = time.time()
    
    for i in range(12):  # 模拟12个并发请求
        t = threading.Thread(target=simulate_fastapi_request, args=(i,))
        threads.append(t)
        t.start()
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    total_time = (time.time() - start_time) * 1000
    
    if results:
        avg_time = sum(results) / len(results)
        max_time = max(results)
        min_time = min(results)
        print(f"📊 并发FastAPI测试: 总耗时 {total_time:.1f}ms")
        print(f"   单请求统计: 平均 {avg_time:.1f}ms, 最大 {max_time:.1f}ms, 最小 {min_time:.1f}ms")

def test_mixed_workload():
    """测试混合工作负载（模拟真实生产场景）"""
    print("\n🔍 测试混合工作负载...")
    
    # 模拟生产环境的混合请求场景
    def batch_task_creation():
        """模拟批量任务创建"""
        from app.core.database import get_independent_db_session, close_independent_db_session
        import asyncio
        
        async def create_task(task_id: int):
            session = get_independent_db_session()
            try:
                from sqlalchemy import text
                session.execute(text("SELECT COUNT(*) FROM tasks"))
                await asyncio.sleep(0.1)  # 模拟任务处理
                session.commit()
            except Exception as e:
                print(f"❌ 批量任务 {task_id} 失败: {e}")
            finally:
                close_independent_db_session(session, f"批量-{task_id}")
        
        # 异步创建12个任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            semaphore = asyncio.Semaphore(5)
            async def controlled_create(task_id: int):
                async with semaphore:
                    return await create_task(task_id)
            
            start = time.time()
            loop.run_until_complete(asyncio.gather(
                *[controlled_create(i) for i in range(12)]
            ))
            elapsed = (time.time() - start) * 1000
            print(f"🚀 批量任务创建完成: {elapsed:.1f}ms")
        finally:
            loop.close()
    
    def concurrent_api_requests():
        """模拟并发API请求"""
        simulate_fastapi_request(99)
    
    # 同时运行批量任务创建和API请求
    batch_thread = threading.Thread(target=batch_task_creation)
    api_threads = [threading.Thread(target=concurrent_api_requests) for _ in range(5)]
    
    start_time = time.time()
    
    # 启动批量任务创建
    batch_thread.start()
    
    # 稍后启动API请求
    time.sleep(0.05)
    for t in api_threads:
        t.start()
    
    # 等待所有完成
    batch_thread.join()
    for t in api_threads:
        t.join()
    
    total_time = (time.time() - start_time) * 1000
    print(f"📊 混合负载测试完成: 总耗时 {total_time:.1f}ms")

def analyze_db_engine_type():
    """分析数据库引擎配置"""
    print("\n🔍 分析数据库引擎配置...")
    
    from app.core.database import engine
    
    print(f"数据库引擎: {type(engine)}")
    print(f"数据库URL: {engine.url}")
    print(f"引擎配置: {engine.url.query}")
    
    # 检查连接池类型
    pool = engine.pool
    print(f"连接池类型: {type(pool)}")
    print(f"连接池类名: {pool.__class__.__name__}")

if __name__ == "__main__":
    print("=" * 60)
    print("🕵️ FastAPI数据库会话阻塞调试")
    print("=" * 60)
    
    analyze_db_engine_type()
    test_get_db_generator()
    test_concurrent_fastapi_sessions()
    test_mixed_workload()
    
    print("=" * 60)
    print("🎯 FastAPI会话调试完成")
    print("=" * 60)