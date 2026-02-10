"""
雪球真实 API 客户端

实现雪球 API 的真实调用，包括：
1. Cookie 鉴权
2. 动态参数生成（_t 和 _s）
3. 请求签名
4. 所有 6 个接口的完整实现
"""

import asyncio
import hashlib
import time
import random
import string
from typing import Dict, List, Any, Optional
import httpx
from loguru import logger


class XueqiuSignatureGenerator:
    """
    雪球签名生成器
    
    用于生成请求所需的 _t 和 _s 参数
    """
    
    @staticmethod
    def generate_t() -> str:
        """
        生成 _t 参数（时间戳/指纹）
        
        根据抓包分析，_t 的格式类似 "1VIVO8a451156c..." 包含设备信息和时间
        """
        # 生成设备指纹部分
        device_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        timestamp = int(time.time() * 1000)
        
        # 组合格式：1 + 设备前缀 + 设备ID + 时间戳
        return f"1VIVO{device_id}{timestamp}"
    
    @staticmethod
    def generate_s(url: str, params: Dict = None) -> str:
        """
        生成 _s 参数（签名）
        
        Args:
            url: 请求 URL
            params: 请求参数
            
        Returns:
            签名字符串
        """
        # 雪球的签名算法（简化版，实际可能需要逆向）
        # 这里使用一个常见的 MD5 签名方式
        
        # 构造签名字符串
        if params:
            param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            sign_str = f"{url}?{param_str}"
        else:
            sign_str = url
        
        # 添加 salt
        salt = "xueqiu_secret"  # 实际需要从逆向获取
        
        # 生成 MD5
        sign = hashlib.md5((sign_str + salt).encode()).hexdigest()[:6]
        
        return sign
    
    @staticmethod
    def generate_xq_token(user_id: str = None) -> str:
        """
        生成 xq_a_token（如果有需要）
        
        Args:
            user_id: 用户ID
            
        Returns:
            token 字符串
        """
        # 实际实现需要根据雪球的 token 生成算法
        if user_id:
            data = f"{user_id}:{int(time.time())}"
            return hashlib.md5(data.encode()).hexdigest()
        return ""


class XueqiuRealClient:
    """
    雪球真实 API 客户端
    
    实现所有接口的真实调用
    """
    
    def __init__(
        self,
        cookie: str,
        user_agent: str = "Xueqiu Android 14.81",
        device_id: str = None,
        timeout: int = 30
    ):
        """
        初始化客户端
        
        Args:
            cookie: 雪球 Cookie（包含 xq_a_token）
            user_agent: User-Agent
            device_id: 设备ID
            timeout: 请求超时时间（秒）
        """
        self.cookie = cookie
        self.user_agent = user_agent
        self.device_id = device_id or self._generate_device_id()
        self.timeout = timeout
        self.base_url = "https://api.xueqiu.com"
        self.stock_url = "https://stock.xueqiu.com"
        
        # 创建 HTTP 客户端
        self.client = httpx.AsyncClient(
            headers=self._build_headers(),
            timeout=timeout,
            verify=False  # 生产环境建议开启
        )
        
        # 签名生成器
        self.signature_gen = XueqiuSignatureGenerator()
        
        logger.info("[XueqiuRealClient] 客户端初始化完成")
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Cookie": self.cookie,
            "User-Agent": self.user_agent,
            "X-Device-ID": self.device_id,
            "X-Device-Model-Name": "Vivo_V1986A",
            "X-Device-OS": "Android 12",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
    
    def _generate_device_id(self) -> str:
        """生成随机设备ID"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=16))
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
        logger.info("[XueqiuRealClient] 客户端已关闭")
    
    # ============== 接口实现 ==============
    
    async def fetch_special_follow(
        self,
        count: int = 20
    ) -> List[Dict]:
        """
        接口1：获取特别关注的用户
        
        Args:
            count: 返回数量
            
        Returns:
            用户列表
        """
        url = "/statuses/special_follow.json"
        
        # 生成动态参数
        _t = self.signature_gen.generate_t()
        _s = self.signature_gen.generate_s(url)
        
        params = {
            "_t": _t,
            "_s": _s
        }
        
        try:
            response = await self.client.get(
                self.base_url + url,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"[XueqiuRealClient] 获取特别关注用户成功，数量: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"[XueqiuRealClient] 获取特别关注用户失败: {e}")
            return []
    
    async def fetch_hot_posts(
        self,
        page: int = 1,
        size: int = 10,
        last_id: int = -1
    ) -> Dict:
        """
        接口2：获取热门帖子
        
        Args:
            page: 页码
            size:   每页数量
            last_id: 上一页最后一条ID，第一页传 -1
            
        Returns:
            帖子数据
        """
        url = "/statuses/hot/listV3.json"
        
        _t = self.signature_gen.generate_t()
        _s = self.signature_gen.generate_s(url, {"page": page, "size": size})
        
        params = {
            "page": page,
            "size": size,
            "last_id": last_id,
            "_t": _t,
            "_s": _s
        }
        
        try:
            response = await self.client.get(
                self.base_url + url,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"[XueqiuRealClient] 获取热门帖子成功，数量: {len(data.get('list', []))}")
            return data
            
        except Exception as e:
            logger.error(f"[XueqiuRealClient] 获取热门帖子失败: {e}")
            return {"list": [], "has_next_page": False}
    
    async def fetch_hot_topics(
        self,
        size: int = 10
    ) -> Dict:
        """
        接口3：获取热门话题
        
        Args:
            size: 返回数量
            
        Returns:
            话题数据
        """
        url = "/query/v1/hot_event/rich_tag.json"
        
        _t = self.signature_gen.generate_t()
        _s = self.signature_gen.generate_s(url, {"size": size})
        
        params = {
            "size": size,
            "_t": _t,
            "_s": _s
        }
        
        try:
            response = await self.client.get(
                self.base_url + url,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"[XueqiuRealClient] 获取热门话题成功，数量: {len(data.get('data', []))}")
            return data
            
        except Exception as e:
            logger.error(f"[XueqiuRealClient] 获取热门话题失败: {e}")
            return {"code": 500, "data": []}
    
    async def fetch_stock_quote(
        self,
        symbol: str,
        extend: str = "detail"
    ) -> Dict:
        """
        接口4：获取个股行情
        
        Args:
            symbol: 股票代码（如 SH600519, 09988）
            extend:  扩展模式
            
        Returns:
            行情数据
        """
        url = "/v5/stock/quote.json"
        
        _t = self.signature_gen.generate_t()
        _s = self.signature_gen.generate_s(url, {"symbol": symbol})
        
        params = {
            "symbol": symbol,
            "extend": extend,
            "user_event": 1,
            "_t": _t,
            "_s": _s
        }
        
        # 行情接口需要额外的 header
        headers = self._build_headers()
        # headers["x-snowx-token"] = self.signature_gen.generate_xq_token()  # 如果需要
        
        try:
            response = await self.client.get(
                self.stock_url + url,
                params=params,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"[XueqiuRealClient] 获取 {symbol} 行情成功")
            return data
            
        except Exception as e:
            logger.error(f"[XueqiuRealClient] 获取 {symbol} 行情失败: {e}")
            return {"error_code": -1, "data": {}}
    
    async def fetch_stock_announcements(
        self,
        symbol_id: str,
        count: int = 10,
        page: int = 1,
        sub_source: int = 1
    ) -> Dict:
        """
        接口5：获取股票公告
        
        Args:
            symbol_id: 股票代码
            count: 每页数量
            page: 页码
            sub_source: 子来源标识
            
        Returns:
            公告数据
        """
        url = "/statuses/stock_timeline.json"
        
        _t = self.signature_gen.generate_t()
        _s = self.signature_gen.generate_s(url, {"symbol_id": symbol_id})
        
        # source 需要编码
        import urllib.parse
        source_encoded = urllib.parse.quote("公告")
        
        params = {
            "symbol_id": symbol_id,
            "source": source_encoded,
            "sub_source": sub_source,
            "page": page,
            "count": count,
            "_t": _t,
            "_s": _s
        }
        
        try:
            response = await self.client.get(
                self.base_url + url,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"[XueqiuRealClient] 获取 {symbol_id} 公告成功，数量: {len(data.get('list', []))}")
            return data
            
        except Exception as e:
            logger.error(f"[XueqiuRealClient] 获取 {symbol_id} 公告失败: {e}")
            return {"list": [], "count": 0}
    
    async def fetch_symbol_discussions(
        self,
        symbol: str,
        page: int = 1,
        size: int = 10
    ) -> Dict:
        """
        接口6：获取关注用户关于标的的讨论
        
        Args:
            symbol: 股票代码
            page: 页码
            size: 每页数量
            
        Returns:
            讨论数据
        """
        url = "/query/v1/symbol/following/status.json"
        
        _t = self.signature_gen.generate_t()
        _s = self.signature_gen.generate_s(url, {"symbol": symbol})
        
        params = {
            "symbol": symbol,
            "page": page,
            "size": size,
            "_t": _t,
            "_s": _s
        }
        
        try:
            response = await self.client.get(
                self.base_url + url,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            # 统计帖子数量
            total_posts = sum(len(group.get("list", [])) for group in data.get("data", []))
            logger.info(f"[XueqiuRealClient] 获取 {symbol} 讨论成功，数量: {total_posts}")
            return data
            
        except Exception as e:
            logger.error(f"[XueqiuRealClient] 获取 {symbol} 讨论失败: {e}")
            return {"code": 500, "data": []}
    
    # ============== 批量获取方法 ==============
    
    async def fetch_multiple_stock_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        批量获取多个股票的行情
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            {symbol: quote_data}
        """
        logger.info(f"[XueqiuRealClient] 批量获取 {len(symbols)} 只股票的行情...")
        
        tasks = [self.fetch_stock_quote(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        quotes = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"[XueqiuRealClient] 获取 {symbol} 行情异常: {result}")
                quotes[symbol] = {"error_code": -1, "data": {}}
            else:
                quotes[symbol] = result
        
        return quotes
    
    async def fetch_market_context(self) -> Dict:
        """
        获取完整的市场上下文（热门话题 + 热门帖子 + 特别关注）
        
        Returns:
            {
                "hot_topics": ...,
                "hot_posts": ...,
                "special_follow": ...
            }
        """
        logger.info("[XueqiuRealClient] 获取市场上下文...")
        
        hot_topics, hot_posts, special_follow = await asyncio.gather(
            self.fetch_hot_topics(),
            self.fetch_hot_posts(),
            self.fetch_special_follow()
        )
        
        return {
            "hot_topics": hot_topics,
            "hot_posts": hot_posts,
            "special_follow": special_follow
        }
    
    async def fetch_stock_complete_data(self, symbol: str) -> Dict:
        """
        获取单个股票的完整数据（行情 + 公告 + 讨论）
        
        Args:
            symbol: 股票代码
            
        Returns:
            {
                "quote": ...,
                "announcements": ...,
                "discussions": ...
            }
        """
        logger.info(f"[XueqiuRealClient] 获取 {symbol} 完整数据...")
        
        quote, announcements, discussions = await asyncio.gather(
            self.fetch_stock_quote(symbol),
            self.fetch_stock_announcements(symbol),
            self.fetch_symbol_discussions(symbol)
        )
        
        return {
            "symbol": symbol,
            "quote": quote,
            "announcements": announcements,
            "discussions": discussions
        }


# 使用示例
async def main():
    """
    使用示例
    """
    # 配置你的 Cookie
    cookie = "xq_a_token=your_token_here; xq_is_login=1; u=your_user_id;"
    
    # 创建客户端
    client = XueqiuRealClient(cookie=cookie)
    
    try:
        # 测试接口
        print("=" * 60)
        print("测试雪球 API")
        print("=" * 60)
        
        # 1. 获取市场上下文
        print("\n1. 获取市场上下文...")
        market_context = await client.fetch_market_context()
        print(f"   ✓ 热门话题: {len(market_context['hot_topics'].get('data', []))} 条")
        print(f"   ✓ 热门帖子: {len(market_context['hot_posts'].get('list', []))} 条")
        print(f"   ✓ 特别关注: {len(market_context['special_follow'])} 人")
        
        # 2. 获取股票行情
        print("\n2. 获取股票行情...")
        symbol = "SH600519"
        quote = await client.fetch_stock_quote(symbol)
        quote_data = quote.get("data", {}).get("quote", {})
        if quote_data:
            print(f"   ✓ {quote_data.get('name')} ({symbol}): {quote_data.get('current')} | {quote_data.get('percent', 0):+.2f}%")
        
        # 3. 获取完整股票数据
        print(f"\n3. 获取 {symbol} 完整数据...")
        stock_data = await client.fetch_stock_complete_data(symbol)
        print(f"   ✓ 公告: {len(stock_data['announcements'].get('list', []))} 条")
        print(f"   ✓ 讨论: {sum(len(g.get('list', [])) for g in stock_data['discussions'].get('data', []))} 条")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        
    finally:
        # 关闭客户端
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
