"""
报告生成完整示例

展示如何使用 ReportGenerator 生成投资报告
"""

import asyncio
from pathlib import Path

from nanobot.services.report_generator import ReportGenerator
from nanobot.services.user_config import UserConfig, UserWatchlist
from nanobot.services.data_fetcher import DataFetcher
from nanobot.services.stock_api_client import StockDataAPIClient


async def main():
    """
    完整示例：生成投资报告
    """
    print("=" * 60)
    print("投资报告生成示例")
    print("=" * 60)
    
    # 1. 创建模拟的用户配置
    user_config = UserConfig.create(
        user_id="user_001",
        initial_data={
            "persona": {
                "risk_preference": "moderate",
                "investment_style": "价值投资",
                "focus_areas": ["AI", "新能源", "白酒"]
            }
        }
    )
    
    # 设置关注列表
    user_config.watchlist = UserWatchlist(
        stocks=["600519", "300750"],  # 贵州茅台、宁德时代
        influencers=["张三投资", "李四财经"],
        keywords=["AI", "新能源"],
        sectors=["白酒", "新能源"]
    )
    
    print(f"\n用户配置:")
    print(f"  用户ID: {user_config.user_id}")
    print(f"  关注股票: {user_config.watchlist.stocks}")
    print(f"  关注大V: {user_config.watchlist.influencers}")
    
    # 2. 创建 API 客户端（实际使用时替换为真实的 API）
    api_client = StockDataAPIClient(api_key="demo_key")
    
    # 3. 创建数据获取器
    data_fetcher = DataFetcher(api_client=api_client)
    
    # 4. 创建报告生成器
    # 注意：这里需要传入实际的 config_manager 和 workspace_manager
    # 为了演示，我们创建一个简单的模拟版本
    
    class MockConfigManager:
        def get_config(self, user_id):
            return user_config
    
    class MockWorkspaceManager:
        def get_workspace(self, user_id):
            return Path(f"/tmp/workspace/{user_id}")
    
    config_manager = MockConfigManager()
    workspace_manager = MockWorkspaceManager()
    
    # 创建报告生成器（不使用 agent_loop，使用模拟模式）
    report_generator = ReportGenerator(
        config_manager=config_manager,
        workspace_manager=workspace_manager,
        data_fetcher=data_fetcher,
        max_retries=3
    )
    
    print(f"\n报告生成器初始化完成")
    
    # 5. 生成报告
    print(f"\n开始生成报告...")
    print("-" * 60)
    
    result = await report_generator.generate_report(
        user_id="user_001",
        report_type="daily",
        use_cache=False
    )
    
    # 6. 显示结果
    print("\n" + "=" * 60)
    print("报告生成结果")
    print("=" * 60)
    
    if result["success"]:
        print(f"\n✓ 报告生成成功!")
        print(f"  报告ID: {result['report_id']}")
        print(f"  报告路径: {result['report_path']}")
        print(f"\n报告内容预览:")
        print("-" * 60)
        print(result["content"][:500] + "..." if len(result["content"]) > 500 else result["content"])
        print("-" * 60)
    else:
        print(f"\n✗ 报告生成失败: {result.get('error')}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
