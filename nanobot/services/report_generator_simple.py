"""报告生成器 - 完整实现

提供基于 Prompt 模板的投资报告生成功能。
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

from loguru import logger


class ReportGenerator:
    """投资报告生成器"""
    
    def __init__(
        self,
        config_manager,
        workspace_manager,
        agent_loop=None,
        max_retries: int = 3
    ):
        self.config_manager = config_manager
        self.workspace_manager = workspace_manager
        self.agent_loop = agent_loop
        self.max_retries = max_retries
        logger.info("[ReportGenerator] 初始化完成")
    
    async def generate_report(
        self,
        user_id: str,
        report_type: str = "daily",
        custom_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成投资报告"""
        
        logger.info(f"[ReportGenerator] 开始生成报告: user={user_id}, type={report_type}")
        
        try:
            # 1. 获取用户配置
            user_config = self.config_manager.get_config(user_id)
            if not user_config:
                raise ValueError(f"用户 {user_id} 不存在")
            
            # 2. 构建 Prompt
            prompt = self._build_prompt(
                user_id=user_id,
                report_type=report_type,
                user_config=user_config,
                custom_data=custom_data or {}
            )
            
            # 3. 调用 LLM 生成报告
            report_content = await self._call_llm_with_retry(
                prompt=prompt,
                user_id=user_id,
                report_type=report_type
            )
            
            # 4. 保存报告
            report_id = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            report_path = self._save_report(
                user_id=user_id,
                report_id=report_id,
                content=report_content,
                metadata={
                    "report_type": report_type,
                    "user_id": user_id,
                    "generated_at": datetime.now().isoformat(),
                    "prompt_length": len(prompt),
                    "content_length": len(report_content)
                }
            )
            
            logger.info(f"[ReportGenerator] 报告生成成功: {report_id}")
            
            return {
                "success": True,
                "report_id": report_id,
                "report_path": str(report_path),
                "content": report_content,
                "metadata": {
                    "report_type": report_type,
                    "user_id": user_id,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"[ReportGenerator] 报告生成失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_prompt(
        self,
        user_id: str,
        report_type: str,
        user_config: Any,
        custom_data: Dict[str, Any]
    ) -> str:
        """构建 Prompt"""
        
        watchlist = user_config.watchlist
        preferences = user_config.preferences
        
        # 格式化关注列表
        watchlist_text = self._format_watchlist(watchlist)
        
        # 获取用户画像信息
        custom_persona = user_config.custom_data.get('persona', {})
        
        # 构建 Prompt
        prompt = f"""# 投资报告生成任务

## 角色设定
你是一位专业的投资分析师，拥有10年以上的金融市场分析经验。你需要根据用户的投资偏好和风险承受能力，生成个性化的投资报告。

## 用户基本信息
- **用户ID**: {user_id}
- **报告类型**: {report_type}
- **报告日期**: {datetime.now().strftime("%Y年%m月%d日")}
- **语言偏好**: {preferences.language}

## 用户关注列表
{watchlist_text}

## 用户画像
- **风险偏好**: {custom_persona.get('risk_preference', 'moderate')}
- **投资经验**: {custom_persona.get('investment_experience', 'intermediate')}
- **投资周期**: {custom_persona.get('investment_horizon', 'medium')}
- **报告长度偏好**: {custom_persona.get('preferred_report_length', 'medium')}
{self._format_additional_preferences(custom_persona)}

{self._format_custom_data(custom_data)}

## 任务要求

### 1. 内容要求

根据报告类型 **{report_type}**，生成相应的内容：

**如果是日报 (daily)**:
1. **市场概览**（200-300字）：当日大盘主要指数表现、板块轮动情况、成交量变化
2. **重点标的分析**（每个关注标的100-150字）：股价表现、技术面简析、相关新闻
3. **大V观点汇总**（150-200字）：关注大V当日重要观点及倾向性
4. **明日关注要点**（100字）：次日重要财经事件和风险点

**如果是周报 (weekly)**:
1. **本周市场回顾**（300-400字）：主要指数周涨跌幅、板块轮动特征、资金流向
2. **关注标的周表现**（每只股票150-200字）：股价表现、技术面分析、估值对比
3. **板块/行业分析**（300字）：关注行业动态、政策影响
4. **下周展望**（200字）：重要事件、潜在风险和机会

**如果是实时提醒 (realtime)**:
1. **异动概述**（100字）：触发的事件、涉及标的
2. **影响分析**（150字）：对关注标的的潜在影响、板块联动
3. **关注要点**（100字）：建议关注的时间节点

### 2. 格式要求
- 使用 Markdown 格式
- 一级标题 `#` 用于报告标题
- 二级标题 `##` 用于主要章节
- 三级标题 `###` 用于小节
- 使用 `-` 或 `*` 表示列表项
- 重要数据和观点使用 **加粗** 强调

### 3. 风格要求
- 根据用户的风险偏好调整语气：
  - **保守型**：强调风险，建议谨慎操作，避免激进语言
  - **激进型**：突出机会，但仍需提示风险，语气积极
  - **平衡型**：客观分析，给出不同情境下的建议
- 语言简洁专业，避免冗余
- 数据驱动的分析，避免主观臆断

### 4. 限制条件
- **日报**: 总长度控制在 1500-2000 字
- **周报**: 总长度控制在 2500-3000 字
- **实时提醒**: 总长度控制在 400-500 字
- 不要编造不存在的数据（如果缺少某些数据，明确说明"数据待更新"）
- 不要给出具体的投资建议（如"买入"或"卖出"），只提供分析
- 不要泄露其他用户的信息
- 不要推荐具体的产品或服务

## 输出格式
请直接输出完整的 Markdown 格式报告，不要包含任务说明或其他元信息。报告应该直接可用，不需要进一步处理。

**重要提醒**：
1. 确保内容真实可靠，不编造数据
2. 根据用户的风险偏好调整语气和建议
3. 严格遵守字数限制
4. 使用 Markdown 格式，层次清晰
"""
        
        return prompt
    
    def _format_watchlist(self, watchlist) -> str:
        """格式化关注列表"""
        lines = []
        
        if watchlist.stocks:
            lines.append(f"- **股票标的**: {', '.join(watchlist.stocks)}")
        
        if watchlist.influencers:
            lines.append(f"- **关注大V**: {', '.join(watchlist.influencers)}")
        
        if watchlist.keywords:
            lines.append(f"- **关键词**: {', '.join(watchlist.keywords)}")
        
        if watchlist.sectors:
            lines.append(f"- **关注板块**: {', '.join(watchlist.sectors)}")
        
        return "\n".join(lines) if lines else "- 暂无关注列表"
    
    def _format_additional_preferences(self, persona: Dict[str, Any]) -> str:
        """格式化额外的偏好设置"""
        lines = []
        
        if persona.get('focus_areas'):
            lines.append(f"- **特别关注领域**: {', '.join(persona['focus_areas'])}")
        
        if persona.get('avoid_topics'):
            lines.append(f"- **不感兴趣的内容**: {', '.join(persona['avoid_topics'])}")
        
        return "\n".join(lines)
    
    def _format_custom_data(self, custom_data: Dict[str, Any]) -> str:
        """格式化自定义数据"""
        sections = []
        
        if custom_data.get('market_data'):
            sections.append("## 市场数据\n" + self._format_market_data(custom_data['market_data']))
        
        if custom_data.get('news_data'):
            sections.append("## 新闻数据\n" + self._format_news_data(custom_data['news_data']))
        
        if custom_data.get('influencer_data'):
            sections.append("## 大V观点\n" + self._format_influencer_data(custom_data['influencer_data']))
        
        return "\n\n".join(sections) if sections else ""
    
    def _format_market_data(self, data: Dict[str, Any]) -> str:
        """格式化市场数据"""
        lines = []
        if data.get('indices'):
            for idx, values in data['indices'].items():
                change = values.get('change_pct', 0)
                lines.append(f"- {idx}: {values.get('value', 'N/A')} ({change:+.2f}%)")
        return "\n".join(lines) if lines else "暂无市场数据"
    
    def _format_news_data(self, news_list: List[Dict[str, Any]]) -> str:
        """格式化新闻数据"""
        if not news_list:
            return "暂无新闻数据"
        
        lines = []
        for i, news in enumerate(news_list[:5], 1):
            lines.append(f"{i}. **{news.get('title', '无标题')}**")
            lines.append(f"   来源: {news.get('source', '未知')}")
            if news.get('summary'):
                lines.append(f"   摘要: {news['summary']}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_influencer_data(self, opinions: List[Dict[str, Any]]) -> str:
        """格式化大V观点数据"""
        if not opinions:
            return "暂无大V观点"
        
        lines = []
        for opinion in opinions:
            influencer = opinion.get("influencer", "未知")
            content = opinion.get("content", "")
            sentiment = opinion.get("sentiment", "neutral")
            
            emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}.get(sentiment, "➡️")
            
            lines.append(f"**{influencer}** {emoji}")
            lines.append(f"> {content}")
            lines.append("")
        
        return "\n".join(lines)
    
    async def _call_llm_with_retry(
        self,
        prompt: str,
        user_id: str,
        report_type: str
    ) -> str:
        """调用 LLM 生成报告，带重试机制"""
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"[ReportGenerator] 调用 LLM 尝试 {attempt + 1}/{self.max_retries}")
                
                if self.agent_loop:
                    # 使用 MultiTenantAgentLoop 调用 LLM
                    if hasattr(self.agent_loop, 'switch_workspace'):
                        self.agent_loop.switch_workspace(user_id)
                    
                    response = await self.agent_loop.process_direct(
                        content=prompt,
                        session_key=f"report_generation:{user_id}:{report_type}",
                        channel="report_generator",
                        chat_id=user_id
                    )
                    
                    return response
                else:
                    # 降级方案
                    logger.warning("[ReportGenerator] AgentLoop 不可用，返回模拟报告")
                    return self._generate_mock_report(report_type, user_id)
                    
            except Exception as e:
                last_error = e
                logger.warning(f"[ReportGenerator] 调用 LLM 失败 (尝试 {attempt + 1}): {e}")
                
                if attempt < self.max_retries - 1:
                    wait_time = 1.0 * (attempt + 1)
                    logger.info(f"[ReportGenerator] 等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
        
        raise Exception(f"调用 LLM 失败，已重试 {self.max_retries} 次: {last_error}")
    
    def _generate_mock_report(self, report_type: str, user_id: str) -> str:
        """生成模拟报告"""
        now = datetime.now().strftime("%Y年%m月%d日")
        
        return f"""# {report_type.upper()} 投资报告

**生成时间**: {now}  
**用户**: {user_id}  
**报告类型**: {report_type}

---

## 注意

这是系统生成的模拟报告。实际报告将包含：
- 市场概览和分析
- 关注标的的详细分析
- 大V观点汇总
- 投资建议和风险提示

请确保系统已正确配置 LLM 服务以生成完整报告。

---

*此报告由 nanobot 自动生成*
"""
    
    def _save_report(
        self,
        user_id: str,
        report_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Path:
        """保存报告到用户工作空间"""
        
        workspace = self.workspace_manager.get_workspace(user_id)
        reports_dir = workspace / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        # 保存报告内容
        report_file = reports_dir / f"{report_id}.md"
        report_file.write_text(content, encoding="utf-8")
        
        # 保存元数据
        metadata_file = reports_dir / f"{report_id}.json"
        metadata_file.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        logger.info(f"[ReportGenerator] 报告已保存: {report_file}")
        
        return report_file
    
    def _build_prompt(
        self,
        user_id: str,
        report_type: str,
        user_config: Any,
        custom_data: Dict[str, Any]
    ) -> str:
        """构建 Prompt"""
        
        watchlist = user_config.watchlist
        preferences = user_config.preferences
        
        # 格式化关注列表
        watchlist_text = self._format_watchlist(watchlist)
        
        # 获取用户画像信息
        custom_persona = user_config.custom_data.get('persona', {})
        
        # 构建 Prompt
        prompt = f"""# 投资报告生成任务

## 角色设定
你是一位专业的投资分析师，拥有10年以上的金融市场分析经验。你需要根据用户的投资偏好和风险承受能力，生成个性化的投资报告。

## 用户基本信息
- **用户ID**: {user_id}
- **报告类型**: {report_type}
- **报告日期**: {datetime.now().strftime("%Y年%m月%d日")}
- **语言偏好**: {preferences.language}

## 用户关注列表
{watchlist_text}

## 用户画像
- **风险偏好**: {custom_persona.get('risk_preference', 'moderate')}
- **投资经验**: {custom_persona.get('investment_experience', 'intermediate')}
- **投资周期**: {custom_persona.get('investment_horizon', 'medium')}
- **报告长度偏好**: {custom_persona.get('preferred_report_length', 'medium')}
{self._format_additional_preferences(custom_persona)}

{self._format_custom_data(custom_data)}

## 任务要求

### 1. 内容要求

根据报告类型 **{report_type}**，生成相应的内容：

**如果是日报 (daily)**:
1. **市场概览**（200-300字）：当日大盘主要指数表现、板块轮动情况、成交量变化
2. **重点标的分析**（每个关注标的100-150字）：股价表现、技术面简析、相关新闻
3. **大V观点汇总**（150-200字）：关注大V当日重要观点及倾向性
4. **明日关注要点**（100字）：次日重要财经事件和风险点

**如果是周报 (weekly)**:
1. **本周市场回顾**（300-400字）：主要指数周涨跌幅、板块轮动特征、资金流向
2. **关注标的周表现**（每只股票150-200字）：股价表现、技术面分析、估值对比
3. **板块/行业分析**（300字）：关注行业动态、政策影响
4. **下周展望**（200字）：重要事件、潜在风险和机会

**如果是实时提醒 (realtime)**:
1. **异动概述**（100字）：触发的事件、涉及标的
2. **影响分析**（150字）：对关注标的的潜在影响、板块联动
3. **关注要点**（100字）：建议关注的时间节点

### 2. 格式要求
- 使用 Markdown 格式
- 一级标题 `#` 用于报告标题
- 二级标题 `##` 用于主要章节
- 三级标题 `###` 用于小节
- 使用 `-` 或 `*` 表示列表项
- 重要数据和观点使用 **加粗** 强调

### 3. 风格要求
- 根据用户的风险偏好调整语气：
  - **保守型**：强调风险，建议谨慎操作，避免激进语言
  - **激进型**：突出机会，但仍需提示风险，语气积极
  - **平衡型**：客观分析，给出不同情境下的建议
- 语言简洁专业，避免冗余
- 数据驱动的分析，避免主观臆断

### 4. 限制条件
- **日报**: 总长度控制在 1500-2000 字
- **周报**: 总长度控制在 2500-3000 字
- **实时提醒**: 总长度控制在 400-500 字
- 不要编造不存在的数据（如果缺少某些数据，明确说明"数据待更新"）
- 不要给出具体的投资建议（如"买入"或"卖出"），只提供分析
- 不要泄露其他用户的信息
- 不要推荐具体的产品或服务

## 输出格式
请直接输出完整的 Markdown 格式报告，不要包含任务说明或其他元信息。报告应该直接可用，不需要进一步处理。

**重要提醒**：
1. 确保内容真实可靠，不编造数据
2. 根据用户的风险偏好调整语气和建议
3. 严格遵守字数限制
4. 使用 Markdown 格式，层次清晰
"""
        
        return prompt
    
    def _format_watchlist(self, watchlist) -> str:
        """格式化关注列表"""
        lines = []
        
        if watchlist.stocks:
            lines.append(f"- **股票标的**: {', '.join(watchlist.stocks)}")
        
        if watchlist.influencers:
            lines.append(f"- **关注大V**: {', '.join(watchlist.influencers)}")
        
        if watchlist.keywords:
            lines.append(f"- **关键词**: {', '.join(watchlist.keywords)}")
        
        if watchlist.sectors:
            lines.append(f"- **关注板块**: {', '.join(watchlist.sectors)}")
        
        return "\n".join(lines) if lines else "- 暂无关注列表"
    
    def _format_additional_preferences(self, persona: Dict[str, Any]) -> str:
        """格式化额外的偏好设置"""
        lines = []
        
        if persona.get('focus_areas'):
            lines.append(f"- **特别关注领域**: {', '.join(persona['focus_areas'])}")
        
        if persona.get('avoid_topics'):
            lines.append(f"- **不感兴趣的内容**: {', '.join(persona['avoid_topics'])}")
        
        return "\n".join(lines)
    
    def _format_custom_data(self, custom_data: Dict[str, Any]) -> str:
        """格式化自定义数据"""
        sections = []
        
        if custom_data.get('market_data'):
            sections.append("## 市场数据\n" + self._format_market_data(custom_data['market_data']))
        
        if custom_data.get('news_data'):
            sections.append("## 新闻数据\n" + self._format_news_data(custom_data['news_data']))
        
        if custom_data.get('influencer_data'):
            sections.append("## 大V观点\n" + self._format_influencer_data(custom_data['influencer_data']))
        
        return "\n\n".join(sections) if sections else ""
    
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
        
        return "\n".join(lines)
    
    def _format_news_data(self, news_list: List[Dict[str, Any]]) -> str:
        """格式化新闻数据"""
        if not news_list:
            return "暂无新闻数据"
        
        lines = ["### 重要新闻摘要", ""]
        
        for i, news in enumerate(news_list[:5], 1):
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
            return "暂无大V观点"
        
        lines = ["### 关注大V观点汇总", ""]
        
        for opinion in opinions:
            influencer = opinion.get("influencer", "未知")
            content = opinion.get("content", "")
            sentiment = opinion.get("sentiment", "neutral")
            
            emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}.get(sentiment, "➡️")
            
            lines.append(f"**{influencer}** {emoji}")
            lines.append(f"> {content}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _save_report(
        self,
        user_id: str,
        report_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Path:
        """保存报告到用户工作空间"""
        
        workspace = self.workspace_manager.get_workspace(user_id)
        reports_dir = workspace / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        # 保存报告内容
        report_file = reports_dir / f"{report_id}.md"
        report_file.write_text(content, encoding="utf-8")
        
        # 保存元数据
        metadata_file = reports_dir / f"{report_id}.json"
        metadata_file.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        logger.info(f"[ReportGenerator] 报告已保存: {report_file}")
        
        return report_file


# 导出主要类
__all__ = ['ReportGenerator']