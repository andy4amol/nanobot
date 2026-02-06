"""UserConfig 管理器 - 用户配置和数据管理"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class UserWatchlist:
    """用户关注列表"""
    stocks: List[str] = field(default_factory=list)           # 股票代码
    influencers: List[str] = field(default_factory=list)      # 大V账号
    keywords: List[str] = field(default_factory=list)         # 关键词
    sectors: List[str] = field(default_factory=list)          # 行业板块
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> "UserWatchlist":
        if not data:
            return cls()
        return cls(
            stocks=data.get("stocks", []),
            influencers=data.get("influencers", []),
            keywords=data.get("keywords", []),
            sectors=data.get("sectors", [])
        )


@dataclass
class UserPreferences:
    """用户偏好设置"""
    report_frequency: str = "daily"       # "daily", "weekly", "realtime", "both"
    report_time: str = "09:00"           # 报告生成时间
    report_format: str = "markdown"     # "markdown", "pdf", "html"
    language: str = "zh"                # "zh", "en"
    max_report_length: int = 5000         # 最大报告长度
    notification_channels: List[str] = field(default_factory=lambda: ["push"])
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def default(cls) -> "UserPreferences":
        return cls()
    
    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> "UserPreferences":
        if not data:
            return cls.default()
        
        # 过滤掉无效的字段
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)


@dataclass
class UserConfig:
    """完整用户配置"""
    user_id: str
    created_at: str
    updated_at: str
    watchlist: UserWatchlist
    preferences: UserPreferences
    custom_data: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "watchlist": self.watchlist.to_dict(),
            "preferences": self.preferences.to_dict(),
            "custom_data": self.custom_data,
            "version": self.version
        }
    
    @classmethod
    def create(cls, user_id: str, initial_data: Optional[Dict] = None) -> "UserConfig":
        """创建新用户配置"""
        now = datetime.now().isoformat()
        custom_data = initial_data or {}
        
        return cls(
            user_id=user_id,
            created_at=now,
            updated_at=now,
            watchlist=UserWatchlist(),
            preferences=UserPreferences.default(),
            custom_data=custom_data
        )
    
    @classmethod
    def from_dict(cls, data: Dict) -> "UserConfig":
        """从字典创建配置"""
        return cls(
            user_id=data["user_id"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            watchlist=UserWatchlist.from_dict(data.get("watchlist")),
            preferences=UserPreferences.from_dict(data.get("preferences")),
            custom_data=data.get("custom_data", {}),
            version=data.get("version", "1.0")
        )
    
    def update_watchlist(self, **kwargs) -> None:
        """更新关注列表"""
        for key, value in kwargs.items():
            if hasattr(self.watchlist, key):
                setattr(self.watchlist, key, value)
        self.updated_at = datetime.now().isoformat()
    
    def update_preferences(self, **kwargs) -> None:
        """更新偏好设置"""
        for key, value in kwargs.items():
            if hasattr(self.preferences, key):
                setattr(self.preferences, key, value)
        self.updated_at = datetime.now().isoformat()
    
    def set_custom_data(self, key: str, value: Any) -> None:
        """设置自定义数据"""
        self.custom_data[key] = value
        self.updated_at = datetime.now().isoformat()


class UserConfigManager:
    """
    用户配置管理器
    
    负责：
    1. 用户配置的 CRUD 操作
    2. 配置的持久化存储
    3. 批量操作支持
    """
    
    def __init__(self, base_path: str = "~/.nanobot/workspaces"):
        """
        初始化 UserConfigManager
        
        Args:
            base_path: Workspace 基础路径
        """
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        print(f"[UserConfigManager] 基础路径: {self.base_path}")
    
    def _get_config_path(self, user_id: str) -> Path:
        """获取用户配置文件路径"""
        workspace = self.base_path / f"user_{user_id}"
        workspace.mkdir(exist_ok=True)
        return workspace / "config.json"
    
    def get_config(self, user_id: str) -> Optional[UserConfig]:
        """
        获取用户配置
        
        Args:
            user_id: 用户 ID
            
        Returns:
            UserConfig 对象，不存在则返回 None
        """
        config_path = self._get_config_path(user_id)
        if not config_path.exists():
            return None
        
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return UserConfig.from_dict(data)
        except Exception as e:
            print(f"[UserConfigManager] 加载配置失败 {user_id}: {e}")
            return None
    
    def save_config(self, config: UserConfig) -> None:
        """
        保存用户配置
        
        Args:
            config: UserConfig 对象
        """
        config_path = self._get_config_path(config.user_id)
        config.updated_at = datetime.now().isoformat()
        
        try:
            config_path.write_text(
                json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[UserConfigManager] 保存配置失败 {config.user_id}: {e}")
            raise
    
    def create_user(
        self, 
        user_id: str, 
        initial_data: Optional[Dict] = None
    ) -> UserConfig:
        """
        创建新用户
        
        Args:
            user_id: 用户 ID
            initial_data: 初始数据
            
        Returns:
            新创建的 UserConfig
        """
        # 检查是否已存在
        if self.get_config(user_id):
            raise ValueError(f"User {user_id} already exists")
        
        # 创建配置
        config = UserConfig.create(user_id, initial_data)
        
        # 保存
        self.save_config(config)
        
        print(f"[UserConfigManager] 创建用户 {user_id} 成功")
        return config
    
    def update_watchlist(
        self, 
        user_id: str, 
        watchlist_data: Dict[str, List[str]]
    ) -> Optional[UserConfig]:
        """
        更新用户关注列表
        
        Args:
            user_id: 用户 ID
            watchlist_data: 关注列表数据
            
        Returns:
            更新后的 UserConfig，用户不存在则返回 None
        """
        config = self.get_config(user_id)
        if not config:
            return None
        
        # 更新关注列表
        for key, value in watchlist_data.items():
            if hasattr(config.watchlist, key):
                setattr(config.watchlist, key, value)
        
        # 保存
        self.save_config(config)
        
        print(f"[UserConfigManager] 更新用户 {user_id} 关注列表成功")
        return config
    
    def update_preferences(
        self, 
        user_id: str, 
        prefs_data: Dict[str, Any]
    ) -> Optional[UserConfig]:
        """
        更新用户偏好
        
        Args:
            user_id: 用户 ID
            prefs_data: 偏好数据
            
        Returns:
            更新后的 UserConfig，用户不存在则返回 None
        """
        config = self.get_config(user_id)
        if not config:
            return None
        
        # 更新偏好
        for key, value in prefs_data.items():
            if hasattr(config.preferences, key):
                setattr(config.preferences, key, value)
        
        # 保存
        self.save_config(config)
        
        print(f"[UserConfigManager] 更新用户 {user_id} 偏好成功")
        return config
    
    def delete_user(self, user_id: str) -> bool:
        """
        删除用户
        
        Args:
            user_id: 用户 ID
            
        Returns:
            是否删除成功
        """
        config_path = self._get_config_path(user_id)
        if not config_path.exists():
            return False
        
        # 删除 workspace（UserConfigManager 不直接管理，但通知）
        # 实际删除由 WorkspaceManager 处理
        
        print(f"[UserConfigManager] 用户 {user_id} 配置已标记删除")
        return True
    
    def list_users(self) -> List[str]:
        """
        列出所有用户
        
        Returns:
            用户 ID 列表
        """
        users = []
        for item in self.base_path.iterdir():
            if item.is_dir() and item.name.startswith("user_"):
                # 只移除开头的 "user_" 前缀，而不是替换所有出现的 "user_"
                user_id = item.name[5:]  # len("user_") == 5
                users.append(user_id)
        return users
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        users = self.list_users()
        total_users = len(users)
        
        # 统计文件数量
        total_files = 0
        total_size = 0
        
        for user_id in users:
            workspace = self.base_path / f"user_{user_id}"
            if workspace.exists():
                for item in workspace.rglob("*"):
                    if item.is_file():
                        total_files += 1
                        total_size += item.stat().st_size
        
        return {
            "total_users": total_users,
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "base_path": str(self.base_path)
        }
