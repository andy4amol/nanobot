"""
Example usage of MultiTenantAgentLoop and supporting components.

This example demonstrates how to use the multi-tenant features of nanobot
to serve multiple users with isolated workspaces.
"""

import asyncio
from pathlib import Path

# Import the multi-tenant components
from nanobot.workspace.manager import WorkspaceManager
from nanobot.services.user_config import UserConfigManager
from nanobot.agent.multi_tenant_loop import MultiTenantAgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.config.loader import load_config


async def example_workflow():
    """
    Example workflow demonstrating the multi-tenant setup.
    """
    print("=" * 60)
    print("nanobot Multi-Tenant Example")
    print("=" * 60)
    
    # 1. Initialize Workspace Manager
    print("\n[1] Initializing Workspace Manager...")
    workspace_manager = WorkspaceManager("~/.nanobot/workspaces")
    
    # 2. Initialize User Config Manager
    print("\n[2] Initializing User Config Manager...")
    config_manager = UserConfigManager("~/.nanobot/workspaces")
    
    # 3. Create example users
    print("\n[3] Creating example users...")
    
    # User 1: Alice - Tech enthusiast
    user1_id = "alice_tech"
    if not workspace_manager.workspace_exists(user1_id):
        print(f"  Creating workspace for {user1_id}...")
        workspace = workspace_manager.create_workspace(
            user_id=user1_id,
            template_data={
                "language": "zh",
                "report_format": "markdown"
            }
        )
        
        # Create user config
        config = config_manager.create_user(user1_id)
        config.update_watchlist(
            stocks=["AAPL", "TSLA", "NVDA", "MSFT"],
            influencers=["@elonmusk", "@satyanadella", "@tim_cook"],
            keywords=["AI", "Electric Vehicles", "Cloud Computing"],
            sectors=["Technology", "Automotive"]
        )
        config.update_preferences(
            report_frequency="daily",
            report_time="09:00",
            language="zh"
        )
        config_manager.save_config(config)
        print(f"  ✓ User {user1_id} created successfully")
    else:
        print(f"  User {user1_id} already exists")
    
    # User 2: Bob - Finance focus
    user2_id = "bob_finance"
    if not workspace_manager.workspace_exists(user2_id):
        print(f"  Creating workspace for {user2_id}...")
        workspace = workspace_manager.create_workspace(
            user_id=user2_id,
            template_data={
                "language": "en",
                "report_format": "markdown"
            }
        )
        
        # Create user config
        config = config_manager.create_user(user2_id)
        config.update_watchlist(
            stocks=["JPM", "BAC", "GS", "V"],
            influencers=["@RayDalio", "@WarrenBuffett"],
            keywords=["Interest Rates", "Inflation", "Banking"],
            sectors=["Finance", "Banking"]
        )
        config.update_preferences(
            report_frequency="weekly",
            report_time="08:00",
            language="en"
        )
        config_manager.save_config(config)
        print(f"  ✓ User {user2_id} created successfully")
    else:
        print(f"  User {user2_id} already exists")
    
    # 4. Initialize the multi-tenant agent loop
    print("\n[4] Initializing MultiTenantAgentLoop...")
    
    # Load configuration
    config = load_config()
    
    # Create components
    bus = MessageBus()
    provider = LiteLLMProvider(
        api_key=config.get_api_key(),
        api_base=config.get_api_base(),
        default_model=config.agents.defaults.model
    )
    
    # Create the multi-tenant loop
    loop = MultiTenantAgentLoop(
        bus=bus,
        provider=provider,
        workspace_manager=workspace_manager,
        model=config.agents.defaults.model,
        brave_api_key=config.tools.web.search.api_key or None,
        exec_config=config.tools.exec,
    )
    
    print("  ✓ MultiTenantAgentLoop initialized")
    
    # 5. Demonstrate processing messages for different users
    print("\n[5] Processing messages for different users...")
    
    # Process message for Alice
    print("\n  Processing for Alice (alice_tech)...")
    try:
        response1 = await loop.process_for_user(
            user_id="alice_tech",
            message="Generate a brief summary of my watchlist stocks performance today",
            session_key="demo_session_1"
        )
        print(f"  ✓ Alice's response received (length: {len(response1)})")
        # Print first 200 chars
        print(f"  Preview: {response1[:200]}...")
    except Exception as e:
        print(f"  ✗ Error processing for Alice: {e}")
    
    # Process message for Bob
    print("\n  Processing for Bob (bob_finance)...")
    try:
        response2 = await loop.process_for_user(
            user_id="bob_finance",
            message="What are the latest updates on my banking sector watchlist?",
            session_key="demo_session_2"
        )
        print(f"  ✓ Bob's response received (length: {len(response2)})")
        # Print first 200 chars
        print(f"  Preview: {response2[:200]}...")
    except Exception as e:
        print(f"  ✗ Error processing for Bob: {e}")
    
    # 6. Show workspace info
    print("\n[6] Workspace information:")
    
    for user_id in ["alice_tech", "bob_finance"]:
        info = workspace_manager.get_workspace_info(user_id)
        print(f"\n  User: {user_id}")
        print(f"    Exists: {info['exists']}")
        if info['exists']:
            print(f"    Path: {info['path']}")
            print(f"    Directories: {info['directories']}")
            print(f"    Files: {info['files']}")
    
    # 7. List all workspaces
    print("\n[7] All workspaces:")
    all_workspaces = workspace_manager.list_workspaces()
    print(f"  Total workspaces: {len(all_workspaces)}")
    for ws in all_workspaces:
        print(f"    - {ws['user_id']}")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_workflow())
