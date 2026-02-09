# nanobot 多租户服务完整实现指南

## 📁 已完成的文件清单

### 1. 架构文档
- **`/Users/lulei/codes/ai/nanobot/core_ark.md`**
  - 完整的多租户架构设计文档
  - 包含架构图、数据流、实施路线图
  - 性能优化建议

### 2. 核心组件实现

#### 2.1 Workspace 管理器
**文件**: `/Users/lulei/codes/ai/nanobot/nanobot/workspace/manager.py`

- **WorkspaceManager 类**: 管理多用户工作空间
- **功能**:
  - 创建/删除 Workspace
  - 维护标准目录结构 (memory, reports, data, skills)
  - 模板文件生成 (AGENTS.md, USER.md, SOUL.md, HEARTBEAT.md)
  - 工作空间克隆
  - 统计信息查询

#### 2.2 用户配置管理器
**文件**: `/Users/lulei/codes/ai/nanobot/nanobot/services/user_config.py`

- **UserConfigManager 类**: 管理用户配置
- **数据类**:
  - `UserWatchlist`: 用户关注列表（股票、大V、关键词、行业）
  - `UserPreferences`: 用户偏好（报告频率、格式、语言等）
  - `UserConfig`: 完整用户配置
- **功能**:
  - 用户配置的 CRUD
  - 关注列表更新
  - 偏好设置更新
  - 批量操作

#### 2.3 多租户 Agent 循环
**文件**: `/Users/lulei/codes/ai/nanobot/nanobot/agent/multi_tenant_loop.py`

- **MultiTenantAgentLoop 类**: 支持动态 Workspace 切换
- **核心功能**:
  - `switch_workspace(user_id)`: 动态切换用户工作空间
  - `process_for_user(user_id, message)`: 为指定用户处理消息
  - 每个用户独立的 Context、Session、Tools、Subagents
  - 共享的 LLM Provider、Message Bus、Cron Service

#### 2.4 定时任务调度器
**文件**: `/Users/lulei/codes/ai/nanobot/nanobot/services/scheduler.py`

- **ReportScheduler 类**: 定时报告调度器
- **功能**:
  - 每日报告定时任务
  - 每周报告定时任务
  - Cron 表达式支持
  - 任务管理（添加、删除、查询）
  - 手动立即生成报告

### 3. FastAPI 接口实现

**文件**: `/Users/lulei/codes/ai/nanobot/nanobot/api/main.py`

完整的 REST API 实现，包含以下端点：

#### 3.1 健康检查
- `GET /` - API 信息
- `GET /health` - 健康检查

#### 3.2 用户管理
- `POST /users` - 创建用户
- `GET /users` - 列出所有用户
- `GET /users/{user_id}` - 获取用户信息
- `DELETE /users/{user_id}` - 删除用户

#### 3.3 关注列表
- `PUT /users/{user_id}/watchlist` - 更新关注列表

#### 3.4 偏好设置
- `PUT /users/{user_id}/preferences` - 更新偏好设置

#### 3.5 聊天
- `POST /chat` - 发送消息

#### 3.6 报告
- `POST /reports` - 生成报告
- `GET /reports/{report_id}` - 获取报告状态

#### 3.7 定时任务
- `GET /schedule` - 获取定时任务信息

### 4. 测试用例

**文件**: `/Users/lulei/codes/ai/nanobot/tests/test_multi_tenant.py`

完整的测试套件，包含：

#### 4.1 WorkspaceManager 测试
- 初始化测试
- 创建工作空间测试
- 删除工作空间测试
- 查询工作空间信息测试

#### 4.2 UserConfigManager 测试
- 用户创建测试
- 配置获取/更新测试
- 关注列表更新测试
- 偏好设置更新测试

#### 4.3 集成测试
- 完整用户工作流测试
- 多用户数据隔离测试

## 🚀 快速开始指南

### 1. 安装依赖

```bash
# 基础依赖
pip install fastapi uvicorn pydantic

# 定时任务（可选）
pip install apscheduler

# 测试（可选）
pip install pytest pytest-asyncio
```

### 2. 启动 API 服务

```bash
# 方式 1: 直接运行
python -m nanobot.api.main

# 方式 2: 使用 uvicorn
uvicorn nanobot.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 运行测试

```bash
# 运行所有测试
pytest tests/test_multi_tenant.py -v

# 运行特定测试类
pytest tests/test_multi_tenant.py::TestWorkspaceManager -v

# 运行集成测试
pytest tests/test_multi_tenant.py::TestIntegration -v
```

### 4. 使用示例

```python
import asyncio
from nanobot.workspace.manager import WorkspaceManager
from nanobot.services.user_config import UserConfigManager
from nanobot.agent.multi_tenant_loop import MultiTenantAgentLoop

async def main():
    # 初始化组件
    workspace_manager = WorkspaceManager("~/.nanobot/workspaces")
    config_manager = UserConfigManager("~/.nanobot/workspaces")
    
    # 创建用户
    user_id = "my_user"
    workspace = workspace_manager.create_workspace(user_id=user_id)
    config = config_manager.create_user(user_id=user_id)
    
    # 配置关注列表
    config_manager.update_watchlist(
        user_id=user_id,
        watchlist_data={
            "stocks": ["AAPL", "TSLA"],
            "influencers": ["@elonmusk"]
        }
    )
    
    # 初始化 Agent（需要 API key）
    # loop = MultiTenantAgentLoop(...)
    # response = await loop.process_for_user(user_id, "Generate my daily report")

if __name__ == "__main__":
    asyncio.run(main())
```

## 📚 API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## 🎯 后续优化建议

1. **数据库集成**: 当前使用文件系统，可迁移到 PostgreSQL + Redis
2. **消息队列**: 使用 Celery + RabbitMQ 处理后台任务
3. **监控告警**: 集成 Prometheus + Grafana
4. **缓存层**: 添加 Redis 缓存热点数据
5. **水平扩展**: 支持多实例部署 + 负载均衡

## 📄 许可证

MIT License - 详见 LICENSE 文件
