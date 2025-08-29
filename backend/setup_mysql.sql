-- MySQL数据库设置脚本
-- 解决MySQL 8.0认证问题并创建专用用户

-- 1. 修复root用户认证方式（MySQL 8.0兼容）
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';

-- 2. 创建专用数据库
CREATE DATABASE IF NOT EXISTS ai_docs_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 3. 创建专用用户（推荐方式）
CREATE USER IF NOT EXISTS 'ai_docs_user'@'localhost' IDENTIFIED WITH mysql_native_password BY 'ai_docs_password';

-- 4. 授予权限
GRANT ALL PRIVILEGES ON ai_docs_db.* TO 'ai_docs_user'@'localhost';

-- 5. 授予创建临时表权限（应用可能需要）
GRANT CREATE TEMPORARY TABLES ON ai_docs_db.* TO 'ai_docs_user'@'localhost';

-- 6. 刷新权限
FLUSH PRIVILEGES;

-- 7. 验证用户创建
SELECT user, host, plugin FROM mysql.user WHERE user IN ('root', 'ai_docs_user');

-- 8. 显示数据库
SHOW DATABASES;