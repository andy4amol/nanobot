"""
测试雪球 API 并打印详细返回数据
"""

import asyncio
import json
from nanobot.services.xueqiu_client import XueqiuRealClient


def print_json(data, title="数据", max_depth=3):
    """
格式打印 JSON 数据
    
    Args:
        data: 要打印的数据
        title: 标题
        max_depth: 最大打印深度
    """
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)
    
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    
    # 如果数据太长，只打印前 2000 字符
    if len(json_str) > 2000:
        print(json_str[:2000])
        print(f"\n... (数据已截断，完整长度: {len(json_str)} 字符)")
    else:
        print(json_str)


async def test_api_with_details():
    """
    测试 API 并打印详细数据
    """
    # 配置 Cookie
    cookie = "your_cookie_here"  # TODO: 替换为真实的 Cookie
    
    print("="*60)
    print("雪球 API 详细测试")
    print("="*60)
    
    client = XueqiuRealClient(cookie=cookie)
    
    try:
        # 测试 1: 获取特别关注用户
        print("\n" + "🔍 测试 1: 获取特别关注用户".ljust(60))
        special_follow = await client.fetch_special_follow(count=5)
        print_json(special_follow, "特别关注用户返回数据")
        
        # 测试 2: 获取热门帖子
        print("\n" + "🔍 测试 2: 获取热门帖子".ljust(60))
        hot_posts = await client.fetch_hot_posts(page=1, size=3)
        print_json(hot_posts, "热门帖子返回数据")
        
        # 测试 3: 获取热门话题
        print("\n" + "🔍 测试 3: 获取热门话题".ljust(60))
        hot_topics = await client.fetch_hot_topics(size=3)
        print_json(hot_topics, "热门话题返回数据")
        
        # 测试 4: 获取股票行情
        print("\n" + "🔍 测试 4: 获取股票行情 (SH600519)".ljust(60))
        quote = await client.fetch_stock_quote("SH600519")
        print_json(quote, "股票行情返回数据")
        
        # 测试 5: 获取股票公告
        print("\n" + "🔍 测试 5: 获取股票公告 (SH600519)".ljust(60))
        announcements = await client.fetch_stock_announcements("SH600519", count=3)
        print_json(announcements, "股票公告返回数据")
        
        # 测试 6: 获取股票讨论
        print("\n" + "🔍 测试 6: 获取股票讨论 (SH600519)".ljust(60))
        discussions = await client.fetch_symbol_discussions("SH600519", size=3)
        print_json(discussions, "股票讨论返回数据")
        
        print("\n" + "="*60)
        print("✅ 所有接口测试完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_api_with_details())
