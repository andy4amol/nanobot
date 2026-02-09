"""Prompt 模板管理系统

提供动态 Prompt 生成功能，支持：
1. 基础模板定义（包含对大模型的建议和限制）
2. 动态数据注入（用户画像、投资偏好等）
3. 多场景模板管理（日报、周报、突发事件等）
4. 用户自定义模板覆盖
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class ReportType(Enum):
    """报告类型枚举"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    REALTIME = "realtime"
    CUSTOM = "custom"


class ReportSection(Enum):
    """报告章节类型"""
    MARKET_OVERVIEW = "market_overview"
    STOCK_ANALYSIS = "stock_analysis"
    INFLUENCER_OPINIONS = "influencer_opinions"
    NEWS_SUMMARY = "news_summary"
    RISK_WARNING = "risk_warning"
    INVESTMENT_SUGGESTIONS = "investment_suggestions"


@dataclass
class UserPersona:
    """用户画像数据"""
    # 基础属性
    risk_preference: str = "moderate"  # conservative, moderate, aggressive
    investment_experience: str = "intermediate"  # novice, intermediate, expert
    investment_horizon: str = "medium"  # short, medium, long
    
    # 偏好设置
    preferred_report_length: str = "medium"  # short, medium, detailed
    focus_areas: List[str] = field(default_factory=list)  # 用户特别关注的领域
    avoid_topics: List[str] = field(default_factory=list)  # 用户不想看到的内容
    
    # 交互历史
    feedback_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_preference": self.risk_preference,
            "investment_experience": self.investment_experience,
            "investment_horizon": self.investment_horizon,
            "preferred_report_length": self.preferred_report_length,
            "focus_areas": self.focus_areas,
            "avoid_topics": self.avoid_topics,
            "feedback_history": self.feedback_history
        }


@dataclass
class PromptTemplate:
    """Prompt 模板定义"""
    name: str
    description: str
    template: str
    required_variables: List[str] = field(default_factory=list)
    optional_variables: List[str] = field(default_factory=list)
    version: str = "1.0"
    
    def validate_variables(self, variables: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证变量是否满足模板要求"""
        missing = []
        for var in self.required_variables:
            if var not in variables or variables[var] is None:
                missing.append(var)
        return len(missing) == 0, missing
    
    def render(self, variables: Dict[str, Any]) -> str:
        """渲染模板"""
        is_valid, missing = self.validate_variables(variables)
        if not is_valid:
            raise ValueError(f"Missing required variables: {missing}")
        
        try:
            return self.template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Template rendering failed: missing key {e}")


# 预定义的报告 Prompt 模板库
DEFAULT_TEMPLATES = {
    "daily_report": PromptTemplate(
        name="daily_report",
        description="每日投资简报",
        required_variables=[
            "user_id", "report_date", "watchlist", "user_persona"
        ],
        optional_variables=[
            "market_data", "news_summary", "influencer_opinions"
        ],
        template="""# Role
你是一位资深的金融投资顾问，擅长数据驱动的投资分析。

# Goal
根据提供的【市场宏观数据】和【用户关注标的详情】，撰写一份逻辑严密、数据准确的投资日报。

# Data Handling Rules (至关重要)
1. **数据对应性**：必须严格基于 `<target_assets>` 中提供的 JSON 数据结构。JSON 中 `symbol` 为 "A" 的对象，其 `announcements` (公告) 只能用于分析 A，严禁张冠李戴。
2. **缺失值处理**：
   - 如果某个字段（如 `abnormal_movements` 或 `announcements`）为空列表 `[]` 或 `null`，**必须跳过**该维度的分析。
   - 严禁编造数据来填补空白（例如：不要说"今日无异动，走势平稳"，直接不提异动即可）。
3. **数量自适应**：用户关注的标的数量为 1-3 个不定，请对输入的所有标的逐一分析。

# Input Data

<market_context>
{market_data}
</market_context>

<target_assets>
{watchlist}
</target_assets>

<user_preference>
关注风格：{user_persona}
</user_preference>

# Output Guidelines

请按照以下逻辑生成报告：

## Part 1: 市场全景 (Market Overview)
结合 `<market_context>`，用简练的语言概括今日市场情绪和最热话题。

## Part 2: 核心关注深度复盘 (Deep Dive)
遍历 `<target_assets>` 中的每一个标的对象：

### [标的名称] (代码)
* **行情透视**：基于 `market_data` 和 `financial_data`。当前价格是多少？相比昨天涨跌如何？估值（PE/PB）处于什么水平？
* **消息面与异动**：
    * *（仅当 `announcements` 有数据时）*：分析公告对股价的影响。
    * *（仅当 `abnormal_movements` 有数据时）*：解释盘中异动（如"10:30 大单拉升"）背后的资金意图。
    * *（仅当 `related_articles` 有数据时）*：引用热门文章的观点作为补充。
    * *（仅当 `specific_big_v_views` 有数据时）*：引用大 V 对该具体标的的看法。
* **总结建议**：结合上述信息，给出一个简短的观察结论。

---
**开始生成：**
""",
        version="2.0"
    ),
    
    "weekly_report": PromptTemplate(
        name="weekly_report",
        description="每周投资总结",
        required_variables=["user_id", "week_start", "week_end", "watchlist", "user_persona"],
        optional_variables=["weekly_performance", "sector_analysis"],
        template="""# 投资周报生成任务

## 角色设定
你是一位资深的投资策略师，擅长从宏观经济和微观个股两个维度分析市场。你需要为用户生成年度的投资周报。

## 用户画像
{user_persona}

## 报告周期
{week_start} 至 {week_end}

## 用户关注列表
{watchlist}

## 任务要求

### 1. 内容要求
1. **本周市场回顾**（300-400字）：
   - 主要指数周涨跌幅
   - 板块轮动特征
   - 成交量和资金流向

2. **关注标的周表现**（每只股票150-200字）：
   - 股价表现和技术面分析
   - 重要新闻和公告解读
   - 估值水平和同业对比

3. **板块/行业分析**（300字）：
   - 关注行业本周动态
   - 政策影响和趋势判断

4. **下周展望**（200字）：
   - 关注的重要事件和数据
   - 潜在风险和机会提示

### 2. 格式和风格要求
- 使用 Markdown 格式，层次清晰
- 总长度控制在 2500-3000 字
- 根据用户风险偏好调整分析角度
- 数据驱动，避免主观臆断

### 3. 限制条件
- 不要编造数据
- 不给出具体买卖建议
- 保护用户隐私

## 输出格式
直接输出完整的 Markdown 格式周报。
""",
        version="1.0"
    ),
    
    "realtime_alert": PromptTemplate(
        name="realtime_alert",
        description="实时异动提醒",
        required_variables=["user_id", "alert_time", "trigger_event", "watchlist"],
        optional_variables=["market_data"],
        template="""# 实时异动提醒生成任务

## 触发信息
- 触发时间：{alert_time}
- 触发事件：{trigger_event}

## 用户关注列表
{watchlist}

## 任务要求

### 1. 内容要求
1. **异动概述**（100字）：
   - 简要说明触发的事件
   - 涉及的关注标的

2. **影响分析**（150字）：
   - 对关注标的的潜在影响
   - 相关板块联动效应

3. **关注要点**（100字）：
   - 建议关注的时间节点
   - 后续可能的发展

### 2. 格式和风格要求
- 使用 Markdown 格式，简洁明了
- 总长度控制在 400-500 字
- 语言紧迫但不失专业

### 3. 限制条件
- 不编造信息
- 不给出具体操作建议
- 保护用户隐私

## 输出格式
直接输出 Markdown 格式的提醒内容。
""",
        version="1.0"
    )
}


class PromptTemplateManager:
    """Prompt 模板管理器
    
    负责：
    1. 管理基础模板库
    2. 支持用户自定义模板
    3. 模板的 CRUD 操作
    4. 模板渲染和验证
    """
    
    def __init__(self, workspace_manager=None):
        """
        初始化模板管理器
        
        Args:
            workspace_manager: WorkspaceManager 实例，用于存储用户自定义模板
        """
        self.workspace_manager = workspace_manager
        self._templates: Dict[str, PromptTemplate] = {}
        self._user_templates: Dict[str, Dict[str, PromptTemplate]] = {}  # user_id -> templates
        
        # 加载默认模板
        self._load_default_templates()
    
    def _load_default_templates(self) -> None:
        """加载默认模板库"""
        for name, template in DEFAULT_TEMPLATES.items():
            self._templates[name] = template
    
    def get_template(self, name: str, user_id: Optional[str] = None) -> Optional[PromptTemplate]:
        """
        获取模板
        
        优先级：
        1. 用户自定义模板
        2. 默认模板
        
        Args:
            name: 模板名称
            user_id: 用户 ID，如果提供则优先查找用户自定义模板
            
        Returns:
            PromptTemplate 或 None
        """
        # 检查用户自定义模板
        if user_id and user_id in self._user_templates:
            if name in self._user_templates[user_id]:
                return self._user_templates[user_id][name]
        
        # 返回默认模板
        return self._templates.get(name)
    
    def list_templates(self, user_id: Optional[str] = None) -> List[str]:
        """
        列出所有可用模板
        
        Args:
            user_id: 用户 ID，如果提供则包括用户自定义模板
            
        Returns:
            模板名称列表
        """
        templates = set(self._templates.keys())
        
        if user_id and user_id in self._user_templates:
            templates.update(self._user_templates[user_id].keys())
        
        return sorted(list(templates))
    
    def save_user_template(
        self, 
        user_id: str, 
        name: str, 
        template: PromptTemplate
    ) -> bool:
        """
        保存用户自定义模板
        
        Args:
            user_id: 用户 ID
            name: 模板名称
            template: PromptTemplate 对象
            
        Returns:
            是否保存成功
        """
        try:
            if user_id not in self._user_templates:
                self._user_templates[user_id] = {}
            
            self._user_templates[user_id][name] = template
            
            # 持久化到用户 workspace
            if self.workspace_manager:
                self._persist_user_template(user_id, name, template)
            
            return True
        except Exception as e:
            print(f"[PromptTemplateManager] 保存模板失败: {e}")
            return False
    
    def _persist_user_template(
        self, 
        user_id: str, 
        name: str, 
        template: PromptTemplate
    ) -> None:
        """将用户模板持久化到文件"""
        try:
            workspace = self.workspace_manager.get_workspace(user_id)
            templates_dir = workspace / "templates"
            templates_dir.mkdir(exist_ok=True)
            
            template_file = templates_dir / f"{name}.json"
            
            template_data = {
                "name": template.name,
                "description": template.description,
                "template": template.template,
                "required_variables": template.required_variables,
                "optional_variables": template.optional_variables,
                "version": template.version
            }
            
            template_file.write_text(
                json.dumps(template_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[PromptTemplateManager] 持久化模板失败: {e}")
    
    def load_user_templates(self, user_id: str) -> None:
        """从用户 workspace 加载自定义模板"""
        try:
            if not self.workspace_manager:
                return
            
            workspace = self.workspace_manager.get_workspace(user_id)
            templates_dir = workspace / "templates"
            
            if not templates_dir.exists():
                return
            
            for template_file in templates_dir.glob("*.json"):
                try:
                    data = json.loads(template_file.read_text(encoding="utf-8"))
                    template = PromptTemplate(
                        name=data["name"],
                        description=data["description"],
                        template=data["template"],
                        required_variables=data.get("required_variables", []),
                        optional_variables=data.get("optional_variables", []),
                        version=data.get("version", "1.0")
                    )
                    
                    if user_id not in self._user_templates:
                        self._user_templates[user_id] = {}
                    
                    self._user_templates[user_id][template.name] = template
                    
                except Exception as e:
                    print(f"[PromptTemplateManager] 加载模板 {template_file} 失败: {e}")
                    
        except Exception as e:
            print(f"[PromptTemplateManager] 加载用户模板失败: {e}")


class PromptRenderer:
    """Prompt 渲染器
    
    负责将模板和用户数据结合，生成最终 Prompt
    """
    
    def __init__(self, template_manager: PromptTemplateManager):
        self.template_manager = template_manager
    
    def render_report_prompt(
        self,
        user_id: str,
        report_type: ReportType,
        user_config: Any,  # UserConfig 对象
        user_persona: UserPersona,
        market_data: Optional[Dict[str, Any]] = None,
        news_data: Optional[List[Dict[str, Any]]] = None,
        influencer_data: Optional[List[Dict[str, Any]] = None,
        custom_template_name: Optional[str] = None
    ) -> str:
        """
        渲染报告生成 Prompt
        
        Args:
            user_id: 用户 ID
            report_type: 报告类型
            user_config: 用户配置对象
            user_persona: 用户画像
            market_data: 市场数据（可选）
            news_data: 新闻数据（可选）
            influencer_data: 大V观点（可选）
            custom_template_name: 自定义模板名称（可选）
            
        Returns:
            渲染后的 Prompt 字符串
        """
        # 1. 获取模板
        template_name = custom_template_name or f"{report_type.value}_report"
        template = self.template_manager.get_template(template_name, user_id)
        
        if not template:
            # 使用默认日报模板
            template = self.template_manager.get_template("daily_report")
        
        # 2. 准备变量
        variables = self._prepare_template_variables(
            user_id=user_id,
            report_type=report_type,
            user_config=user_config,
            user_persona=user_persona,
            market_data=market_data,
            news_data=news_data,
            influencer_data=influencer_data
        )
        
        # 3. 渲染模板
        return template.render(variables)
    
    def _prepare_template_variables(
        self,
        user_id: str,
        report_type: ReportType,
        user_config: Any,
        user_persona: UserPersona,
        market_data: Optional[Dict[str, Any]],
        news_data: Optional[List[Dict[str, Any]]],
        influencer_data: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """准备模板变量"""
        
        # 格式化关注列表
        watchlist_str = self._format_watchlist(user_config.watchlist)
        
        # 格式化用户画像
        persona_str = self._format_user_persona(user_persona)
        
        # 格式化市场数据
        market_data_str = self._format_market_data(market_data) if market_data else "数据待更新"
        
        # 格式化新闻数据
        news_str = self._format_news_data(news_data) if news_data else "数据待更新"
        
        # 格式化大V观点
        influencer_str = self._format_influencer_data(influencer_data) if influencer_data else "数据待更新"
        
        return {
            "user_id": user_id,
            "report_date": datetime.now().strftime("%Y年%m月%d日"),
            "report_type": report_type.value,
            "watchlist": watchlist_str,
            "user_persona": persona_str,
            "market_data": market_data_str,
            "news_summary": news_str,
            "influencer_opinions": influencer_str,
            "language": user_config.preferences.language,
            "report_format": user_config.preferences.report_format
        }
    
    def _format_watchlist(self, watchlist) -> str:
        """格式化关注列表"""
        lines = []
        
        if watchlist.stocks:
            lines.append(f"**股票标的**: {', '.join(watchlist.stocks)}")
        
        if watchlist.influencers:
            lines.append(f"**关注大V**: {', '.join(watchlist.influencers)}")
        
        if watchlist.keywords:
            lines.append(f"**关键词**: {', '.join(watchlist.keywords)}")
        
        if watchlist.sectors:
            lines.append(f"**关注板块**: {', '.join(watchlist.sectors)}")
        
        return "\n".join(lines) if lines else "暂无关注列表"
    
    def _format_user_persona(self, persona: UserPersona) -> str:
        """格式化用户画像"""
        lines = [
            f"**风险偏好**: {persona.risk_preference}",
            f"**投资经验**: {persona.investment_experience}",
            f"**投资周期**: {persona.investment_horizon}",
            f"**报告长度偏好**: {persona.preferred_report_length}"
        ]
        
        if persona.focus_areas:
            lines.append(f"**特别关注领域**: {', '.join(persona.focus_areas)}")
        
        if persona.avoid_topics:
            lines.append(f"**不感兴趣的内容**: {', '.join(persona.avoid_topics)}")
        
        return "\n".join(lines)
    
    def _format_market_data(self, data: Dict[str, Any]) -> str:
        """格式化市场数据"""
        if not data:
            return "市场数据待更新"
        
        lines = ["### 市场数据概览"]
        
        if "indices" in data:
            lines.append("\n**主要指数**:")
            for idx, values in data["indices"].items():
                change = values.get("change_pct", 0)
                lines.append(f"- {idx}: {values.get('value', 'N/A')} ({change:+.2f}%)")
        
        if "volume" in data:
            lines.append(f"\n**成交量**: {data['volume']}")
        
        return "\n".join(lines)
    
    def _format_news_data(self, news_list: List[Dict[str, Any]]) -> str:
        """格式化新闻数据"""
        if not news_list:
            return "新闻数据待更新"
        
        lines = ["### 重要新闻摘要", ""]
        
        for i, news in enumerate(news_list[:5], 1):  # 只显示前5条
            title = news.get("title", "无标题")
            source = news.get("source", "未知来源")
            summary = news.get("summary", "")
            
            lines.append(f"{i}. **{title}**")
            lines.append(f"   来源: {source}")
            if summary:
                lines.append(f"   摘要: {summary}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_influencer_data(self, opinions: List[Dict[str, Any]]) -> str:
        """格式化大V观点数据"""
        if not opinions:
            return "大V观点数据待更新"
        
        lines = ["### 关注大V观点汇总", ""]
        
        for opinion in opinions:
            influencer = opinion.get("influencer", "未知")
            content = opinion.get("content", "")
            sentiment = opinion.get("sentiment", "neutral")  # bullish, bearish, neutral
            timestamp = opinion.get("timestamp", "")
            
            # 根据情感倾向添加标记
            sentiment_emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}
            emoji = sentiment_emoji.get(sentiment, "➡️")
            
            lines.append(f"**{influencer}** {emoji}")
            lines.append(f"> {content}")
            if timestamp:
                lines.append(f"*发布时间: {timestamp}*")
            lines.append("")
        
        return "\n".join(lines)


# 便捷函数：快速创建报告 Prompt
def create_report_prompt(
    user_id: str,
    report_type: str,
    user_config: Any,
    user_persona: Optional[UserPersona] = None,
    **kwargs
) -> str:
    """
    快速创建报告生成的 Prompt
    
    Args:
        user_id: 用户 ID
        report_type: 报告类型 (daily, weekly, monthly, realtime)
        user_config: 用户配置对象
        user_persona: 用户画像（可选）
        **kwargs: 额外的数据（market_data, news_data 等）
        
    Returns:
        完整的 Prompt 字符串
    """
    template_manager = PromptTemplateManager()
    renderer = PromptRenderer(template_manager)
    
    # 如果没有提供 user_persona，使用默认的
    if user_persona is None:
        user_persona = UserPersona()
    
    # 准备变量
    variables = {
        "user_id": user_id,
        "report_date": datetime.now().strftime("%Y年%m月%d日"),
        "report_type": report_type,
        "watchlist": renderer._format_watchlist(user_config.watchlist),
        "user_persona": renderer._format_user_persona(user_persona),
        "language": user_config.preferences.language,
        "report_format": user_config.preferences.report_format,
        **kwargs
    }
    
    # 获取模板
    template_name = f"{report_type}_report"
    template = template_manager.get_template(template_name, user_id)
    
    if not template:
        template = template_manager.get_template("daily_report")
    
    # 渲染模板
    return template.render(variables)


# 导出主要类
__all__ = [
    'PromptTemplate',
    'PromptTemplateManager',
    'PromptRenderer',
    'UserPersona',
    'ReportType',
    'ReportSection',
    'create_report_prompt',
    'DEFAULT_TEMPLATES'
]