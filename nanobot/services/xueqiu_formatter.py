"""
雪球数据格式化器

将雪球 API 返回的 JSON 数据转换为 Markdown 格式，用于动态拼接到 Prompt 中
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class XueqiuDataFormatter:
    """雪球数据格式化器"""
    
    @staticmethod
    def format_special_follow(users: List[Dict]) -> str:
        """
        格式化特别关注的用户列表
        
        Args:
            users: 从接口1获取的用户列表
            
        Returns:
            Markdown 格式的字符串
        """
        if not users:
            return "暂无特别关注的用户"
        
        lines = ["## 特别关注的用户"]
        lines.append("")
        
        for i, item in enumerate(users[:10], 1):  # 最多显示10个
            user = item.get("user", {})
            
            screen_name = user.get("screen_name", "未知用户")
            user_id = user.get("id", 0)
            followers = user.get("followers_count", 0)
            status_count = user.get("status_count", 0)
            stocks_count = user.get("stocks_count", 0)
            description = user.get("description", "暂无简介")[:100]  # 限制长度
            
            lines.append(f"### {i}. {screen_name} (ID: {user_id})")
            lines.append(f"- **简介**: {description}")
            lines.append(f"- **粉丝数**: {followers:,}")
            lines.append(f"- **发帖数**: {status_count:,}")
            lines.append(f"- **自选股数**: {stocks_count}")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_hot_posts(posts_data: Dict) -> str:
        """
        格式化热门帖子列表
        
        Args:
            posts_data: 从接口2获取的帖子数据
            
        Returns:
            Markdown 格式的字符串
        """
        posts = posts_data.get("list", [])
        
        if not posts:
            return "暂无热门帖子"
        
        lines = ["## 热门帖子"]
        lines.append("")
        
        for i, post in enumerate(posts[:10], 1):
            post_id = post.get("id", 0)
            title = post.get("title", "无标题") or post.get("description", "")[:50]
            text = XueqiuDataFormatter._clean_html(post.get("text", ""))[:200]
            created_at = XueqiuDataFormatter._format_timestamp(post.get("created_at"))
            retweet_count = post.get("retweet_count", 0)
            reply_count = post.get("reply_count", 0)
            like_count = post.get("like_count", 0)
            
            user = post.get("user", {})
            author = user.get("screen_name", "未知作者")
            
            # 关联股票
            card = post.get("card", {})
            related_stock = card.get("param", "") if card else ""
            
            lines.append(f"### {i}. {title}")
            lines.append(f"**作者**: {author} | **时间**: {created_at}")
            if related_stock:
                lines.append(f"**关联股票**: {related_stock}")
            lines.append(f"**互动**: 转发 {retweet_count} | 回复 {reply_count} | 点赞 {like_count}")
            lines.append(f"**内容**: {text}...")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_hot_topics(topics_data: Dict) -> str:
        """
        格式化热门话题
        
        Args:
            topics_data: 从接口3获取的话题数据
            
        Returns:
            Markdown 格式的字符串
        """
        topics = topics_data.get("data", [])
        
        if not topics:
            return "暂无热门话题"
        
        lines = ["## 热门话题"]
        lines.append("")
        
        for i, topic in enumerate(topics[:10], 1):
            title = topic.get("show_title", "未知话题")
            full_title = topic.get("title", "")
            stocks = topic.get("stocks", [])
            
            lines.append(f"### {i}. {title}")
            lines.append(f"**话题标签**: {full_title}")
            
            if stocks:
                lines.append("**相关股票**:")
                for stock in stocks[:5]:  # 最多显示5个
                    name = stock.get("name", "")
                    code = stock.get("code", "")
                    current = stock.get("current", "")
                    percentage = stock.get("percentage", 0)
                    
                    # 计算涨跌幅显示
                    change_str = f"+{percentage:.2f}%" if percentage > 0 else f"{percentage:.2f}%"
                    emoji = "📈" if percentage > 0 else "📉" if percentage < 0 else "➡️"
                    
                    lines.append(f"- {emoji} {name} ({code}): {current} | {change_str}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_stock_quote(quote_data: Dict) -> str:
        """
        格式化个股行情
        
        Args:
            quote_data: 从接口4获取的行情数据
            
        Returns:
            Markdown 格式的字符串
        """
        quote = quote_data.get("data", {}).get("quote", {})
        
        if not quote:
            return "暂无行情数据"
        
        symbol = quote.get("symbol", "")
        name = quote.get("name", "")
        current = quote.get("current", 0)
        chg = quote.get("chg", 0)
        percent = quote.get("percent", 0)
        high = quote.get("high", 0)
        low = quote.get("low", 0)
        open_price = quote.get("open", 0)
        last_close = quote.get("last_close", 0)
        volume = quote.get("volume", 0)
        amount = quote.get("amount", 0)
        pe_ttm = quote.get("pe_ttm", 0)
        pb = quote.get("pb", 0)
        market_cap = quote.get("market_capital", 0)
        high52w = quote.get("high52w", 0)
        low52w = quote.get("low52w", 0)
        
        lines = [f"## {name} ({symbol}) 行情"]
        lines.append("")
        
        # 核心行情
        change_str = f"+{chg:.2f}" if chg > 0 else f"{chg:.2f}"
        percent_str = f"+{percent:.2f}%" if percent > 0 else f"{percent:.2f}%"
        emoji = "📈" if percent > 0 else "📉" if percent < 0 else "➡️"
        
        lines.append(f"### 核心行情 {emoji}")
        lines.append(f"- **当前价**: {current} | **涨跌额**: {change_str} | **涨跌幅**: {percent_str}")
        lines.append(f"- **今开**: {open_price} | **昨收**: {last_close}")
        lines.append(f"- **最高**: {high} | **最低**: {low}")
        lines.append("")
        
        # 成交数据
        lines.append("### 成交数据")
        lines.append(f"- **成交量**: {volume:,} 股")
        lines.append(f"- **成交额**: {amount/1e8:.2f} 亿")
        lines.append("")
        
        # 估值指标
        lines.append("### 估值指标")
        lines.append(f"- **市盈率(TTM)**: {pe_ttm:.2f}")
        lines.append(f"- **市净率**: {pb:.2f}")
        lines.append(f"- **总市值**: {market_cap/1e8:.2f} 亿")
        lines.append("")
        
        # 52周区间
        lines.append("### 52周区间")
        lines.append(f"- **52周高**: {high52w} | **52周低**: {low52w}")
        lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_stock_announcements(announcements_data: Dict) -> str:
        """
        格式化股票公告
        
        Args:
            announcements_data: 从接口5获取的公告数据
            
        Returns:
            Markdown 格式的字符串
        """
        announcements = announcements_data.get("list", [])
        
        if not announcements:
            return "暂无公告"
        
        lines = ["## 最新公告"]
        lines.append("")
        
        for i, ann in enumerate(announcements[:5], 1):  # 最多显示5条
            title = ann.get("title", "无标题")
            description = ann.get("description", "")
            created_at = XueqiuDataFormatter._format_timestamp(ann.get("created_at"))
            
            # AI 摘要
            ai_summary = ""
            extend_home = ann.get("extend_st_home_page", {})
            if extend_home:
                ai_card = extend_home.get("ai_card", {})
                ai_summary = ai_card.get("core_text_summary", "")
            
            lines.append(f"### {i}. {title}")
            lines.append(f"**发布时间**: {created_at}")
            lines.append(f"**摘要**: {description[:150]}...")
            
            if ai_summary:
                lines.append(f"**AI 解读**: {ai_summary}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_symbol_discussions(discussions_data: Dict) -> str:
        """
        格式化关注用户的标的讨论
        
        Args:
            discussions_data: 从接口6获取的讨论数据
            
        Returns:
            Markdown 格式的字符串
        """
        data_list = discussions_data.get("data", [])
        
        if not data_list:
            return "暂无讨论"
        
        lines = ["## 关注用户的讨论"]
        lines.append("")
        
        for group in data_list:
            group_name = group.get("name", "")
            posts = group.get("list", [])
            
            lines.append(f"### {group_name}")
            lines.append("")
            
            for i, post in enumerate(posts[:5], 1):  # 每组最多显示5条
                user = post.get("user", {})
                author = user.get("screen_name", "未知")
                text = XueqiuDataFormatter._clean_html(post.get("text", ""))[:150]
                created_at = XueqiuDataFormatter._format_timestamp(post.get("created_at"))
                like_count = post.get("like_count", 0)
                
                lines.append(f"**{i}. {author} - {created_at}**")
                lines.append(f"{text}...")
                
                # 精彩评论
                comments = post.get("excellent_comments", [])
                if comments:
                    lines.append(f"   💬 精彩评论 ({len(comments)}条)")
                
                lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_complete_market_context(
        hot_topics: Dict = None,
        hot_posts: Dict = None,
        special_follow: List = None
    ) -> str:
        """
        格式化完整的市场上下文
        
        Args:
            hot_topics: 热门话题数据
            hot_posts: 热门帖子数据
            special_follow: 特别关注用户数据
            
        Returns:
            完整的 Markdown 格式市场上下文
        """
        lines = ["# 市场全景"]
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        if hot_topics:
            lines.append(XueqiuDataFormatter.format_hot_topics(hot_topics))
            lines.append("---")
            lines.append("")
        
        if hot_posts:
            lines.append(XueqiuDataFormatter.format_hot_posts(hot_posts))
            lines.append("---")
            lines.append("")
        
        if special_follow:
            lines.append(XueqiuDataFormatter.format_special_follow(special_follow))
        
        return "\n".join(lines)
    
    @staticmethod
    def format_complete_stock_analysis(
        symbol: str,
        quote_data: Dict = None,
        announcements: Dict = None,
        discussions: Dict = None
    ) -> str:
        """
        格式化完整的标的分析
        
        Args:
            symbol: 股票代码
            quote_data: 行情数据
            announcements: 公告数据
            discussions: 讨论数据
            
        Returns:
            完整的 Markdown 格式标的分析
        """
        lines = [f"# {symbol} 深度分析"]
        lines.append("")
        lines.append(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        if quote_data:
            lines.append(XueqiuDataFormatter.format_stock_quote(quote_data))
            lines.append("---")
            lines.append("")
        
        if announcements:
            lines.append(XueqiuDataFormatter.format_stock_announcements(announcements))
            lines.append("---")
            lines.append("")
        
        if discussions:
            lines.append(XueqiuDataFormatter.format_symbol_discussions(discussions))
        
        return "\n".join(lines)
    
    # ============== 辅助方法 ==============
    
    @staticmethod
    def _clean_html(text: str) -> str:
        """清理 HTML 标签，提取纯文本"""
        if not text:
            return ""
        
        # 简单的 HTML 标签清理（可以使用 BeautifulSoup 做更精确的清理）
        import re
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def _format_timestamp(timestamp: int) -> str:
        """格式化时间戳"""
        if not timestamp:
            return "未知时间"
        
        try:
            # 雪球时间戳是毫秒级
            dt = datetime.fromtimestamp(timestamp / 1000)
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            return "未知时间"


class PromptBuilder:
    """
    动态 Prompt 构建器
    
    将格式化后的 Markdown 数据拼接到 Prompt 模板中
    """
    
    @staticmethod
    def build_daily_report_prompt(
        base_template: str,
        market_context: str = None,
        stock_analysis: str = None,
        user_preference: str = None
    ) -> str:
        """
        构建日报 Prompt
        
        Args:
            base_template: 基础模板字符串
            market_context: 市场上下文 Markdown
            stock_analysis: 标的分析 Markdown
            user_preference: 用户偏好信息
            
        Returns:
            完整的 Prompt
        """
        prompt = base_template
        
        # 替换占位符
        if market_context:
            prompt = prompt.replace("{{market_context}}", market_context)
        
        if stock_analysis:
            prompt = prompt.replace("{{stock_analysis}}", stock_analysis)
        
        if user_preference:
            prompt = prompt.replace("{{user_preference}}", user_preference)
        
        # 清理未替换的占位符
        prompt = prompt.replace("{{market_context}}", "暂无市场数据")
        prompt = prompt.replace("{{stock_analysis}}", "暂无标的分析")
        prompt = prompt.replace("{{user_preference}}", "暂无用户偏好")
        
        return prompt
    
    @staticmethod
    def build_analysis_prompt(
        symbol: str,
        quote_data: Dict,
        announcements: Dict = None,
        discussions: Dict = None,
        additional_context: str = ""
    ) -> str:
        """
        构建单只股票的分析 Prompt
        
        Args:
            symbol: 股票代码
            quote_data: 行情数据
            announcements: 公告数据（可选）
            discussions: 讨论数据（可选）
            additional_context: 额外上下文
            
        Returns:
            完整的分析 Prompt
        """
        formatter = XueqiuDataFormatter
        
        lines = [
            "# 单只股票深度分析",
            "",
            f"请基于以下数据，对 {symbol} 进行深度分析：",
            "",
            "## 1. 行情数据",
            formatter.format_stock_quote(quote_data),
            ""
        ]
        
        if announcements:
            lines.append("## 2. 最新公告")
            lines.append(formatter.format_stock_announcements(announcements))
            lines.append("")
        
        if discussions:
            lines.append("## 3. 用户讨论")
            lines.append(formatter.format_symbol_discussions(discussions))
            lines.append("")
        
        if additional_context:
            lines.append("## 4. 额外信息")
            lines.append(additional_context)
            lines.append("")
        
        lines.extend([
            "## 分析要求",
            "1. 综合行情、公告、讨论等多维度信息",
            "2. 给出当前股价走势判断",
            "3. 分析公告对股价的影响",
            "4. 总结市场情绪和用户观点",
            "5. 给出投资风险提示",
            "",
            "**开始分析：**"
        ])
        
        return "\n".join(lines)


# 使用示例
if __name__ == "__main__":
    # 示例数据
    formatter = XueqiuDataFormatter()
    
    # 测试格式化行情数据
    sample_quote = {
        "data": {
            "quote": {
                "symbol": "09988",
                "name": "阿里巴巴-W",
                "current": 160.6,
                "chg": 2.7,
                "percent": 1.71,
                "high": 162.6,
                "low": 158.7,
                "open": 159.7,
                "last_close": 157.9,
                "volume": 40701461,
                "amount": 6.5476e9,
                "pe_ttm": 22.98,
                "pb": 2.65,
                "market_capital": 3.067e12,
                "high52w": 186.2,
                "low52w": 94.95
            }
        }
    }
    
    print("=== 格式化行情数据 ===")
    print(formatter.format_stock_quote(sample_quote))
    print("\n" + "="*60 + "\n")
    
    # 测试构建分析 Prompt
    prompt = PromptBuilder.build_analysis_prompt("09988", sample_quote)
    print("=== 构建分析 Prompt ===")
    print(prompt)
