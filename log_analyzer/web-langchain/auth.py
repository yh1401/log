"""用户身份模块 - 简化版

按照需求调整：
1. 暂时移除所有权限限制逻辑
2. 在请求头中通过 X-User-Id 标识用户身份
3. 如未提供则使用默认用户
"""

import json
import secrets
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).parent.parent.parent
AUTH_DIR = PROJECT_ROOT / "log_analyzer" / "auth"
USERS_FILE = AUTH_DIR / "users.json"

AUTH_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_USER_ID = "hanmeimei"
DEFAULT_USERNAME = "hanmeimei"
ADMIN_USERNAME = "useradmin"


@dataclass
class User:
    user_id: str
    username: str
    created_at: str


class UserManager:
    """用户管理（简化版 - 仅维护用户档案，不做权限校验）"""

    def __init__(self):
        self._ensure_files()

    def _ensure_files(self):
        if not USERS_FILE.exists():
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def _load_users(self) -> Dict[str, Dict]:
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def _save_users(self, users: Dict[str, Dict]):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)

    def get_or_create_user(self, user_id: str, username: str = None) -> Dict[str, str]:
        """获取或创建用户档案（无鉴权）"""
        users = self._load_users()

        if user_id in users:
            return users[user_id]

        new_user = {
            "user_id": user_id,
            "username": username or f"用户_{user_id[:8]}",
            "created_at": datetime.now().isoformat()
        }
        users[user_id] = new_user
        self._save_users(users)
        return new_user

    def get_user(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        users = self._load_users()
        return users.get(user_id)

    def list_users(self) -> List[Dict]:
        """列出所有用户"""
        return list(self._load_users().values())

    def is_admin(self, username: str) -> bool:
        """检查用户是否为管理员"""
        return username == ADMIN_USERNAME

    def authenticate_admin(self, user_id: str, username: str = None) -> Dict:
        """验证管理员身份"""
        user_info = self.get_or_create_user(user_id, username)
        if not self.is_admin(user_info.get("username", "")):
            raise PermissionError(f"用户 {user_info.get('username')} 不是管理员，无权访问此接口")
        return user_info


user_manager = UserManager()


# ==================== 管理员认证依赖 ====================

from fastapi import HTTPException, Header


async def require_admin(
    x_user_id: str = Header(None, alias="X-User-Id"),
    x_username: str = Header(None, alias="X-User_Name")
) -> Dict[str, Any]:
    """FastAPI依赖：验证用户是否为管理员
    
    - 通过 X-User-Id 和 X-User_Name 头识别用户身份
    - 验证用户名为 "useradmin"
    - 非管理员用户返回 HTTP 403 Forbidden
    """
    if not x_user_id:
        raise HTTPException(
            status_code=403,
            detail={"code": 403, "message": "未提供用户标识", "data": None}
        )
    
    try:
        user_info = user_manager.authenticate_admin(x_user_id, x_username)
        return user_info
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail={"code": 403, "message": str(e), "data": None}
        )
