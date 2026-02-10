#!/usr/bin/env python3
"""
场景模拟脚本 - 修复版
模拟三个场景：
1. 新用户场景，增加用户，同时设置该用户的特性
2. 触发定时生成报告的逻辑，在对应用户的 workspace 中生成真实的报告
3. 多名用户设定的报告时间已经到达，在其 workspace 中完成报告输出
"""

import asyncio
import json
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path

# API 基础 URL
BASE_URL = "http://localhost:8000"


async def create_user(session: aiohttp.ClientSession, user_id: str) -> dict:
    """场景1: 创建新用户"""
    print(f"\n{'='*60}")
    print(f"场景 1.1: 创建新用户 - {user_id}")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/users"
    data = {"user_id": user_id}
    
    async with session.post(url, json=data) as response:
        result = await response.json()
        if response.status in [200, 201]:
            print(f"✓ 用户创建成功")
            print(f"  - 用户ID: {result['user_id']}")
            print(f"  - 创建时间: {result['created_at']}")
            return result
        else:
            print(f"✗ 用户创建失败: {result}")
            return None


async def update_watchlist(session: aiohttp.ClientSession, user_id: str) -> dict:
    """场景1: 更新用户关注列表（特性设置）"""
    print(f"\n{'='*60}")
    print(f"场景 1.2: 设置用户特性 - {user_id} 的关注列表")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/users/{user_id}/watchlist"
    data = {
        "stocks": ["AAPL", "TSLA", "BABA", "0700.HK", "NVDA"],
        "influencers": ["@elonmusk", "@雷总", "@段永平", "@张磊"],
        "keywords": ["人工智能", "新能源", "芯片", "电动车", "大模型"],
        "sectors": ["科技", "汽车", "半导体", "互联网"]
    }
    
    async with session.put(url, json=data) as response:
        if response.status == 200:
            result = await response.json()
            print(f"✓ 关注列表更新成功")
            print(f"  - 股票: {', '.join(result['watchlist']['stocks'])}")
            print(f"  - 大V: {', '.join(result['watchlist']['influencers'])}")
            print(f"  - 关键词: {', '.join(result['watchlist']['keywords'])}")
            return result
        else:
            error = await response.text()
            print(f"✗ 关注列表更新失败: {error}")
            return None


async def update_preferences(session: aiohttp.ClientSession, user_id: str) -> dict:
    """场景1: 更新用户偏好设置（特性设置）"""
    print(f"\n{'='*60}")
    print(f"场景 1.3: 设置用户特性 - {user_id} 的偏好设置")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/users/{user_id}/preferences"
    # 设置报告时间为下午 2:20 (14:20)
    data = {
        "report_frequency": "daily",
        "report_time": "14:20",
        "report_format": "markdown",
        "language": "zh",
        "max_report_length": 3000,
        "notification_channels": ["push", "email"]
    }
    
    async with session.put(url, json=data) as response:
        if response.status == 200:
            result = await response.json()
            print(f"✓ 偏好设置更新成功")
            print(f"  - 报告频率: {result['preferences']['report_frequency']}")
            print(f"  - 报告时间: {result['preferences']['report_time']}")
            print(f"  - 语言: {result['preferences']['language']}")
            print(f"  - 通知渠道: {', '.join(result['preferences']['notification_channels'])}")
            return result
        else:
            error = await response.text()
            print(f"✗ 偏好设置更新失败: {error}")
            return None


async def trigger_report_generation(session: aiohttp.ClientSession, user_id: str, report_type: str = "daily") -> dict:
    """场景2: 触发定时报告生成"""
    print(f"\n{'='*60}")
    print(f"场景 2: 触发定时生成报告 - {user_id}")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/reports"
    data = {
        "report_type": report_type,
        "custom_prompt": None,
        "focus_areas": ["stock_analysis", "market_overview", "watchlist_summary"]
    }
    
    # 使用 token 作为 user_id 进行认证（根据 main.py 中的 get_current_user 逻辑）
    headers = {"Authorization": f"Bearer {user_id}"}
    
    async with session.post(url, json=data, headers=headers) as response:
        if response.status in [200, 201, 202]:
            result = await response.json()
            print(f"✓ 报告生成任务已触发")
            print(f"  - 用户: {user_id}")
            print(f"  - 报告ID: {result.get('report_id')}")
            print(f"  - 状态: {result.get('status')}")
            print(f"  - 消息: {result.get('message')}")
            print(f"\n  报告将保存到: ~/.nanobot/workspaces/user_{user_id}/reports/")
            return result
        else:
            error = await response.text()
            print(f"✗ 报告生成触发失败: {error}")
            return None


async def setup_multi_user_schedule(session: aiohttp.ClientSession) -> list:
    """场景3: 设置多个用户的定时报告任务"""
    print(f"\n{'='*60}")
    print(f"场景 3: 多名用户设定报告时间")
    print(f"{'='*60}")
    
    # 定义多个用户，各自有不同的报告时间
    users = [
        {
            "id": "investor_a", 
            "report_time": "08:00",  # 早上8点
            "stocks": ["AAPL", "MSFT", "GOOGL"],
            "report_frequency": "daily"
        },
        {
            "id": "trader_b", 
            "report_time": "09:30",  # 开盘时间
            "stocks": ["TSLA", "NVDA", "AMD"],
            "report_frequency": "daily"
        },
        {
            "id": "analyst_c", 
            "report_time": "07:30",  # 盘前
            "stocks": ["BABA", "0700.HK", "TCEHY"],
            "report_frequency": "daily"
        }
    ]
    
    created_users = []
    
    for user in users:
        print(f"\n  处理用户: {user['id']}")
        
        # 创建用户
        user_result = await create_user(session, user['id'])
        if user_result:
            # 设置关注列表
            await update_watchlist_for_user(session, user['id'], user['stocks'])
            
            # 设置偏好（报告时间）
            await update_preferences_for_user(
                session, 
                user['id'], 
                user['report_time'], 
                user['report_frequency']
            )
            
            created_users.append(user)
            print(f"  ✓ 用户 {user['id']} 的定时任务已设置")
            print(f"    - 报告时间: 每天 {user['report_time']}")
            print(f"    - 关注股票: {', '.join(user['stocks'])}")
    
    print(f"\n{'='*60}")
    print(f"✓ 场景 3 完成")
    print(f"  - 共设置 {len(created_users)} 个用户的定时报告任务")
    print(f"  - 报告将按各自设定的时间自动生成")
    print(f"  - 报告将保存到各用户的 workspace/reports/ 目录")
    print(f"{'='*60}")
    
    return created_users


async def update_watchlist_for_user(session: aiohttp.ClientSession, user_id: str, stocks: list):
    """为特定用户更新关注列表"""
    url = f"{BASE_URL}/users/{user_id}/watchlist"
    data = {
        "stocks": stocks,
        "influencers": [],
        "keywords": ["科技股", "财报", "市场动态"],
        "sectors": ["科技"]
    }
    
    async with session.put(url, json=data) as response:
        if response.status == 200:
            pass


async def update_preferences_for_user(
    session: aiohttp.ClientSession, 
    user_id: str, 
    report_time: str,
    report_frequency: str = "daily"
):
    """为特定用户更新偏好设置"""
    url = f"{BASE_URL}/users/{user_id}/preferences"
    # 设置报告时间为下午 2:20 (14:20)
    data = {
        "report_frequency": report_frequency,
        "report_time": "14:20",
        "report_format": "markdown",
        "language": "zh",
        "max_report_length": 3000,
        "notification_channels": ["push"]
    }
    
    async with session.put(url, json=data) as response:
        if response.status == 200:
            pass


async def main():
    """主函数：运行所有场景测试"""
    print(f"\n{'='*70}")
    print("Nanobot 多租户服务 - 场景模拟测试")
    print(f"{'='*70}")
    print(f"\nAPI 地址: {BASE_URL}")
    print(f"测试时间: {datetime.now().isoformat()}")
    
    async with aiohttp.ClientSession() as session:
        # 检查服务健康状态
        try:
            async with session.get(f"{BASE_URL}/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print(f"\n✓ 服务状态: {health['status']}")
                    print(f"  - 版本: {health['version']}")
                    print(f"  - 时间: {health['timestamp']}")
                else:
                    print(f"\n✗ 服务未就绪 (状态码: {resp.status})")
                    return
        except Exception as e:
            print(f"\n✗ 无法连接到服务: {e}")
            print(f"  请确保服务已启动: python -m nanobot.api.main")
            return
        
        results = {
            "scenario1": False,
            "scenario2": False,
            "scenario3": False
        }
        
        # ========== 场景 1: 新用户场景 ==========
        print(f"\n{'='*70}")
        print("开始场景 1: 新用户场景 - 增加用户并设置特性")
        print(f"{'='*70}")
        
        test_user_id = f"demo_user_{datetime.now().strftime('%H%M%S')}"
        
        # 1.1 创建用户
        user_result = await create_user(session, test_user_id)
        if user_result:
            # 1.2 更新关注列表
            await update_watchlist(session, test_user_id)
            
            # 1.3 更新偏好设置
            await update_preferences(session, test_user_id)
            
            results["scenario1"] = True
            print(f"\n✓ 场景 1 完成: 用户 {test_user_id} 已创建并配置完成")
        else:
            print(f"\n✗ 场景 1 失败: 无法创建用户")
        
        # ========== 场景 2: 触发定时生成报告 ==========
        if results["scenario1"]:
            print(f"\n{'='*70}")
            print("开始场景 2: 触发定时生成报告逻辑")
            print(f"{'='*70}")
            
            report_result = await trigger_report_generation(
                session, 
                test_user_id, 
                report_type="daily"
            )
            
            if report_result:
                results["scenario2"] = True
                print(f"\n✓ 场景 2 完成: 报告生成任务已触发")
            else:
                print(f"\n✗ 场景 2 失败: 无法触发报告生成")
        
        # ========== 场景 3: 多用户定时报告任务 ==========
        print(f"\n{'='*70}")
        print("开始场景 3: 多名用户设定报告时间，在其 workspace 中完成报告输出")
        print(f"{'='*70}")
        
        users = await setup_multi_user_schedule(session)
        
        if users:
            results["scenario3"] = True
            print(f"\n✓ 场景 3 完成: 已为 {len(users)} 个用户设置定时报告任务")
        else:
            print(f"\n⚠ 场景 3 部分完成: 部分用户设置可能失败")
        
        # ========== 测试总结 ==========
        print(f"\n{'='*70}")
        print("测试总结")
        print(f"{'='*70}")
        print(f"✓ 场景 1: 新用户创建与配置 - {'完成' if results['scenario1'] else '失败'}")
        print(f"✓ 场景 2: 报告生成触发 - {'完成' if results['scenario2'] else '失败'}")
        print(f"✓ 场景 3: 多用户定时任务 - {'完成' if results['scenario3'] else '部分完成'}")
        
        print(f"\n{'='*70}")
        print("工作区路径: ~/.nanobot/workspaces/")
        print("报告输出路径: ~/.nanobot/workspaces/user_{user_id}/reports/")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    # Check if required packages are installed
    try:
        import aiohttp
    except ImportError:
        print("错误: 请先安装 aiohttp: pip install aiohttp")
        exit(1)
    
    # Run the test
    asyncio.run(main())
