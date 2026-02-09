"""报告生成器模块

负责生成投资分析报告，包括：
1. 动态 Prompt 组装
2. LLM 调用生成报告
3. 报告格式化和保存
4. 支持多种报告类型（日报、周报、实时提醒）
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

from loguru import logger

# 导入必要的内部模块
try:
    from nanobot.services.prompt_templates import (
        PromptTemplateManager,
        PromptRenderer,
        UserPersona,
        ReportType
    )
    from nanobot.services.user_config import UserConfigManager, UserConfig
    from nanobot.workspace.manager import WorkspaceManager
    from nanobot.agent.multi_tenant_loop import MultiTenantAgentLoop
    from nanobot.services.data_fetcher import DataFetcher, UserPreferenceFetcher
except ImportError as e:
    logger.error(f"导入模块失败: {e}")
    # 定义占位符以便在没有依赖时也能导入
    PromptTemplateManager = None
    UserConfigManager = None
    WorkspaceManager = None
    MultiTenantAgentLoop = None
    DataFetcher = None
    UserPreferenceFetcher = None


class ReportGenerator:
    """
    报告生成器
    
    职责：
    1. 管理 Prompt 模板
    2. 组装生成报告所需的上下文和数据
    3. 调用 LLM 生成报告内容
    4. 格式化并保存报告
    
    Example:
        generator = ReportGenerator(
            config_manager=config_manager,
            workspace_manager=workspace_manager,
            agent_loop=agent_loop
        )
        
        result = await generator.generate_report(
            user_id="user_001",
            report_type="daily"
        )
    """
    
    def __init__(
        self,
        config_manager: Any,
        workspace_manager: Any,
        agent_loop: Optional[Any] = None,
        template_manager: Optional[Any] = None,
        data_fetcher: Optional[Any] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化报告生成器
        
        Args:
            config_manager: 用户配置管理器
            workspace_manager: 工作空间管理器
            agent_loop: 多租户 Agent Loop（用于调用 LLM）
            template_manager: Prompt 模板管理器（可选）
            data_fetcher: 数据获取器（可选）
            max_retries: 生成失败时的最大重试次数
            retry_delay: 重试间隔（秒）
        """
        self.config_manager = config_manager
        self.workspace_manager = workspace_manager
        self.agent_loop = agent_loop
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 初始化模板管理器
        if template_manager:
            self.template_manager = template_manager
        elif PromptTemplateManager:
            self.template_manager = PromptTemplateManager(workspace_manager)
        else:
            self.template_manager = None
            logger.warning("PromptTemplateManager 不可用")
        
        # 初始化渲染器
        if PromptRenderer and self.template_manager:
            self.prompt_renderer = PromptRenderer(self.template_manager)
        else:
            self.prompt_renderer = None
        
        # 初始化数据获取器
        if data_fetcher:
            self.data_fetcher = data_fetcher
        elif DataFetcher:
            self.data_fetcher = DataFetcher()
        else:
            self.data_fetcher = None
            logger.warning("DataFetcher 不可用")
        
        logger.info("[ReportGenerator] 初始化完成")
    
    async def generate_report(
        self,
        user_id: str,
        report_type: str = "daily",
        custom_data: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        生成投资报告
        
        Args:
            user_id: 用户 ID
            report_type: 报告类型 (daily, weekly, monthly, realtime)
            custom_data: 自定义数据（如外部提供的市场数据、新闻等）
            use_cache: 是否使用缓存
            
        Returns:
            包含报告信息的字典：
            {
                "success": bool,
                "report_id": str,
                "report_path": str,
                "content": str,
                "metadata": Dict[str, Any],
                "error": Optional[str]
            }
        """
        logger.info(f"[ReportGenerator] 开始生成报告: user={user_id}, type={report_type}")
        
        try:
            # 1. 获取用户配置
            user_config = self.config_manager.get_config(user_id)
            if not user_config:
                raise ValueError(f"用户 {user_id} 不存在")
            
            # 2. 获取或创建用户画像
            user_persona = self._get_user_persona(user_id, user_config)
            
            # 3. 准备数据（如果没有提供外部数据，使用数据获取器收集）
            if custom_data:
                market_data = custom_data.get("market_data", "{}")
                assets_data = custom_data.get("assets_data", "[]")
                user_preference = custom_data.get("user_preference", "{}")
            else:
                # 自动获取数据
                market_context, assets_details, user_preference = await self._collect_report_data(user_config, user_persona)
                
                market_data = json.dumps(market_context.to_dict(), ensure_ascii=False, indent=2)
                assets_data = json.dumps([asset.to_dict() for asset in assets_details], ensure_ascii=False, indent=2)
            
            # 4. 生成 Prompt
            prompt = await self._generate_enhanced_prompt(
                user_id=user_id,
                report_type=report_type,
                user_config=user_config,
                user_persona=user_persona,
                market_data=market_data,
                assets_data=assets_data,
                user_preference=user_preference
            )
            
            # 5. 调用 LLM 生成报告
            report_content = await self._call_llm_with_retry(
                prompt=prompt,
                user_id=user_id,
                report_type=report_type
            )
            
            # 6. 保存报告到文件
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
                    "generated_at": datetime.now().isoformat(),
                    "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt
                }
            }
            
        except Exception as e:
            logger.error(f"[ReportGenerator] 报告生成失败: {e}", exc_info=True)
            return {
                "success": False,
                "report_id": None,
                "report_path": None,
                "content": None,
                "metadata": None,
                "error": str(e)
            }
    
    async def _collect_report_data(
        self,
        user_config: Any,
        user_persona: Any
    ) -> tuple:
        """
        收集报告所需的数据
        
        Args:
            user_config: 用户配置
            user_persona: 用户画像
            
        Returns:
            (market_context, assets_details, user_preference)
        """
        logger.info("[ReportGenerator] 收集报告数据...")
        
        # 并行获取市场数据和用户偏好
        market_context_task = self.data_fetcher.fetch_market_context() if self.data_fetcher else None
        user_preference = UserPreferenceFetcher.get_user_preference(user_config) if UserPreferenceFetcher else {}
        
        # 获取用户关注的标的
        symbols = getattr(user_config.watchlist, 'stocks', [])
        
        # 获取标的详细数据
        assets_details = []
        if self.data_fetcher and symbols:
            assets_details = await self.data_fetcher.fetch_asset_details(symbols)
        
        # 获取市场上下文
        market_context = await market_context_task if market_context_task else None
        if not market_context:
            from nanobot.services.data_fetcher import MarketContext
            market_context = MarketContext()
        
        return market_context, assets_details, user_preference
    
    async def _generate_enhanced_prompt(
        self,
        user_id: str,
        report_type: str,
        user_config: Any,
        user_persona: Any,
        market_data: str,
        assets_data: str,
        user_preference: str
    ) -> str:
        """
        生成增强版 Prompt（使用新的模板结构）
        
        Args:
            user_id: 用户 ID
            report_type: 报告类型
            user_config: 用户配置
            user_persona: 用户画像
            market_data: 市场数据 JSON 字符串
            assets_data: 标的详细数据 JSON 字符串
            user_preference: 用户偏好 JSON 字符串
            
        Returns:
            完整的 Prompt 字符串
        """
        # 获取模板
        template = self.template_manager.get_template("daily_report", user_id) if self.template_manager else None
        if not template:
            return self._generate_simple_prompt(user_id, report_type, user_config, user_persona)
        
        # 准备变量
        variables = {
            "user_id": user_id,
            "report_date": datetime.now().strftime("%Y年%m月%d日"),
            "watchlist": assets_data,
            "user_persona": self._format_user_preference(user_preference),
            "market_data": market_data,
            "news_summary": "",
            "influencer_opinions": ""
        }
        
        return template.render(variables)
    
    def _format_user_preference(self, user_preference: Any) -> str:
        """
        格式化用户偏好
        
        Args:
            user_preference: 用户偏好数据（dict 或 JSON 字符串）
            
        Returns:
            格式化后的字符串
        """
        import json
        
        if isinstance(user_preference, str):
            try:
                user_preference = json.loads(user_preference)
            except:
                return user_preference
        
        if isinstance(user_preference, dict):
            investment_style = user_preference.get("investment_style", "价值投资")
            risk_level = user_preference.get("risk_level", "中等")
            
            return f"""
**投资风格**: {investment_style}
**风险等级**: {risk_level}
"""
        
        return str(user_preference)
    
    def _get_user_persona(self, user_id: str, user_config) -> Any:
        """
        获取用户画像
        
        目前从用户配置中推断，后续可以从专门的用户画像服务获取
        """
        # 从 watchlist 和 preferences 推断风险偏好
        risk_map = {
            "conservative": "conservative",
            "moderate": "moderate",
            "aggressive": "aggressive"
        }
        
        # 从 config.json 中读取用户画像数据（如果有）
        persona_data = getattr(user_config, 'custom_data', {}).get('persona', {})
        
        # 检查 UserPersona 是否可用
        if 'UserPersona' in globals() and UserPersona:
            return UserPersona(
                risk_preference=persona_data.get('risk_preference', 'moderate'),
                investment_experience=persona_data.get('investment_experience', 'intermediate'),
                investment_horizon=persona_data.get('investment_horizon', 'medium'),
                preferred_report_length=persona_data.get('preferred_report_length', 'medium'),
                focus_areas=persona_data.get('focus_areas', []),
                avoid_topics=persona_data.get('avoid_topics', [])
            )
        else:
            return {"risk_preference": "moderate"}
    
    async def _call_llm_with_retry(
        self,
        prompt: str,
        user_id: str,
        report_type: str
    ) -> str:
        """
        调用 LLM 生成报告，带重试机制
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"[ReportGenerator] 调用 LLM 尝试 {attempt + 1}/{self.max_retries}")
                
                if self.agent_loop:
                    # 使用 MultiTenantAgentLoop 调用 LLM
                    # 需要先切换到用户 workspace
                    if hasattr(self.agent_loop, 'switch_workspace'):
                        self.agent_loop.switch_workspace(user_id)
                    
                    # 调用 agent 处理
                    response = await self.agent_loop.process_direct(
                        content=prompt,
                        session_key=f"report_generation:{user_id}:{report_type}",
                        channel="report_generator",
                        chat_id=user_id
                    )
                    
                    return response
                else:
                    # 降级方案：返回提示信息
                    logger.warning("[ReportGenerator] AgentLoop 不可用，返回模拟报告")
                    return self._generate_mock_report(report_type, user_id)
                    
            except Exception as e:
                last_error = e
                logger.warning(f"[ReportGenerator] 调用 LLM 失败 (尝试 {attempt + 1}): {e}")
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.info(f"[ReportGenerator] 等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
        
        # 所有重试都失败了
        raise Exception(f"调用 LLM 失败，已重试 {self.max_retries} 次: {last_error}")
    
    def _generate_mock_report(self, report_type: str, user_id: str) -> str:
        """生成模拟报告（用于测试或降级场景）"""
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
    
    def _generate_simple_prompt(
        self,
        user_id: str,
        report_type: str,
        user_config: Any,
        user_persona: Any
    ) -> str:
        """
        生成简单的 Prompt（降级方案）
        """
        watchlist = user_config.watchlist
        
        return f"""请为用户 {user_id} 生成一份 {report_type} 投资报告。

## 用户关注列表
- 股票: {', '.join(watchlist.stocks) if watchlist.stocks else '无'}
- 关注大V: {', '.join(watchlist.influencers) if watchlist.influencers else '无'}
- 关键词: {', '.join(watchlist.keywords) if watchlist.keywords else '无'}

## 用户画像
- 风险偏好: {user_persona.risk_preference}
- 投资经验: {user_persona.investment_experience}

请生成一份专业的投资报告，包含市场概览、关注标的分析和投资建议。
"""
    
    def _save_report(
        self,
        user_id: str,
        report_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Path:
        """
        保存报告到用户工作空间
        
        Args:
            user_id: 用户 ID
            report_id: 报告 ID
            content: 报告内容
            metadata: 报告元数据
            
        Returns:
            报告文件路径
        """
        # 获取用户 workspace
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


# 便捷函数：快速生成报告
def create_report_generator(
    config_manager: Any,
    workspace_manager: Any,
    agent_loop: Optional[Any] = None
) -> ReportGenerator:
    """
    快速创建报告生成器实例
    
    Args:
        config_manager: 用户配置管理器
        workspace_manager: 工作空间管理器
        agent_loop: 多租户 Agent Loop（可选）
        
    Returns:
        ReportGenerator 实例
    """
    return ReportGenerator(
        config_manager=config_manager,
        workspace_manager=workspace_manager,
        agent_loop=agent_loop
    )


# 导出主要类和函数
__all__ = [
    'ReportGenerator',
    'create_report_generator'
]