-- 任务队列表迁移脚本
-- 支持20用户x3并发=60个并发任务的数据库队列

-- 创建任务队列表
CREATE TABLE IF NOT EXISTS task_queue (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id INT NOT NULL,
    user_id INT NOT NULL,
    priority INT DEFAULT 5 COMMENT '优先级：1-10，数值越大优先级越高',
    status ENUM('queued', 'processing', 'completed', 'failed', 'cancelled') DEFAULT 'queued',
    worker_id VARCHAR(50) NULL COMMENT '处理该任务的工作者ID',
    queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '入队时间',
    started_at TIMESTAMP NULL COMMENT '开始处理时间', 
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    attempts INT DEFAULT 0 COMMENT '已尝试次数',
    max_attempts INT DEFAULT 3 COMMENT '最大重试次数',
    error_message TEXT NULL COMMENT '错误信息',
    task_data JSON NULL COMMENT '任务数据快照',
    estimated_duration INT DEFAULT 300 COMMENT '预估处理时长(秒)',
    
    -- 索引优化
    INDEX idx_status_priority_queued (status, priority DESC, queued_at ASC) COMMENT '队列处理优化索引',
    INDEX idx_user_status (user_id, status) COMMENT '用户任务状态查询索引',
    INDEX idx_worker_processing (worker_id, status) COMMENT '工作者状态查询索引',
    INDEX idx_queued_at (queued_at) COMMENT '时间范围查询索引',
    
    -- 外键约束
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务队列表 - 支持20用户x3并发任务调度';

-- SQLite版本（开发环境）
-- CREATE TABLE IF NOT EXISTS task_queue (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     task_id INTEGER NOT NULL,
--     user_id INTEGER NOT NULL,
--     priority INTEGER DEFAULT 5,
--     status TEXT CHECK(status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')) DEFAULT 'queued',
--     worker_id TEXT,
--     queued_at TEXT DEFAULT CURRENT_TIMESTAMP,
--     started_at TEXT,
--     completed_at TEXT,
--     attempts INTEGER DEFAULT 0,
--     max_attempts INTEGER DEFAULT 3,
--     error_message TEXT,
--     task_data TEXT,
--     estimated_duration INTEGER DEFAULT 300,
--     FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
--     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
-- );

-- 创建队列配置表
CREATE TABLE IF NOT EXISTS queue_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='队列配置表';

-- 插入默认队列配置
INSERT IGNORE INTO queue_config (config_key, config_value, description) VALUES
('max_concurrent_users', '20', '系统最大支持并发用户数'),
('user_max_concurrent_tasks', '3', '单用户最大并发任务数'),
('system_max_concurrent_tasks', '60', '系统总最大并发任务数(20用户x3)'),
('worker_pool_size', '20', '工作者池大小'),
('queue_check_interval', '2', '队列检查间隔(秒)'),
('task_timeout', '600', '任务超时时间(秒)'),
('max_queue_length', '200', '最大队列长度'),
('priority_boost_threshold', '300', '等待超过此秒数的任务优先级自动提升');

-- 创建队列统计视图（便于监控）
CREATE OR REPLACE VIEW queue_statistics AS
SELECT 
    status,
    COUNT(*) as count,
    AVG(TIMESTAMPDIFF(SECOND, queued_at, COALESCE(started_at, NOW()))) as avg_wait_time,
    MAX(TIMESTAMPDIFF(SECOND, queued_at, COALESCE(started_at, NOW()))) as max_wait_time
FROM task_queue 
WHERE queued_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
GROUP BY status;