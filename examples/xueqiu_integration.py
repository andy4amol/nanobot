"""
雪球数据集成示例

展示如何调用雪球 API 获取数据，并格式化为 Markdown 拽数接到 Prompt 中
"""

import asyncio
import json
from typing import Dict, List, Any

from nanobot.services.xueqiu_formatter import XueqiuDataFormatter, PromptBuilder


class XueqiuAPIClient:
    """
    雪球 API 客户端（简化版）
    
    实际使用时需要：
    1. 实现 Cookie 鉴权
    2. 处理动态参数 _t 和 _s
    3. 添加请求重试和错误处理
    """
    
    def __init__(self, cookie: str = None):
        self.cookie = cookie
        self.base_headers = {
            "User-Agent": "Xueqiu Android 14.81",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        if cookie:
            self.base_headers["Cookie"] = cookie
    
    async def fetch_special_follow(self) -> List[Dict]:
        """
        获取特别关注的用户（接口1）
        
        URL: https://api.xueqiu.com/statuses/special_follow.json
        """
        # 模拟返回数据
        return [
            {
                "is_read": True,
                "user": {
                    "id": 1955602780,
                    "screen_name": "不明真相的群众",
                    "description": "主业：陪聊，副业：投资",
                    "followers_count": 649129,
                    "friends_count": 13525,
                    "status_count": 93858,
                    "stocks_count": 519
                }
            }
        ]
    
    async def fetch_hot_posts(self, page: int = 1, size: int = 10) -> Dict:
        """
        获取热门帖子（接口2）
        
        URL: https://api.xueqiu.com/statuses/hot/listV3.json
        """
        return {
            "has_next_page": True,
            "list": [
                {
                    "id": 375583120,
                    "user_id": 1638377010,
                    "title": "今日市场观察",
                    "text": "<p>今日A股市场整体表现强劲...</p>",
                    "description": "今日A股市场整体表现强劲，新能源板块领涨",
                    "created_at": 1770679672000,
                    "retweet_count": 6,
                    "reply_count": 63,
                    "fav_count": 31,
                    "like_count": 197,
                    "user": {
                        "id": 1638377010,
                        "screen_name": "投资达人"
                    },
                    "card": {
                        "type": "new_stock",
                        "param": "SH600519"
                    }
                }
            ]
        }
    
    async def fetch_hot_topics(self, size: int = 10) -> Dict:
        """
        获取热门话题（接口3）
        
        URL: https://api.xueqiu.com/query/v1/hot_event/rich_tag.json
        """
        return {
            "code": 200,
            "message": "success",
            "success": True,
            "data": [
                {
                    "id": 456372,
                    "show_title": "春节行情预判",
                    "title": "#春节行情预判#",
                    "stocks": [
                        {
                            "name": "上证指数",
                            "code": "SH000001",
                            "current": "4129.43",
                            "percentage": 0.15
                        },
                        {
                            "name": "贵州茅台",
                            "code": "SH600519",
                            "current": "1850.00",
                            "percentage": 1.2
                        }
                    ]
                }
            ]
        }
    
    async def fetch_stock_quote(self, symbol: str) -> Dict:
        """
        获取个股行情（接口4）
        
        URL: https://stock.xueqiu.com/v5/stock/quote.json
        """
        return {
            "error_code": 0,
            "data": {
                "quote": {
                    "symbol": "SH600519",
                    "code": "600519",
                    "name": "贵州茅台",
                    "current": 1850.00,
                    "chg": 15.00,
                    "percent": 0.82,
                    "high": 1860.00,
                    "low": 1830.00,
                    "open": 1840.00,
                    "last_close": 1835.00,
                    "volume": 4070146,
                    "amount": 7.5e9,
                    "pe_ttm": 35.5,
                    "pb": 12.3,
                    "market_capital": 2.3e12,
                    "high52w": 2100.00,
                    "low52w": 1500.00
                }
            }
        }
    
    async def fetch_stock_announcements(self, symbol: str, count: int = 10) -> Dict:
        """
        获取股票公告（接口5）
        
        URL: https://api.xueqiu.com/statuses/stock_timeline.json
        """
        return {
            "count": 1,
            "page": 1,
            "list": [
                {
                    "id": 374878982,
                    "symbol_id": symbol,
                    "title": "贵州茅台关于重大事项的公告",
                    "description": "公司拟投资XX项目，预计总投资额XX亿元",
                    "created_at": 1770201602000,
                    "source": "公告",
                    "extend_st_home_page": {
                        "ai_card": {
                            "core_text_summary": "公司公告显示将加大在新业务领域的投入，短期内可能影响现金流，但长期有利于业务多元化"
                        }
                    }
                }
            ]
        }
    
    async def fetch_symbol_discussions(self, symbol: str, page: int = 1, size: int = 10) -> Dict:
        """
        获取关注用户关于标的的讨论（接口6）
        
        URL: https://api.xueqiu.com/query/v1/symbol/following/status.json
        """
        return {
            "code": 200,
            "success": True,
            "message": "success",
            "data": [
                {
                    "name": "讨论",
                    "list": [
                        {
                            "id": 375483578,
                            "title": "茅台今日走势分析",
                            "text": "<p>茅台今日表现稳健，符合预期...</p>",
                            "user": {
                                "id": 123456,
                                "screen_name": "价值投资派"
                            },
                            "created_at": 1770613267000,
                            "like_count": 25,
                            "excellent_comments": [
                                {
                                    "id": 396367317,
                                    "text": "分析很到位，支持持有",
                                    "user": {
                                        "screen_name": "稳健投资者"
                                    },
                                    "likeCount": 6
                                }
                            ]
                        }
                    ]
                }
            ]
        }


async def generate_daily_report_prompt(symbol: str = "SH600519"):
    """
    生成完整的日报 Prompt
    
    Args:
        symbol: 需要分析的股票代码
    """
    print("=" * 60)
    print("开始生成日报 Prompt")
    print("=" * 60)
    
    # 1. 创建 API 客户端
    api_client = XueqiuAPIClient(cookie="your_cookie_here")
    
    # 2. 创建格式化器
    formatter = XueqiuDataFormatter()
    
    # 3. 并行获取市场数据
    print("\n1. 获取市场数据...")
    hot_topics, hot_posts, special_follow = await asyncio.gather(
        api_client.fetch_hot_topics(),
        api_client.fetch_hot_posts(),
        api_client.fetch_special_follow()
    )
    print("   ✓ 市场数据获取完成")
    
    # 4. 获取标的详细数据
    print(f"\n2. 获取 {symbol} 数据...")
    quote, announcements, discussions = await asyncio.gather(
        api_client.fetch_stock_quote(symbol),
        api_client.fetch_stock_announcements(symbol),
        api_client.fetch_symbol_discussions(symbol)
    )
    print(f"   ✓ {symbol} 数据获取完成")
    
    # 5. 格式化市场上下文
    print("\n3. 格式化市场上下文...")
    market_context_md = formatter.format_complete_market_context(
        hot_topics=hot_topics,
        hot_posts=hot_posts,
        special_follow=special_follow
    )
    print("   ✓ 市场上下文格式化完成")
    
    # 6. 格式化标的分析
    print(f"\n4. 格式化 {symbol} 分析...")
    stock_analysis_md = formatter.format_complete_stock_analysis(
        symbol=symbol,
        quote_data=quote,
        announcements=announcements,
        discussions=discussions
    )
    print(f"   ✓ {symbol} 分析格式化完成")
    
    # 7. 构建完整 Prompt
    print("\n5. 构建完整 Prompt...")
    base_template = """# 投资日报生成任务

## Role
你是一位资深的金融投资顾问，擅长数据驱动的投资分析。

## Goal
根据提供的【市场全景】和【标的深度分析】，撰写一份逻辑严密、数据准确的投资日报。

## 市场全景
{{market_context}}

## 标的深度分析
{{stock_analysis}}

## 分析要求
1. 结合市场热门话题和用户关注，给出宏观判断
2. 基于标的行情、公告、讨论，给出具体分析
3. 总结投资机会和风险
4. 给出操作建议（谨慎/观望/积极）

**开始生成：**"""
    
    full_prompt = PromptBuilder.build_daily_report_prompt(
        base_template=base_template,
        market_context=market_context_md,
        stock_analysis=stock_analysis_md,
        user_preference="风险偏好：中等 | 投资风格：价值投资"
    )
    print("   ✓ Prompt 构建完成")
    
    # 8. 输出结果
    print("\n" + "=" * 60)
    print("生成的 Prompt 预览（前500字符）:")
    print("=" * 60)
    print(full_prompt[:500])
    print("...")
    
    print("\n" + "=" * 60)
    print("完整 Prompt 长度:", len(full_prompt), "字符")
    print("=" * 60)
    
    return full_prompt


async def generate_stock_analysis_prompt(symbol: str):
    """
    生成单只股票的分析 Prompt（简化版）
    """
    print("=" * 60)
    print(f"生成 {symbol} 分析 Prompt")
    print("=" * 60)
    
    api_client = XueqiuAPIClient()
    formatter = XueqiuDataFormatter()
    
    # 获取数据
    quote, announcements, discussions = await asyncio.gather(
        api_client.fetch_stock_quote(symbol),
        api_client.fetch_stock_announcements(symbol),
        api_client.fetch_symbol_discussions(symbol)
    )
    
    # 构建分析 Prompt
    prompt = PromptBuilder.build_analysis_prompt(
        symbol=symbol,
        quote_data=quote,
        announcements=announcements,
        discussions=discussions
    )
    
    print("\n" + "=" * 60)
    print("分析 Prompt 预览:")
    print("=" * 60)
    print(prompt[:800])
    print("...")
    
    return prompt


# 主程序
async def main():
    """
    主程序入口
    """
    import sys
    
    # 默认股票代码
    symbol = "SH600519"
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if len(sys.argv) > 2:
            symbol = sys.argv[2]
    else:
        mode = "daily"
    
    if mode == "daily":
        # 生成日报 Prompt
        await generate_daily_report_prompt(symbol)
    elif mode == "stock":
        # 生成单只股票分析 Prompt
        await generate_stock_analysis_prompt(symbol)
    else:
        print("使用方法:")
        print("  python xueqiu_integration.py daily [股票代码]  # 生成日报 Prompt")
        print("  python xueqiu_integration.py stock [股票代码]  # 生成股票分析 Prompt")


if __name__ == "__main__":
    asyncio.run(main())
