#!/usr/bin/env python3
"""
数据库迁移命令行工具

用法:
    python migrate.py --help                    # 显示帮助
    python migrate.py status                    # 显示迁移状态
    python migrate.py create "添加新表"          # 创建新的迁移文件
    python migrate.py auto "自动检测变更"        # 自动生成迁移脚本
    python migrate.py up                        # 执行所有待迁移
    python migrate.py up --target 20231201_001  # 执行到指定迁移
    python migrate.py down 20231201_001         # 回滚指定迁移
    python migrate.py backup                    # 创建数据库备份
    python migrate.py restore backup.db         # 恢复数据库备份
    python migrate.py history                   # 显示迁移历史

环境变量:
    CONFIG_FILE: 指定配置文件路径
    
示例:
    CONFIG_FILE=config.test.yaml python migrate.py up
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Optional
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from migrations.migration_manager import MigrationManager, MigrationRecord


class MigrationCLI:
    """迁移命令行接口"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.migration_manager = None
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _get_manager(self) -> MigrationManager:
        """获取迁移管理器"""
        if not self.migration_manager:
            self.migration_manager = MigrationManager(self.config_file)
        return self.migration_manager
    
    def status(self):
        """显示迁移状态"""
        manager = self._get_manager()
        
        print("=== 数据库迁移状态 ===")
        
        # 显示数据库信息
        db_url = manager._mask_database_url(getattr(manager.settings, 'database_url', '未知'))
        db_type = getattr(manager.settings, 'database_type', '未知')
        print(f"数据库类型: {db_type}")
        print(f"数据库连接: {db_url}")
        print()
        
        # 显示待执行的迁移
        pending = manager.get_pending_migrations()
        if pending:
            print(f"待执行的迁移 ({len(pending)} 个):")
            for migration_id in pending:
                print(f"  - {migration_id}")
        else:
            print("✅ 所有迁移已执行，数据库为最新状态")
        
        print()
        
        # 显示最近执行的迁移
        history = manager.get_migration_history()
        if history:
            print(f"最近执行的迁移 (最新 5 个):")
            for record in history[:5]:
                status_icon = "✅" if record.executed_at else "⏳"
                exec_time = record.executed_at.strftime('%Y-%m-%d %H:%M:%S') if record.executed_at else "未执行"
                print(f"  {status_icon} {record.id} - {record.description} ({exec_time})")
        else:
            print("暂无迁移历史")
    
    def create(self, description: str, sql_up: str = "", sql_down: str = ""):
        """创建新的迁移文件"""
        if not description:
            print("❌ 错误: 必须提供迁移描述")
            return
        
        if not sql_up:
            print("请输入升级SQL (按Ctrl+D或Ctrl+Z结束):")
            sql_up_lines = []
            try:
                while True:
                    line = input()
                    sql_up_lines.append(line)
            except EOFError:
                sql_up = '\n'.join(sql_up_lines)
        
        if not sql_down and sql_up:
            print("请输入降级SQL (可选，按Ctrl+D或Ctrl+Z结束):")
            sql_down_lines = []
            try:
                while True:
                    line = input()
                    sql_down_lines.append(line)
            except EOFError:
                sql_down = '\n'.join(sql_down_lines)
        
        manager = self._get_manager()
        migration_id = manager.create_migration(description, sql_up, sql_down)
        
        print(f"✅ 成功创建迁移文件: {migration_id}")
        print(f"文件位置: migrations/versions/{migration_id}.py")
        print("请检查并编辑迁移文件，然后运行 'python migrate.py up' 执行迁移")
    
    def auto_generate(self, description: str = None):
        """自动生成迁移脚本"""
        manager = self._get_manager()
        
        print("🔍 检测数据库结构变更...")
        migration_id = manager.auto_generate_migration(description)
        
        if migration_id:
            print(f"✅ 成功生成迁移文件: {migration_id}")
            print(f"文件位置: migrations/versions/{migration_id}.py")
            print("请检查迁移文件，然后运行 'python migrate.py up' 执行迁移")
        else:
            print("ℹ️ 未检测到数据库结构变更")
    
    def migrate_up(self, target: str = None, no_backup: bool = False):
        """执行迁移"""
        manager = self._get_manager()
        
        if target:
            print(f"🚀 执行迁移到: {target}")
            # TODO: 实现指定目标的迁移
            print("❌ 暂不支持指定目标迁移，请使用 'python migrate.py up' 执行所有待迁移")
        else:
            print("🚀 执行所有待迁移...")
            
            # 显示待执行的迁移
            pending = manager.get_pending_migrations()
            if not pending:
                print("✅ 没有待执行的迁移")
                return
            
            print(f"将执行以下 {len(pending)} 个迁移:")
            for migration_id in pending:
                print(f"  - {migration_id}")
            
            # 确认执行
            if not self._confirm("确认执行以上迁移吗？"):
                print("❌ 迁移已取消")
                return
            
            try:
                executed_count = manager.migrate_to_latest(create_backup=not no_backup)
                print(f"✅ 成功执行 {executed_count} 个迁移")
            except Exception as e:
                print(f"❌ 迁移执行失败: {e}")
                sys.exit(1)
    
    def migrate_down(self, migration_id: str):
        """回滚迁移"""
        if not migration_id:
            print("❌ 错误: 必须指定要回滚的迁移ID")
            return
        
        manager = self._get_manager()
        
        print(f"⚠️ 警告: 即将回滚迁移 {migration_id}")
        print("此操作可能导致数据丢失，建议先创建备份")
        
        if not self._confirm("确认回滚此迁移吗？"):
            print("❌ 回滚已取消")
            return
        
        try:
            manager.rollback_migration(migration_id)
            print(f"✅ 成功回滚迁移: {migration_id}")
        except Exception as e:
            print(f"❌ 回滚失败: {e}")
            sys.exit(1)
    
    def create_backup(self, name: str = None):
        """创建数据库备份"""
        manager = self._get_manager()
        
        print("💾 创建数据库备份...")
        
        try:
            backup_path = manager.create_backup(name)
            print(f"✅ 备份创建成功: {backup_path}")
        except Exception as e:
            print(f"❌ 备份创建失败: {e}")
            sys.exit(1)
    
    def restore_backup(self, backup_path: str):
        """恢复数据库备份"""
        if not backup_path:
            print("❌ 错误: 必须指定备份文件路径")
            return
        
        if not os.path.exists(backup_path):
            print(f"❌ 错误: 备份文件不存在: {backup_path}")
            return
        
        manager = self._get_manager()
        
        print(f"⚠️ 警告: 即将恢复备份 {backup_path}")
        print("此操作将覆盖当前数据库，所有未保存的数据将丢失")
        
        if not self._confirm("确认恢复此备份吗？"):
            print("❌ 恢复已取消")
            return
        
        try:
            manager.restore_backup(backup_path)
            print(f"✅ 数据库恢复成功")
        except Exception as e:
            print(f"❌ 恢复失败: {e}")
            sys.exit(1)
    
    def show_history(self, limit: int = 20):
        """显示迁移历史"""
        manager = self._get_manager()
        history = manager.get_migration_history()
        
        if not history:
            print("暂无迁移历史")
            return
        
        print(f"=== 迁移历史 (最新 {min(limit, len(history))} 条) ===")
        print()
        
        for record in history[:limit]:
            status_icon = "✅" if record.executed_at else "⏳"
            exec_time = record.executed_at.strftime('%Y-%m-%d %H:%M:%S') if record.executed_at else "未执行"
            backup_info = f" (备份: {record.backup_path})" if record.backup_path else ""
            
            print(f"{status_icon} {record.id}")
            print(f"   描述: {record.description}")
            print(f"   执行时间: {exec_time}{backup_info}")
            if record.checksum:
                print(f"   校验和: {record.checksum[:16]}...")
            print()
    
    def _confirm(self, message: str) -> bool:
        """确认提示"""
        try:
            response = input(f"{message} (y/N): ").lower().strip()
            return response in ['y', 'yes']
        except KeyboardInterrupt:
            print("\n❌ 操作已取消")
            sys.exit(1)
    
    def cleanup(self):
        """清理资源"""
        if self.migration_manager:
            self.migration_manager.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数据库迁移工具', formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument('--config', help='配置文件路径')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # status 命令
    subparsers.add_parser('status', help='显示迁移状态')
    
    # create 命令
    create_parser = subparsers.add_parser('create', help='创建新的迁移文件')
    create_parser.add_argument('description', help='迁移描述')
    create_parser.add_argument('--sql-up', help='升级SQL文件路径')
    create_parser.add_argument('--sql-down', help='降级SQL文件路径')
    
    # auto 命令
    auto_parser = subparsers.add_parser('auto', help='自动生成迁移脚本')
    auto_parser.add_argument('description', nargs='?', help='迁移描述（可选）')
    
    # up 命令
    up_parser = subparsers.add_parser('up', help='执行迁移')
    up_parser.add_argument('--target', help='目标迁移ID')
    up_parser.add_argument('--no-backup', action='store_true', help='不创建备份')
    
    # down 命令
    down_parser = subparsers.add_parser('down', help='回滚迁移')
    down_parser.add_argument('migration_id', help='要回滚的迁移ID')
    
    # backup 命令
    backup_parser = subparsers.add_parser('backup', help='创建数据库备份')
    backup_parser.add_argument('name', nargs='?', help='备份名称（可选）')
    
    # restore 命令
    restore_parser = subparsers.add_parser('restore', help='恢复数据库备份')
    restore_parser.add_argument('backup_path', help='备份文件路径')
    
    # history 命令
    history_parser = subparsers.add_parser('history', help='显示迁移历史')
    history_parser.add_argument('--limit', type=int, default=20, help='显示数量限制')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 创建CLI实例
    cli = MigrationCLI(args.config)
    
    try:
        # 执行对应的命令
        if args.command == 'status':
            cli.status()
        elif args.command == 'create':
            sql_up = ""
            sql_down = ""
            if args.sql_up and os.path.exists(args.sql_up):
                with open(args.sql_up, 'r', encoding='utf-8') as f:
                    sql_up = f.read()
            if args.sql_down and os.path.exists(args.sql_down):
                with open(args.sql_down, 'r', encoding='utf-8') as f:
                    sql_down = f.read()
            cli.create(args.description, sql_up, sql_down)
        elif args.command == 'auto':
            cli.auto_generate(args.description)
        elif args.command == 'up':
            cli.migrate_up(args.target, args.no_backup)
        elif args.command == 'down':
            cli.migrate_down(args.migration_id)
        elif args.command == 'backup':
            cli.create_backup(args.name)
        elif args.command == 'restore':
            cli.restore_backup(args.backup_path)
        elif args.command == 'history':
            cli.show_history(args.limit)
    
    except KeyboardInterrupt:
        print("\n❌ 操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        sys.exit(1)
    finally:
        cli.cleanup()


if __name__ == '__main__':
    main()