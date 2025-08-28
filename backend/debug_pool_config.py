#!/usr/bin/env python3
"""
数据库连接池配置调试脚本
分析连接池配置和实际行为的差异
"""
from app.core.config import get_settings
from app.core.database import engine, get_engine_config

def debug_config():
    """调试配置加载"""
    print("🔍 分析数据库配置...")
    
    settings = get_settings()
    print(f"数据库类型: {settings.database_type}")
    print(f"数据库URL: {settings.database_url}")
    print(f"数据库配置: {settings.database_config}")
    
    engine_config = get_engine_config()
    print(f"引擎配置: {engine_config}")
    
    print(f"\n🔗 连接池实际配置:")
    pool = engine.pool
    print(f"  pool.size(): {pool.size()}")
    print(f"  pool._max_overflow: {getattr(pool, '_max_overflow', 'N/A')}")
    print(f"  pool._timeout: {getattr(pool, '_timeout', 'N/A')}")
    print(f"  pool._recycle: {getattr(pool, '_recycle', 'N/A')}")
    
    print(f"\n🔗 连接池当前状态:")
    print(f"  checkedin(): {pool.checkedin()}")
    print(f"  checkedout(): {pool.checkedout()}")
    print(f"  overflow(): {pool.overflow()}")
    print(f"  size(): {pool.size()}")

def test_pool_overflow():
    """测试连接池溢出行为"""
    print("\n🔍 测试连接池溢出行为...")
    
    from app.core.database import SessionLocal, _log_connection_pool_status
    
    sessions = []
    try:
        # 创建超过池大小的连接数
        for i in range(30):
            start = time.time()
            session = SessionLocal()
            elapsed = (time.time() - start) * 1000
            sessions.append(session)
            
            _log_connection_pool_status(f"创建会话-{i}")
            
            # 检查是否出现阻塞
            if elapsed > 1000:
                print(f"⚠️ 会话 {i} 创建阻塞: {elapsed:.1f}ms")
            
            # 如果创建耗时过长，提前停止
            if elapsed > 5000:
                print(f"🚨 检测到严重阻塞，停止测试")
                break
                
    finally:
        # 逐个关闭会话
        for i, session in enumerate(sessions):
            session.close()
            _log_connection_pool_status(f"关闭会话-{i}")

def test_concurrent_access():
    """测试并发访问模式"""
    print("\n🔍 测试并发访问模式...")
    
    import threading
    import time
    
    results = []
    
    def worker_thread(thread_id: int):
        """工作线程"""
        from app.core.database import get_independent_db_session, close_independent_db_session
        
        start = time.time()
        try:
            session = get_independent_db_session()
            try:
                from sqlalchemy import text
                session.execute(text("SELECT COUNT(*) FROM tasks"))
                time.sleep(0.1)  # 模拟处理
            finally:
                close_independent_db_session(session, f"线程-{thread_id}")
        except Exception as e:
            print(f"❌ 线程 {thread_id} 失败: {e}")
        
        elapsed = (time.time() - start) * 1000
        results.append(elapsed)
        print(f"线程 {thread_id}: {elapsed:.1f}ms")
    
    # 创建12个线程并发访问
    threads = []
    start_time = time.time()
    
    for i in range(12):
        t = threading.Thread(target=worker_thread, args=(i,))
        threads.append(t)
        t.start()
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    total_time = (time.time() - start_time) * 1000
    
    if results:
        avg_time = sum(results) / len(results)
        max_time = max(results)
        print(f"📊 线程并发测试: 总耗时 {total_time:.1f}ms, 平均单线程 {avg_time:.1f}ms, 最大 {max_time:.1f}ms")

if __name__ == "__main__":
    import time
    
    print("=" * 60)
    print("🔍 数据库连接池配置调试分析")  
    print("=" * 60)
    
    debug_config()
    test_pool_overflow()
    test_concurrent_access()
    
    print("=" * 60)
    print("🎯 连接池调试完成")
    print("=" * 60)