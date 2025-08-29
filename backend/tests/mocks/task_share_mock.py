"""
任务分享Mock服务
用于测试环境模拟任务分享功能，规避实现依赖问题
"""
from typing import List, Dict, Any, Optional
from unittest.mock import Mock
from datetime import datetime, timedelta


class MockTaskShareService:
    """Mock任务分享服务"""
    
    def __init__(self):
        self.shares = {}  # {share_id: share_data}
        self.task_shares = {}  # {task_id: [share_ids]}
        self.user_shares = {}  # {user_id: [share_ids]}
        self.next_share_id = 1
        
    def create_share(self, task_id: int, owner_id: int, shared_user_ids: List[int], 
                    permission_level: str = "read", share_comment: str = "") -> Dict[str, Any]:
        """创建任务分享"""
        # 模拟业务验证
        if not shared_user_ids:
            return {"success_count": 0, "failed_count": 1, "created_shares": [], 
                   "errors": ["没有有效的用户ID"]}
        
        # 模拟用户验证
        valid_users = []
        errors = []
        
        for user_id in shared_user_ids:
            if user_id == owner_id:
                errors.append(f"不能分享给自己 (用户ID: {user_id})")
            elif user_id > 10:  # 模拟用户不存在
                errors.append(f"用户不存在 (用户ID: {user_id})")
            else:
                valid_users.append(user_id)
        
        # 创建分享记录
        created_shares = []
        for user_id in valid_users:
            share_id = self.next_share_id
            self.next_share_id += 1
            
            share_data = {
                "id": share_id,
                "task_id": task_id,
                "owner_id": owner_id,
                "shared_user_id": user_id,
                "permission_level": permission_level,
                "share_comment": share_comment,
                "is_active": True,
                "shared_at": datetime.utcnow().isoformat(),
                "owner_name": "test_admin",
                "shared_user_name": f"test_user_{user_id}"
            }
            
            self.shares[share_id] = share_data
            
            # 维护索引
            if task_id not in self.task_shares:
                self.task_shares[task_id] = []
            self.task_shares[task_id].append(share_id)
            
            if user_id not in self.user_shares:
                self.user_shares[user_id] = []
            self.user_shares[user_id].append(share_id)
            
            created_shares.append(share_data)
        
        return {
            "success_count": len(created_shares),
            "failed_count": len(errors),
            "created_shares": created_shares,
            "errors": errors
        }
    
    def get_task_shares(self, task_id: int, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """获取任务的分享列表"""
        if task_id not in self.task_shares:
            return []
        
        shares = []
        for share_id in self.task_shares[task_id]:
            share_data = self.shares[share_id]
            if include_inactive or share_data["is_active"]:
                shares.append(share_data)
        
        return shares
    
    def get_user_shared_tasks(self, user_id: int, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """获取分享给用户的任务列表"""
        if user_id not in self.user_shares:
            return []
        
        tasks = []
        for share_id in self.user_shares[user_id]:
            share_data = self.shares[share_id]
            if include_inactive or share_data["is_active"]:
                task_data = {
                    "task_id": share_data["task_id"],
                    "task_title": f"Task {share_data['task_id']}",
                    "permission_level": share_data["permission_level"],
                    "shared_at": share_data["shared_at"],
                    "owner_name": share_data["owner_name"]
                }
                tasks.append(task_data)
        
        return tasks
    
    def update_share(self, share_id: int, owner_id: int, permission_level: str = None, 
                    share_comment: str = None) -> Optional[Dict[str, Any]]:
        """更新分享权限"""
        if share_id not in self.shares:
            return None
        
        share = self.shares[share_id]
        if share["owner_id"] != owner_id:
            return None
        
        if permission_level:
            share["permission_level"] = permission_level
        if share_comment is not None:
            share["share_comment"] = share_comment
        
        share["updated_at"] = datetime.utcnow().isoformat()
        return share
    
    def delete_share(self, share_id: int, owner_id: int, permanently: bool = False) -> bool:
        """删除或撤销分享"""
        if share_id not in self.shares:
            return False
        
        share = self.shares[share_id]
        if share["owner_id"] != owner_id:
            return False
        
        if permanently:
            del self.shares[share_id]
            # 从索引中移除
            for task_shares in self.task_shares.values():
                if share_id in task_shares:
                    task_shares.remove(share_id)
            for user_shares in self.user_shares.values():
                if share_id in user_shares:
                    user_shares.remove(share_id)
        else:
            share["is_active"] = False
            share["revoked_at"] = datetime.utcnow().isoformat()
        
        return True
    
    def search_users(self, query: str, exclude_user_id: int, limit: int = 20) -> List[Any]:
        """搜索用户 - 返回User对象"""
        from app.models.user import User
        from datetime import datetime
        
        # 模拟用户搜索结果
        mock_users = []
        for i in range(2, min(limit + 2, 10)):
            if i != exclude_user_id:
                user = User(
                    id=i,
                    uid=f"test_user_{i}",
                    display_name=f"Test User {i}",
                    email=f"user{i}@test.com",
                    avatar_url=f"https://avatar.example.com/user{i}.jpg",
                    is_admin=False,
                    is_system_admin=False,
                    created_at=datetime.utcnow()
                )
                mock_users.append(user)
        
        # 根据查询过滤
        if query.lower() == "test":
            return mock_users
        elif "user" in query.lower():
            return mock_users[:limit//2]
        else:
            return []
    
    def get_share_stats(self, user_id: int) -> Dict[str, Any]:
        """获取用户分享统计"""
        user_shares_count = 0
        active_shares_count = 0
        permission_breakdown = {"read": 0, "write": 0, "admin": 0}
        
        # 统计用户作为分享者的分享
        for share in self.shares.values():
            if share["owner_id"] == user_id:
                user_shares_count += 1
                if share["is_active"]:
                    active_shares_count += 1
                    permission = share["permission_level"]
                    if permission in permission_breakdown:
                        permission_breakdown[permission] += 1
        
        return {
            "total_shares": user_shares_count,
            "active_shares": active_shares_count,
            "permission_breakdown": permission_breakdown
        }


# 全局Mock实例
mock_task_share_service = MockTaskShareService()


def get_mock_task_share_service():
    """获取Mock任务分享服务实例"""
    return mock_task_share_service