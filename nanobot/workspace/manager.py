"""Workspace 管理器 - 多租户隔离的核心组件"""

import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class WorkspaceConfig:
    """Workspace 配置"""
    user_id: str
    created_at: str
    updated_at: str
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def create(cls, user_id: str) -> "WorkspaceConfig":
        now = datetime.now().isoformat()
        return cls(
            user_id=user_id,
            created_at=now,
            updated_at=now
        )


class WorkspaceManager:
    """
    Workspace 管理器
    
    负责：
    1. 创建、管理多用户 Workspace
    2. 维护目录结构
    3. 提供 Workspace 路径解析
    4. 支持模板复制
    """
    
    # 标准目录结构
    STANDARD_DIRS = [
        "memory",
        "reports",
        "data",
        "skills"
    ]
    
    # 标准文件模板
    STANDARD_FILES = {
        "AGENTS.md": """# Agent 配置

## 用户 ID
{user_id}

## 角色
你是用户的专属 AI 助手。

## 工作流程
1. 理解用户需求
2. 使用工具收集信息
3. 生成个性化回复
4. 保存重要信息到记忆

## 可用工具
- `web_search`: 搜索网络信息
- `web_fetch`: 获取网页内容
- `read_file`: 读取文件
- `write_file`: 写入文件
- `my_system_api`: 查询业务系统

## 输出格式
根据用户偏好生成 {language} 格式的回复。
""",
        "USER.md": """# 用户信息

## 基本信息
- 用户 ID: {user_id}
- 创建时间: {created_at}
- 语言偏好: {language}

## 个性化设置
- 报告格式: {report_format}
- 通知方式: {notification_channels}
""",
        "SOUL.md": """# 人格设定

我是你的专属 AI 助手，具有以下特质：

## 性格
- 专业且友好
- 耐心细致
- 善于分析和总结

## 价值观
- 用户隐私至上
- 提供准确信息
- 持续学习优化

## 沟通风格
- 简洁明了
- 结构化表达
- 根据用户偏好调整语言风格
""",
        "HEARTBEAT.md": """# 周期性任务

## 定时报告
- [ ] 生成每日市场简报
- [ ] 检查关注标的价格变动
- [ ] 汇总关注大V最新观点

## 数据同步
- [ ] 同步用户关注列表
- [ ] 更新个性化推荐

## 自定义任务
（用户可以在这里添加自己的周期性任务）
"""
    }
    
    def __init__(self, base_path: str = "~/.nanobot/workspaces"):
        """
        初始化 WorkspaceManager
        
        Args:
            base_path: Workspace 基础路径
        """
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        print(f"[WorkspaceManager] 基础路径: {self.base_path}")
    
    def _get_workspace_path(self, user_id: str) -> Path:
        """获取用户的 workspace 路径"""
        return self.base_path / f"user_{user_id}"
    
    def workspace_exists(self, user_id: str) -> bool:
        """检查用户的 workspace 是否存在"""
        return self._get_workspace_path(user_id).exists()
    
    def get_workspace(self, user_id: str) -> Path:
        """
        获取用户的 workspace 路径
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Path 对象，指向用户的 workspace 目录
            
        Note:
            此方法不会检查 workspace 是否存在，只是返回路径。
            如需检查存在性，请使用 workspace_exists()。
        """
        return self._get_workspace_path(user_id)
    
    def create_workspace(
        self, 
        user_id: str,
        template_data: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        创建新用户的 workspace
        
        Args:
            user_id: 用户 ID
            template_data: 模板数据，用于填充文件模板
            
        Returns:
            创建的工作空间路径
        """
        workspace = self._get_workspace_path(user_id)
        
        # 如果已存在，先删除（或报错）
        if workspace.exists():
            print(f"[WorkspaceManager] 用户 {user_id} 的 workspace 已存在，删除重建")
            shutil.rmtree(workspace)
        
        # 创建目录结构
        print(f"[WorkspaceManager] 为用户 {user_id} 创建 workspace...")
        workspace.mkdir(parents=True)
        
        # 创建标准目录
        for dir_name in self.STANDARD_DIRS:
            (workspace / dir_name).mkdir(exist_ok=True)
            print(f"  创建目录: {dir_name}/")
        
        # 准备模板数据
        template_values = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "language": "zh",
            "report_format": "markdown",
            "notification_channels": "push,email"
        }
        if template_data:
            template_values.update(template_data)
        
        # 创建标准文件
        for filename, template in self.STANDARD_FILES.items():
            content = template.format(**template_values)
            (workspace / filename).write_text(content, encoding="utf-8")
            print(f"  创建文件: {filename}")
        
        # 创建初始 MEMORY.md
        memory_content = f"""# 长期记忆

## 用户 {user_id} 的记忆

### 基本信息
- 用户ID: {user_id}
- 首次使用: {datetime.now().isoformat()}

### 偏好记录
（AI 会从对话中学习和记录用户的偏好）

### 重要事件
（记录用户关注的重要事件和里程碑）

### 历史对话要点
（记录历史对话的关键信息和结论）
"""
        (workspace / "memory" / "MEMORY.md").write_text(memory_content, encoding="utf-8")
        print(f"  创建文件: memory/MEMORY.md")
        
        # 创建 config.json
        config = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": "1.0",
            "watchlist": {
                "stocks": [],
                "influencers": [],
                "keywords": [],
                "sectors": []
            },
            "preferences": {
                "language": "zh",
                "report_frequency": "daily",
                "report_time": "09:00",
                "report_format": "markdown",
                "notification_channels": ["push"]
            }
        }
        (workspace / "config.json").write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"  创建文件: config.json")
        
        print(f"[WorkspaceManager] 用户 {user_id} 的 workspace 创建完成！")
        return workspace
    
    def delete_workspace(self, user_id: str) -> bool:
        """删除用户的 workspace"""
        workspace = self._get_workspace_path(user_id)
        if not workspace.exists():
            return False
        
        shutil.rmtree(workspace)
        print(f"[WorkspaceManager] 已删除用户 {user_id} 的 workspace")
        return True
    
    def get_workspace_info(self, user_id: str) -> dict:
        """获取 workspace 信息"""
        workspace = self._get_workspace_path(user_id)
        
        if not workspace.exists():
            return {"exists": False}
        
        # 统计信息
        dir_count = sum(1 for d in workspace.rglob("*") if d.is_dir())
        file_count = sum(1 for f in workspace.rglob("*") if f.is_file())
        
        # 获取 config
        config_path = workspace / "config.json"
        config = {}
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
            except:
                pass
        
        return {
            "exists": True,
            "path": str(workspace),
            "directories": dir_count,
            "files": file_count,
            "config": config,
            "created_at": config.get("created_at", "unknown")
        }
    
    def list_workspaces(self) -> list:
        """列出所有 workspace"""
        workspaces = []
        for item in self.base_path.iterdir():
            if item.is_dir() and item.name.startswith("user_"):
                user_id = item.name.replace("user_", "")
                info = self.get_workspace_info(user_id)
                workspaces.append({
                    "user_id": user_id,
                    "info": info
                })
        return workspaces
    
    def clone_template(self, source_user_id: str, target_user_id: str) -> Path:
        """从模板用户克隆 workspace"""
        source = self._get_workspace_path(source_user_id)
        if not source.exists():
            raise ValueError(f"Source user {source_user_id} does not exist")
        
        # 创建新的 workspace
        target = self.create_workspace(target_user_id)
        
        # 复制特定文件（不复制 config.json）
        files_to_copy = ["AGENTS.md", "SOUL.md", "HEARTBEAT.md"]
        for filename in files_to_copy:
            source_file = source / filename
            if source_file.exists():
                shutil.copy(source_file, target / filename)
        
        print(f"[WorkspaceManager] 已从 {source_user_id} 克隆模板到 {target_user_id}")
        return target
