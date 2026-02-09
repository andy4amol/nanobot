# 多租户投资报告系统 - 对话记录与实现总结

**日期**: 2024年2月9日  
**参与者**: 用户 + AI助手  
**主题**: 实现基于nanobot的多租户C端投资报告生成系统

---

## 一、系统架构概览

### 1.1 核心架构组件

```
用户App/前端
    │
    ▼
FastAPI (main.py:490)
    ├── 用户管理 API (/users/*)
    ├── 关注列表更新 (/users/{id}/watchlist)
    ├── 偏好设置更新 (/users/{id}/preferences)
    └── 报告生成接口 (/reports)
    │
    ▼
ReportScheduler (services/scheduler.py:370)
    ├── APScheduler 定时调度
    ├── 1000+ 用户 Job 管理
    └── 异步任务执行
    │
    ▼
ReportGenerator (services/report_generator_simple.py)
    ├── Prompt 模板构建
    ├── 用户画像注入
    └── LLM 调用生成报告
    │
    ▼
用户 Workspace (~/.nanobot/workspaces/user_{id}/)
    ├── config.json (用户配置)
    ├── AGENTS.md (个性化提示词)
    ├── reports/ (生成的报告)
    └── templates/ (自定义模板)
```

### 1.2 数据流图

```
用户配置更新流程:
App → PUT /users/{id}/watchlist → UserConfigManager.update_watchlist() → config.json

定时报告生成流程:
APScheduler → _generate_report_task() → ReportGenerator.generate_report() → LLM → reports/{id}.md
```

---

## 二、关键实现细节

### 2.1 用户信息更新调用链

#### 更新关注列表 (Watchlist)

```python
# Step 1: API 层接收请求
@app.put("/users/{user_id}/watchlist")
async def update_watchlist(user_id: str, watchlist: WatchlistUpdate):
    watchlist_data = watchlist.dict(exclude_unset=True)  # 只包含设置的字段
    updated_config = config_manager.update_watchlist(user_id, watchlist_data)
    return UserResponse(**updated_config.to_dict())

# Step 2: UserConfigManager 执行更新
def update_watchlist(self, user_id: str, watchlist_data: Dict):
    config = self.get_config(user_id)  # 从 config.json 加载
    
    # 更新内存对象
    for key, value in watchlist_data.items():
        if hasattr(config.watchlist, key):
            setattr(config.watchlist, key, value)
    
    config.updated_at = datetime.now().isoformat()
    
    # 保存回文件
    self.save_config(config)  # 写入 config.json
    
    return config
```

#### 更新偏好设置 (Preferences)

```python
# 调用链与 Watchlist 更新类似
config_manager.update_preferences(user_id, prefs_data)
```

### 2.2 定时任务调度机制

#### APScheduler 配置

```python
# scheduler.py:76-84
self.scheduler = AsyncIOScheduler(
    jobstores={'default': MemoryJobStore()},
    job_defaults={
        'coalesce': False,      # 错过的任务不合并
        'max_instances': 3        # 同一 job 最多3个实例
    }
)
```

#### 添加定时任务

```python
def add_daily_report_job(self, user_id: str, hour: int = 9, minute: int = 0):
    job_id = f"daily_report_{user_id}"
    
    trigger = CronTrigger(hour=hour, minute=minute)
    
    job = self.scheduler.add_job(
        func=self._generate_report_task,
        trigger=trigger,
        id=job_id,
        args=[user_id, "daily"],  # 关键：传递 user_id
        replace_existing=True
    )
```

#### 任务执行（用户隔离）

```python
async def _generate_report_task(self, user_id: str, report_type: str):
    """
    关键：每个任务都携带 user_id 参数
    确保执行时知道是哪个用户的任务
    """
    # 1. 获取该用户的配置
    config = self.config_manager.get_config(user_id)
    
    # 2. 切换到该用户的 workspace
    workspace = self.workspace_manager.get_workspace(user_id)
    
    # 3. 调用 ReportGenerator 生成报告
    if self.report_generator:
        result = await self.report_generator.generate_report(
            user_id=user_id,
            report_type=report_type
        )
    
    # 4. 报告自动保存到该用户的 reports/ 目录
```

### 2.3 Prompt 模板系统

#### 模板结构

```python
# report_generator_simple.py: _build_prompt() 方法生成的 Prompt 结构

# 1. 角色设定（固定）
你是一位专业的投资分析师，拥有10年以上的金融市场分析经验...

# 2. 用户基本信息（动态注入）
- 用户ID: {user_id}
- 报告类型: {report_type}
- 报告日期: {datetime.now()}

# 3. 用户关注列表（动态注入）
- **股票标的**: AAPL, TSLA, BABA
- **关注大V**: @elonmusk, @雷总
- **关键词**: AI, 新能源

# 4. 用户画像（动态注入）
- **风险偏好**: moderate
- **投资经验**: intermediate
- **投资周期**: medium

# 5. 任务要求（固定框架 + 动态内容）
### 1. 内容要求
**如果是日报 (daily)**:
1. **市场概览**（200-300字）...
2. **重点标的分析**（每个关注标的100-150字）...

### 2. 格式要求
- 使用 Markdown 格式
- 一级标题 `#` 用于报告标题
...

### 3. 风格要求
- 根据用户的风险偏好调整语气
...

### 4. 限制条件
- **日报**: 总长度控制在 1500-2000 字
- 不要编造不存在的数据
...
```

#### 关键实现点

```python
def _build_prompt(self, user_id, report_type, user_config, custom_data):
    """
    构建 Prompt 的核心方法
    
    1. 从 user_config 中提取动态数据：
       - watchlist.stocks (关注股票)
       - watchlist.influencers (关注大V)
       - preferences.language (语言偏好)
       - custom_data.persona (用户画像)
    
    2. 将动态数据格式化为文本
    
    3. 将格式化后的数据注入到固定模板中
    
    4. 返回完整的 Prompt 字符串
    """
    
    watchlist = user_config.watchlist
    preferences = user_config.preferences
    
    # 格式化关注列表
    watchlist_text = self._format_watchlist(watchlist)
    
    # 获取用户画像
    custom_persona = user_config.custom_data.get('persona', {})
    
    # 构建 Prompt（将动态数据注入模板）
    prompt = f"""
    ## 用户关注列表
    {watchlist_text}
    
    ## 用户画像
    - **风险偏好**: {custom_persona.get('risk_preference', 'moderate')}
    ...
    """
    
    return prompt
```

---

## 三、系统集成方式

### 3.1 在调度器中集成 ReportGenerator

```python
# scheduler.py 修改建议

from nanobot.services.report_generator_simple import ReportGenerator

class ReportScheduler:
    def __init__(self, ...):
        # ... 现有初始化 ...
        
        # 初始化报告生成器
        self.report_generator = ReportGenerator(
            config_manager=self.config_manager,
            workspace_manager=self.workspace_manager,
            agent_loop=None,  # 可以传入 MultiTenantAgentLoop
            max_retries=3
        )
    
    async def _generate_report_task(self, user_id: str, report_type: str) -> None:
        """生成报告的定时任务"""
        logger.info(f"开始生成报告: user={user_id}, type={report_type}")
        
        try:
            # 使用新的报告生成器
            result = await self.report_generator.generate_report(
                user_id=user_id,
                report_type=report_type
            )
            
            if result["success"]:
                logger.info(f"报告生成成功: {result['report_id']}")
                logger.info(f"报告路径: {result['report_path']}")
                logger.info(f"报告内容长度: {len(result['content'])} 字符")
            else:
                logger.error(f"报告生成失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            logger.error(f"生成报告时发生异常: {e}", exc_info=True)
```

### 3.2 初始化流程

```python
# 系统启动时的初始化流程 (main.py lifespan)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 初始化 WorkspaceManager
    workspace_manager = WorkspaceManager("~/.nanobot/workspaces")
    
    # 2. 初始化 UserConfigManager
    config_manager = UserConfigManager("~/.nanobot/workspaces")
    
    # 3. 初始化 MultiTenantAgentLoop (如果需要)
    agent_loop = MultiTenantAgentLoop(...)
    
    # 4. 初始化 ReportScheduler
    report_scheduler = ReportScheduler(
        workspace_base="~/.nanobot/workspaces"
    )
    
    # 5. 启动调度器
    await report_scheduler.start()
    
    # 6. 为现有用户注册定时任务
    users = config_manager.list_users()
    for user_id in users:
        config = config_manager.get_config(user_id)
        if config:
            # 获取用户的报告时间偏好
            report_time = config.preferences.report_time  # e.g., "15:00"
            hour, minute = map(int, report_time.split(":"))
            
            # 注册日报任务
            report_scheduler.add_daily_report_job(
                user_id=user_id,
                hour=hour,
                minute=minute
            )
    
    yield
    
    # 清理
    await report_scheduler.stop()
```

---

## 四、关键特性总结

### 4.1 多租户隔离机制

| 隔离维度 | 实现方式 | 代码位置 |
|---------|---------|---------|
| **数据隔离** | 每个用户独立的 config.json 和 workspace 目录 | `workspace/manager.py:36` |
| **配置隔离** | UserConfigManager 通过 user_id 读取不同文件 | `services/user_config.py:153` |
| **执行隔离** | ReportGenerator 生成报告时携带 user_id 参数 | `services/report_generator_simple.py:25` |
| **存储隔离** | 报告保存到各自用户的 `reports/` 目录 | `services/report_generator_simple.py:687` |

### 4.2 Prompt 模板系统特性

```
Prompt 结构层次:
├── 1. 角色设定（固定）
│   └── 专业投资分析师，10年+经验
│
├── 2. 用户基本信息（动态）
│   ├── 用户ID、报告类型、日期
│   └── 语言偏好
│
├── 3. 用户关注列表（动态）
│   ├── 股票标的: AAPL, TSLA
│   ├── 关注大V: @elonmusk
│   └── 关键词: AI, 新能源
│
├── 4. 用户画像（动态）
│   ├── 风险偏好: moderate
│   ├── 投资经验: intermediate
│   └── 投资周期: medium
│
├── 5. 任务要求（固定框架 + 动态内容）
│   ├── 内容要求（根据 report_type 动态调整）
│   ├── 格式要求（固定 Markdown 规范）
│   ├── 风格要求（根据风险偏好动态调整）
│   └── 限制条件（固定字数、禁止事项）
│
└── 6. 输出格式（固定）
    └── 直接输出 Markdown 格式报告
```

### 4.3 定时调度机制

```python
# 调度器核心机制

# 1. Job 注册（每个用户独立）
job_id = f"daily_report_{user_id}"  # e.g., "daily_report_user_001"

# 2. 触发器设置
trigger = CronTrigger(hour=15, minute=0)  # 每天 15:00

# 3. Job 执行
job = self.scheduler.add_job(
    func=self._generate_report_task,
    trigger=trigger,
    id=job_id,
    args=[user_id, "daily"],  # 关键：传递 user_id
    replace_existing=True
)

# 4. 并发控制
job_defaults = {
    'coalesce': False,      # 错过任务不合并
    'max_instances': 3        # 同一 job 最多3个实例
}
```

---

## 五、文件清单

### 5.1 新建/修改的文件

| 文件路径 | 类型 | 说明 |
|---------|------|------|
| `nanobot/services/prompt_templates.py` | 新建 | Prompt 模板系统，包含 UserPersona、PromptTemplate、PromptTemplateManager、PromptRenderer 等类 |
| `nanobot/services/report_generator_simple.py` | 新建 | 报告生成器，包含 ReportGenerator 类，负责 Prompt 构建、LLM 调用、报告保存 |
| `nanobot/services/scheduler.py` | 修改建议 | 需要集成新的 ReportGenerator 类 |

### 5.2 核心类关系图

```
ReportScheduler
    ├── APScheduler (定时调度)
    ├── config_manager: UserConfigManager
    ├── workspace_manager: WorkspaceManager
    └── report_generator: ReportGenerator (新增)
            ├── config_manager: UserConfigManager
            ├── workspace_manager: WorkspaceManager
            ├── agent_loop: MultiTenantAgentLoop (可选)
            ├── prompt_renderer: PromptRenderer
            │       └── template_manager: PromptTemplateManager
            │               ├── _templates: Dict[str, PromptTemplate]
            │               │       ├── daily_report
            │               │       ├── weekly_report
            │               │       └── realtime_alert
            │               └── _user_templates: Dict[user_id, templates]
            └── max_retries: int = 3
```

---

## 六、后续建议

### 6.1 立即实施

1. **在 scheduler.py 中集成 ReportGenerator**（参考上面的集成示例）
2. **测试单个用户报告生成流程**
3. **验证 Prompt 渲染效果**

### 6.2 短期优化

1. **实现数据收集工具**：获取真实股票数据、新闻、大V观点
2. **添加用户画像管理 API**：允许用户设置风险偏好、投资经验
3. **完善错误处理和日志记录**

### 6.3 长期规划

1. **支持更多报告类型**：月报、季报、年报
2. **添加报告模板可视化编辑器**
3. **实现报告质量评估和反馈机制**
4. **支持多语言报告生成**

---

## 七、核心代码片段

### 7.1 Prompt 模板核心结构

```python
# Prompt 模板的核心结构（来自 report_generator_simple.py: _build_prompt()）

prompt = f"""
# 投资报告生成任务

## 角色设定
你是一位专业的投资分析师，拥有10年以上的金融市场分析经验...

## 用户基本信息
- **用户ID**: {user_id}
- **报告类型**: {report_type}
...

## 用户关注列表
{watchlist_text}  # 动态注入

## 用户画像
- **风险偏好**: {custom_persona.get('risk_preference', 'moderate')}  # 动态注入
...

## 任务要求
### 1. 内容要求
...（根据 report_type 动态调整）

### 2. 格式要求
...（固定 Markdown 规范）

### 3. 风格要求
...（根据风险偏好动态调整）

### 4. 限制条件
...（固定字数、禁止事项）

## 输出格式
请直接输出完整的 Markdown 格式报告...
"""
```

### 7.2 报告生成核心流程

```python
# 报告生成的核心流程（来自 report_generator_simple.py: generate_report()）

async def generate_report(self, user_id, report_type, custom_data):
    # 1. 获取用户配置
    user_config = self.config_manager.get_config(user_id)
    
    # 2. 构建 Prompt（关键步骤）
    prompt = self._build_prompt(
        user_id=user_id,
        report_type=report_type,
        user_config=user_config,
        custom_data=custom_data
    )
    
    # 3. 调用 LLM 生成报告
    report_content = await self._call_llm_with_retry(
        prompt=prompt,
        user_id=user_id,
        report_type=report_type
    )
    
    # 4. 保存报告
    report_path = self._save_report(
        user_id=user_id,
        report_id=report_id,
        content=report_content,
        metadata={...}
    )
    
    return {
        "success": True,
        "report_id": report_id,
        "report_path": str(report_path),
        "content": report_content,
        ...
    }
```

---

## 八、总结

本次对话完成了以下核心工作：

1. **详细解释了现有系统的架构和调用链**，包括：
   - 多租户隔离机制
   - 定时任务调度流程
   - 用户信息更新调用链

2. **设计并实现了完整的报告生成系统**，包括：
   - Prompt 模板系统（`prompt_templates.py`）
   - 报告生成器（`report_generator_simple.py`）
   - 动态 Prompt 构建机制
   - 用户画像注入

3. **提供了详细的集成方案**，包括：
   - 如何在调度器中集成 ReportGenerator
   - 初始化流程
   - 错误处理和降级方案

4. **创建了完整的文档记录**，包括：
   - 系统架构图
   - 数据流图
   - 核心代码片段
   - 后续建议

**核心创新点**：
- **动态 Prompt 系统**：根据用户画像（风险偏好、投资经验）动态调整生成策略
- **多层级模板**：固定框架 + 动态内容 + 用户自定义覆盖
- **完善的隔离机制**：确保1000+用户的任务互不干扰

---

**文档信息**：
- **创建时间**: 2024年2月9日
- **最后更新**: 2024年2月9日
- **版本**: v1.0
- **作者**: AI助手
- **状态**: 已完成初稿
