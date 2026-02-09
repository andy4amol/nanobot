"""数据获取服务

负责从各种数据源获取报告所需的数据：
1. 市场宏观数据（热门话题、大V观点）
2. 标的详细数据（行情、财务、公告、异动）
3. 用户偏好数据
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from loguru import logger


@dataclass
class MarketContext:
    """市场宏观上下文"""
    hot_topics: List[Dict[str, Any]] = None
    big_v_general_views: str = ""
    market_sentiment: str = "中性"
    
    def __post_init__(self):
        if self.hot_topics is None:
            self.hot_topics = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hot_topics": self.hot_topics,
            "big_v_general_views": self.big_v_general_views,
            "market_sentiment": self.market_sentiment
        }


@dataclass
class AssetDetail:
    """标的详细数据"""
    symbol: str
    name: str
    market_data: Dict[str, Any] = None
    financial_data: Dict[str, Any] = None
    announcements: List[Dict[str, Any]] = None
    abnormal_movements: List[Dict[str, Any]] = None
    related_articles: List[Dict[str, Any]] = None
    specific_big_v_views: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.market_data is None:
            self.market_data = {}
        if self.financial_data is None:
            self.financial_data = {}
        if self.announcements is None:
            self.announcements = []
        if self.abnormal_movements is None:
            self.abnormal_movements = []
        if self.related_articles is None:
            self.related_articles = []
        if self.specific_big_v_views is None:
            self.specific_big_v_views = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "market_data": self.market_data,
            "financial_data": self.financial_data,
            "announcements": self.announcements,
            "abnormal_movements": self.abnormal_movements,
            "related_articles": self.related_articles,
            "specific_big_v_views": self.specific_big_v_views
        }


class DataFetcher:
    """数据获取器
    
    负责从各个数据源获取报告所需的数据
    """
    
    def __init__(self, api_client=None):
        """
        初始化数据获取器
        
        Args:
            api_client: API 客户端实例（可选）
        """
        self.api_client = api_client
    
    async def fetch_market_context(self) -> MarketContext:
        """
        获取市场宏观上下文
        
        Returns:
            MarketContext 对象
        """
        try:
            logger.info("[DataFetcher] 获取市场宏观上下文...")
            
            # 并行获取市场热门话题和大V观点
            hot_topics_result, big_v_views_result, sentiment_result = await asyncio.gather(
                self._fetch_hot_topics(),
                self._fetch_big_v_general_views(),
                self._fetch_market_sentiment(),
                return_exceptions=True
            )
            
            hot_topics = hot_topics_result if not isinstance(hot_topics_result, Exception) else []
            big_v_views = big_v_views_result if not isinstance(big_v_views_result, Exception) else ""
            sentiment = sentiment_result if not isinstance(sentiment_result, Exception) else "中性"
            
            return MarketContext(
                hot_topics=hot_topics,
                big_v_general_views=big_v_views,
                market_sentiment=sentiment
            )
            
        except Exception as e:
            logger.error(f"[DataFetcher] 获取市场上下文失败: {e}")
            return MarketContext()
    
    async def _fetch_hot_topics(self) -> List[Dict[str, Any]]:
        """获取市场热门话题"""
        if self.api_client and hasattr(self.api_client, 'get_hot_topics'):
            return await self.api_client.get_hot_topics()
        
        logger.warning("[DataFetcher] 未配置热门话题API，返回空数据")
        return []
    
    async def _fetch_big_v_general_views(self) -> str:
        """获取大V对大盘的整体看法"""
        if self.api_client and hasattr(self.api_client, 'get_big_v_views'):
            views = await self.api_client.get_big_v_views()
            return self._format_big_v_views(views)
        
        logger.warning("[DataFetcher] 未配置大V观点API，返回空数据")
        return ""
    
    async def _fetch_market_sentiment(self) -> str:
        """获取市场情绪指标"""
        if self.api_client and hasattr(self.api_client, 'get_market_sentiment'):
            return await self.api_client.get_market_sentiment()
        
        return "中性"
    
    def _format_big_v_views(self, views: List[Dict[str, Any]]) -> str:
        """格式化大V观点"""
        if not views:
            return ""
        
        lines = []
        for view in views[:5]:
            influencer = view.get("influencer", "未知")
            content = view.get("content", "")
            lines.append(f"- {influencer}: {content}")
        
        return "\n".join(lines)
    
    async def fetch_asset_details(self, symbols: List[str]) -> List[AssetDetail]:
        """
        获取标的详细数据
        
        Args:
            symbols: 标的代码列表
            
        Returns:
            AssetDetail 对象列表
        """
        logger.info(f"[DataFetcher] 获取标的详细数据: {symbols}")
        
        tasks = []
        for symbol in symbols:
            tasks.append(self._fetch_single_asset(symbol))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        assets = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"[DataFetcher] 获取标的数据失败: {result}")
                continue
            if result:
                assets.append(result)
        
        return assets
    
    async def _fetch_single_asset(self, symbol: str) -> Optional[AssetDetail]:
        """
        获取单个标的的完整数据
        
        Args:
            symbol: 标的代码
            
        Returns:
            AssetDetail 对象
        """
        try:
            logger.info(f"[DataFetcher] 获取标的 {symbol} 的数据...")
            
            # 并行获取各类数据
            name_result, market_data_result, financial_data_result, announcements_result, movements_result, articles_result, big_v_views_result = await asyncio.gather(
                self._get_symbol_name(symbol),
                self._get_market_data(symbol),
                self._get_financial_data(symbol),
                self._get_announcements(symbol),
                self._get_abnormal_movements(symbol),
                self._get_related_articles(symbol),
                self._get_specific_big_v_views(symbol),
                return_exceptions=True
            )
            
            name = name_result if not isinstance(name_result, Exception) else symbol
            market_data = market_data_result if not isinstance(market_data_result, Exception) else {}
            financial_data = financial_data_result if not isinstance(financial_data_result, Exception) else {}
            announcements = announcements_result if not isinstance(announcements_result, Exception) else []
            movements = movements_result if not isinstance(movements_result, Exception) else []
            articles = articles_result if not isinstance(articles_result, Exception) else []
            big_v_views = big_v_views_result if not isinstance(big_v_views_result, Exception) else []
            
            return AssetDetail(
                symbol=symbol,
                name=name,
                market_data=market_data,
                financial_data=financial_data,
                announcements=announcements,
                abnormal_movements=movements,
                related_articles=articles,
                specific_big_v_views=big_v_views
            )
            
        except Exception as e:
            logger.error(f"[DataFetcher] 获取标的 {symbol} 数据失败: {e}")
            return None
    
    async def _get_symbol_name(self, symbol: str) -> str:
        """获取标的名称"""
        if self.api_client and hasattr(self.api_client, 'get_symbol_name'):
            return await self.api_client.get_symbol_name(symbol)
        return symbol
    
    async def _get_market_data(self, symbol: str) -> Dict[str, Any]:
        """获取行情数据"""
        if self.api_client and hasattr(self.api_client, 'get_market_data'):
            return await self.api_client.get_market_data(symbol)
        return {}
    
    async def _get_financial_data(self, symbol: str) -> Dict[str, Any]:
        """获取财务数据"""
        if self.api_client and hasattr(self.api_client, 'get_financial_data'):
            return await self.api_client.get_financial_data(symbol)
        return {}
    
    async def _get_announcements(self, symbol: str) -> List[Dict[str, Any]]:
        """获取公告数据"""
        if self.api_client and hasattr(self.api_client, 'get_announcements'):
            return await self.api_client.get_announcements(symbol)
        return []
    
    async def _get_abnormal_movements(self, symbol: str) -> List[Dict[str, Any]]:
        """获取异动数据"""
        if self.api_client and hasattr(self.api_client, 'get_abnormal_movements'):
            return await self.api_client.get_abnormal_movements(symbol)
        return []
    
    async def _get_related_articles(self, symbol: str) -> List[Dict[str, Any]]:
        """获取相关文章"""
        if self.api_client and hasattr(self.api_client, 'get_related_articles'):
            return await self.api_client.get_related_articles(symbol)
        return []
    
    async def _get_specific_big_v_views(self, symbol: str) -> List[Dict[str, Any]]:
        """获取针对该标的的大V观点"""
        if self.api_client and hasattr(self.api_client, 'get_specific_big_v_views'):
            return await self.api_client.get_specific_big_v_views(symbol)
        return []


class UserPreferenceFetcher:
    """用户偏好获取器
    
    负责获取和格式化用户偏好数据
    """
    
    @staticmethod
    def get_user_preference(user_config: Any) -> Dict[str, Any]:
        """
        从用户配置中获取偏好数据
        
        Args:
            user_config: UserConfig 对象
            
        Returns:
            用户偏好字典
        """
        if not user_config:
            return {
                "investment_style": "价值投资",
                "risk_level": "中等",
                "focus_areas": []
            }
        
        # 从 watchlist 推断关注风格
        stocks = getattr(user_config.watchlist, 'stocks', [])
        influencers = getattr(user_config.watchlist, 'influencers', [])
        
        # 简单推断投资风格
        investment_style = "价值投资"
        if influencers:
            investment_style = "趋势跟踪"
        if len(stocks) > 5:
            investment_style = "分散投资"
        
        # 从 custom_data 获取详细偏好
        custom_data = getattr(user_config, 'custom_data', {})
        
        return {
            "investment_style": custom_data.get('investment_style', investment_style),
            "risk_level": custom_data.get('risk_level', '中等'),
            "focus_areas": custom_data.get('focus_areas', []),
            "report_length": custom_data.get('preferred_report_length', 'medium')
        }


__all__ = [
    'MarketContext',
    'AssetDetail',
    'DataFetcher',
    'UserPreferenceFetcher'
]
