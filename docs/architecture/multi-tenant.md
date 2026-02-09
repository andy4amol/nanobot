# 多租户服务架构

本文档详细介绍基于 nanobot 的 C 端多租户 AI 服务架构，支持为每个用户提供个性化的 AI 助理服务。

## 架构概述

### 核心挑战

1. **数据隔离**：每个用户有自己的关注列表、生成的报告
2. **个性化**：不同的关注标的、大V、生成频率
3. **扩展性**：支持数万甚至数十万用户
4. **成本控制**：不能为每个用户起一个独立进程
5. **任务调度**：不同用户有不同的定时需求

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (你的 App)                         │
│         ├─ Web App / Mobile App                             │
│         └─ 用户管理中心（关注配置、报告查看）                 │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  API Gateway / BFF                          │
│    负责：认证、路由、用户身份识别、工作空间映射               │
│    关键：JWT Token → 用户ID → Workspace 路径               │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  nanobot 服务集群                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  共享 Agent 进程（多租户模式）                        │ │
│  │                                                      │ │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │   │ Workspace   │  │ Workspace   │  │ Workspace   │   │ │
│  │   │ /user_001   │  │ /user_002   │  │ /user_003   │   │ │
│  │   │             │  │             │  │             │   │ │
│  │   │ ├─ AGENTS.md│  │ ├─ AGENTS.md│  │ ├─ AGENTS.md│   │ │
│  │   │ ├─ USER.md  │  │ ├─ USER.md  │  │ ├─ USER.md  │   │ │
│  │   │ ├─ HEARTBEAT│  │ ├─ HEARTBEAT│  │ ├─ HEARTBEAT│   │ │
│  │   │ ├─ memory/  │  │ ├─ memory/  │  │ ├─ memory/  │   │ │
│  │   │ └─ reports/│  │ └─ reports/│  │ └─ reports/│   │ │
│  │   └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  │                                                      │ │
│  │  共享组件：                                           │ │
│  │  ├─ 一个 AgentLoop 实例                               │ │
│  │  ├─ 一个 CronService 实例                             │ │
│  │  ├─ 一个 MessageBus 实例                              │ │
│  │  └─ 统一的 ToolRegistry                              │ │
│  │                                                      │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. Workspace 管理

每个用户拥有独立的工作空间，实现数据隔离：

```
~/.nanobot/workspaces/
├── user_001/
│   ├── AGENTS.md           # 个性化 Agent 提示词
│   ├── USER.md             # 用户信息、偏好
│   ├── HEARTBEAT.md        # 周期性任务配置
│   ├── SOUL.md             # 人格设定
│   ├── MEMORY.md           # 长期记忆
│   ├── memory/             # 记忆片段存储
│   ├── reports/            # 生成的报告
│   └── config.json         # 用户特定配置
└── shared/                   # 共享资源（可选）
    └── templates/
```

### 2. 用户配置管理

多租户场景下的用户配置管理：

```python
from nanobot.services.user_config import UserConfigManager

manager = UserConfigManager("~/.nanobot/workspaces")

# 创建用户
config = manager.create_user(user_id="user_123")

# 更新关注列表
manager.update_watchlist(
    user_id="user_123",
    watchlist_data={
        "stocks": ["AAPL", "TSLA"],
        "influencers": ["@elonmusk"]
    }
)

# 更新偏好设置
manager.update_preferences(
    user_id="user_123",
    prefs_data={
        "report_frequency": "daily",
        "language": "zh"
    }
)
```

### 3. 多租户 Agent 循环

支持动态 Workspace 切换的多租户 Agent：

```python
from nanobot.agent.multi_tenant_loop import MultiTenantAgentLoop
from nanobot.workspace.manager import WorkspaceManager
from nanobot.bus.queue import MessageBus
from nanobot.providers.litellm_provider import LiteLLMProvider

# 初始化
workspace_manager = WorkspaceManager()
bus = MessageBus()
provider = LiteLLMProvider(api_key="your-api-key")

loop = MultiTenantAgentLoop(
    bus=bus,
    provider=provider,
    workspace_manager=workspace_manager,
    model="gpt-4"
)

# 处理用户消息
response = await loop.process_for_user(
    user_id="user_123",
    message="Generate my daily report",
    session_key="session_001"
)
```

### 4. 定时任务调度

支持多用户的定时报告调度：

```python
from nanobot.services.scheduler import ReportScheduler

scheduler = ReportScheduler(
    workspace_base="~/.nanobot/workspaces"
)

# 启动调度器
await scheduler.start()

# 添加每日报告任务
job_id = scheduler.add_daily_report_job(
    user_id="user_123",
    hour=9,
    minute=0
)

# 添加每周报告任务
job_id = scheduler.add_weekly_report_job(
    user_id="user_123",
    day_of_week="mon",
    hour=9,
    minute=0
)
```

## 数据流设计

### 用户配置更新流程

```
App → PUT /users/{id}/watchlist → UserConfigManager.update_watchlist() → config.json
```

### 定时报告生成流程

```
APScheduler → _generate_report_task() → ReportGenerator.generate_report() → LLM → reports/{id}.md
```

## 实施路线图

### 阶段 1：基础架构（1-2 周）
- 实现 WorkspaceManager
- 实现 UserConfigManager
- 修改 AgentLoop 支持动态切换

### 阶段 2：API 开发（2-3 周）
- 实现用户管理 API
- 实现报告服务 API
- 实现即时对话 API

### 阶段 3：定时任务（1-2 周）
- 实现 ReportScheduler
- 集成 APScheduler
- 支持 Cron 表达式

### 阶段 4：集成测试（1 周）
- 多用户并发测试
- 性能压力测试
- 端到端集成测试

### 阶段 5：优化（持续）
- 数据库优化
- 缓存策略
- 监控告警

## 扩展建议

### 大规模用户优化

当用户量 > 10,000 时的优化策略：

```python
# 1. 数据库层
# - 使用 PostgreSQL + 分区表
# - 用户配置缓存到 Redis
# - 报告元数据存数据库，内容存对象存储

# 2. 计算层
# - 报告生成使用 Celery + Redis 队列
# - 多 Worker 并行处理
# - 用户分片（Shard）到不同实例

# 3. 存储层
# - 旧报告自动归档到冷存储
# - 使用 CDN 加速报告访问
```

### 成本优化

```python
# 智能调度策略 - 避免高峰期集中执行

class SmartScheduler:
    """智能调度器 - 错峰执行"""
    
    def __init__(self):
        self.user_time_slots = {}
    
    def assign_time_slot(self, user_id: str, preferred_time: str) -> str:
        """分配执行时间槽（错峰）"""
        hour, minute = map(int, preferred_time.split(":"))
        
        # 在 15 分钟窗口内随机分散
        import random
        offset = random.randint(-7, 7)
        new_minute = (minute + offset) % 60
        if new_minute < 0:
            new_minute += 60
        
        assigned_time = f"{hour:02d}:{new_minute:02d}"
        self.user_time_slots[user_id] = assigned_time
        
        return assigned_time
```

## 相关文档

- [系统架构概览](overview.md) - Nanobot 整体架构
- [Workspace 管理](workspace.md) - 工作空间详细说明
- [数据流设计](dataflow.md) - 数据流动详细设计
- [API 开发指南](../development/api.md) - 如何开发 API
- [贡献指南](../contributing/process.md) - 如何为项目做贡献
