"""
使用真实雪球 API 生成报告 Prompt

集成真实 API 调用、数据格式化和 Prompt 构建
"""

import asyncio
import os
from typing import Dict, List

from nanobot.services.xueqiu_client import XueqiuRealClient
from nanobot.services.xueqiu_formatter import XueqiuDataFormatter, PromptBuilder


async def generate_report_with_real_api(
    symbol: str,
    cookie: str,
    report_type: str = "daily"
) -> str:
    """
    使用真实雪球 API 生成报告 Prompt
    
    Args:
        symbol: 股票代码
        cookie: 雪球 Cookie
        report_type: 报告类型 (daily/stock)
        
    Returns:
        完整的 Prompt
    """
    print("=" * 60)
    print(f"使用真实 API 生成 {report_type} 报告 Prompt")
    print("=" * 60)
    
    # 1. 创建真实 API 客户端
    print(f"\n1. 初始化雪球 API 客户端...")
    client = XueqiuRealClient(cookie=cookie)
    print("   ✓ 客户端初始化完成")
    
    # 2. 创建格式化器
    formatter = XueqiuDataFormatter()
    
    try:
        if report_type == "daily":
            # 日报模式：获取市场上下文 + 标的详细数据
            print(f"\n2. 获取市场上下文...")
            market_context_data = await client.fetch_market_context()
            print("   ✓ 市场上下文获取完成")
            
            print(f"\n3. 获取 {symbol} 详细数据...")
            stock_data = await client.fetch_stock_complete_data(symbol)
            print(f"   ✓ {symbol} 数据获取完成")
            
            # 4. 格式化数据
            print(f"\n4. 格式化数据为 Markdown...")
            market_context_md = formatter.format_complete_market_context(
                hot_topics=market_context_data.get("hot_topics"),
                hot_posts=market_context_data.get("hot_posts"),
                special_follow=market_context_data.get("special_follow")
            )
            
            stock_analysis_md = formatter.format_complete_stock_analysis(
                symbol=symbol,
                quote_data=stock_data.get("quote"),
                announcements=stock_data.get("announcements"),
                discussions=stock_data.get("discussions")
            )
            print("   ✓ 数据格式化完成")
            
            # 5. 构建完整 Prompt
            print(f"\n5. 构建完整 Prompt...")
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
2. 基于标的行情、公告、讨论，给出具体给出分析
3. 总结投资机会和风险
4. 给出操作建议（谨慎/观望/积极）

**开始生成：**"""
            
            full_prompt = PromptBuilder.build_daily_report_prompt(
                base_template=base_template,
                market_context=market_context_md,
                stock_analysis=stock_analysis_md,
                user_preference="风险偏好：中等 | 投资风格：价值投资"
            )
            
        elif report_type == "stock":
            # 单股分析模式
            print(f"\n2. 获取 {symbol} 完整数据...")
            stock_data = await client.fetch_stock_complete_data(symbol)
            print(f"   ✓ {symbol} 数据获取完成")
            
            # 3. 构建分析 Prompt
            print(f"\n3. 构建分析 Prompt...")
            full_prompt = PromptBuilder.build_analysis_prompt(
                symbol=symbol,
                quote_data=stock_data.get("quote"),
                announcements=stock_data.get("announcements"),
                discussions=stock_data.get("discussions")
            )
            print("   ✓ Prompt 构建完成")
        
        # 6. 显示结果
        print("\n" + "=" * 60)
        print("Prompt 生成完成！")
        print("=" * 60)
        print(f"Prompt 长度: {len(full_prompt)} 字符")
        print("\n--- Prompt 预览（前800字符）---")
        print(full_prompt[:800])
        print("...")
        
        return full_prompt
        
    finally:
        # 关闭客户端
        await client.close()
        print(f"\n✓ 客户端已关闭")


async def generate_multi_stock_report(
    symbols: List[str],
    cookie: str
) -> str:
    """
    生成多只股票的报告 Prompt
    
    Args:
        symbols: 股票代码列表
        cookie: 雪球 Cookie
        
    Returns:
        完整的 Prompt
    """
    print("=" * 60)
    print(f"生成多只股票报告 Prompt ({len(symbols)} 只股票)")
    print("=" * 60)
    
    client = XueqiuRealClient(cookie=cookie)
    formatter = XueqiuDataFormatter()
    
    try:
        # 1. 获取市场上下文
        print(f"\n1. 获取市场上下文...")
        market_context_data = await client.fetch_market_context()
        print("   ✓ 市场上下文获取完成")
        
        # 2. 获取所有股票数据
        print(f"\n2. 获取 {len(symbols)} 只股票的数据...")
        stock_tasks = [client.fetch_stock_complete_data(symbol) for symbol in symbols]
        stock_data_list = await asyncio.gather(*stock_tasks)
        print(f"   ✓ 所有股票数据获取完成")
        
        # 3. 格式化市场上下文
        print(f"\n3. 格式化数据...")
        market_context_md = formatter.format_complete_market_context(
            hot_topics=market_context_data.get("hot_topics"),
            hot_posts=market_context_data.get("hot_posts"),
            special_follow=market_context_data.get("special_follow")
        )
        
        # 4. 格式化所有股票分析
        stock_analyses = []
        for stock_data in stock_data_list:
            symbol = stock_data.get("symbol")
            analysis_md = formatter.format_complete_stock_analysis(
                symbol=symbol,
                quote_data=stock_data.get("quote"),
                announcements=stock_data.get("announcements"),
                discussions=stock_data.get("discussions")
            )
            stock_analyses.append(analysis_md)
        
        stock_analysis_md = "\n\n---\n\n".join(stock_analyses)
        print("   ✓ 数据格式化完成")
        
        # 5. 构建完整 Prompt
        print(f"\n5. 构建完整 Prompt...")
        base_template = """# 投资日报生成任务

## Role
你是一位资深的金融投资顾问，擅长数据驱动的投资分析。

## Goal
根据提供的【市场全景】和【多只标的深度分析】，撰写一份逻辑严密、数据准确的投资日报。

## 市场全景
{{market_context}}

## 标的深度分析
{{stock_analysis}}

## 分析要求
1. 结合市场热门话题和用户关注，给出宏观判断
2. 逐个分析每只标的的行情、公告、讨论
3. 对比不同标的的投资机会和风险
4. 给出综合操作建议

**开始生成：**"""
        
        full_prompt = PromptBuilder.build_daily_report_prompt(
            base_template=base_template,
            market_context=market_context_md,
            stock_analysis=stock_analysis_md,
            user_preference="风险偏好：中等 | 投资风格：分散投资"
        )
        
        print("\n" + "=" * 60)
        print("Prompt 生成完成！")
        print("=" * 60)
        print(f"Prompt 长度: {len(full_prompt)} 字符")
        
        return full_prompt
        
    finally:
        await client.close()


# 从环境变量或配置文件读取 Cookie
def get_cookie() -> str:
    """
    获取雪球 Cookie
    
    优先级：
    1. 环境变量 XUEQIU_COOKIE
    2. .env 文件
    3. 提示用户输入
    """
    # 从环境变量读取
    cookie = os.getenv("XUEQIU_COOKIE")
    if cookie:
        return cookie
    
    # 从 .env 文件读取
    env_file = ".env"
    if os.path.exists(env_file):
        from dotenv import load_dotenv
        load_dotenv(env_file)
        cookie = os.getenv("XUEQIU_COOKIE")
        if cookie:
            return cookie
    
    # 提示用户
    print("\n" + "=" * 60)
    print("需要雪球 Cookie 才能调用 API")
    print("=" * 60)
    print("\n请按以下步骤获取 Cookie:")
    print("1. 打开雪球官网 https://xueqiu.com")
    print("2. 登录账号")
    print("3. 按 F12 打开开发者工具")
    print("4. 切换到 Network 标签")
    print("5. 刷新页面，找到任意请求")
    print("6. 在 Request Headers 中找到 Cookie")
    print("7. 复制完整的 Cookie 字符串")
    print("\n" + "-" * 60)
    
    cookie = input("\n请粘贴你的 Cookie: ").strip()
    
    # 保存到 .env 文件
    save = input("是否保存 Cookie 到 .env 文件? (y/n): ").strip().lower()
    if save == 'y':
        with open(env_file, 'w') as f:
            f.write(f"XUEQIU_COOKIE={cookie}\n")
        print(f"✓ Cookie 已保存到 {env_file}")
    
    return cookie


# 主程序
async def main():
    import sys
    
    # 获取 Cookie
    cookie = get_cookie()
    
    if len(sys.argv) < 3:
        print("\n使用方法:")
        print("  python real_xueqiu_integration.py daily <股票代码>           # 生成日报 Prompt")
        print("  python real_xueqiu_integration.py stock <股票代码>           # 生成单股分析 Prompt")
        print("  python real_xueqiu_integration.py multi <股票1,股票2,股票3> # 生成多股分析 Prompt")
        print("\n示例:")
        print("  python real_xueqiu_integration.py daily SH600519")
        print("  python real_xueqiu_integration.py multi SH600519,SH000001,")
        return
    
    mode = sys.argv[1]
    symbols_arg = sys.argv[2]
    
    if mode == "daily":
        symbol = symbols_arg
        prompt = await generate_report_with_real_api(symbol, cookie, "daily")
        
    elif mode == "stock":
        symbol = symbols_arg
        prompt = await generate_report_with_real_api(symbol, cookie, "stock")
        
    elif mode == "multi":
        symbols = [s.strip() for s in symbols_arg.split(',') if s.strip()]
        prompt = await generate_multi_stock_report(symbols, cookie)
        
    else:
        print(f"未知的模式: {mode}")
        return
    
    # 保存 Prompt 到文件
    output_file = f"{mode}_prompt.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"\n✓ Prompt 已保存到 {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
