#!/usr/bin/env python3
"""
nanobot Multi-Tenant Service Launcher

This script helps you quickly start the nanobot multi-tenant service,
run tests, and manage users.
"""

import argparse
import asyncio
import subprocess
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def run_api_server(host="0.0.0.0", port=8000, reload=False):
    """Start the API server."""
    print(f"🚀 Starting API server on {host}:{port}")
    print(f"   API Docs: http://{host}:{port}/docs")
    print(f"   Health: http://{host}:{port}/health")
    print()
    
    import uvicorn
    uvicorn.run(
        "nanobot.api.main:app",
        host=host,
        port=port,
        reload=reload
    )


def run_tests(test_path="tests/test_multi_tenant.py", verbose=True):
    """Run the test suite."""
    print("🧪 Running tests...")
    print()
    
    cmd = ["pytest"]
    if verbose:
        cmd.append("-v")
    cmd.append(test_path)
    
    result = subprocess.run(cmd)
    return result.returncode


def run_example():
    """Run the example script."""
    print("📝 Running example...")
    print()
    
    from examples.multi_tenant_example import example_workflow
    asyncio.run(example_workflow())


def create_user(user_id, **kwargs):
    """Create a new user."""
    print(f"👤 Creating user: {user_id}")
    print()
    
    from nanobot.workspace.manager import WorkspaceManager
    from nanobot.services.user_config import UserConfigManager
    
    workspace_manager = WorkspaceManager()
    config_manager = UserConfigManager()
    
    # Create workspace
    workspace = workspace_manager.create_workspace(
        user_id=user_id,
        template_data=kwargs
    )
    
    # Create config
    config = config_manager.create_user(user_id=user_id, initial_data=kwargs)
    
    print(f"✅ User {user_id} created successfully!")
    print(f"   Workspace: {workspace}")
    print(f"   Config: {config.to_dict()}")


def list_users():
    """List all users."""
    print("📋 Listing all users...")
    print()
    
    from nanobot.workspace.manager import WorkspaceManager
    from nanobot.services.user_config import UserConfigManager
    
    workspace_manager = WorkspaceManager()
    config_manager = UserConfigManager()
    
    users = config_manager.list_users()
    
    if not users:
        print("No users found.")
    else:
        print(f"Total users: {len(users)}")
        print()
        for user_id in users:
            info = workspace_manager.get_workspace_info(user_id)
            print(f"  👤 {user_id}")
            print(f"     Workspace: {info.get('exists', False)}")
            print(f"     Files: {info.get('files', 0)}")
            print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="nanobot Multi-Tenant Service Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start API server
  %(prog)s api
  
  # Run tests
  %(prog)s test
  
  # Run example
  %(prog)s example
  
  # Create a user
  %(prog)s create-user my_user --language zh
  
  # List all users
  %(prog)s list-users
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # API server command
    api_parser = subparsers.add_parser("api", help="Start API server")
    api_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    api_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("--path", default="tests/test_multi_tenant.py", help="Test file path")
    test_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    # Example command
    example_parser = subparsers.add_parser("example", help="Run example")
    
    # Create user command
    create_parser = subparsers.add_parser("create-user", help="Create a new user")
    create_parser.add_argument("user_id", help="User ID")
    create_parser.add_argument("--language", default="zh", help="Language preference")
    create_parser.add_argument("--report-frequency", default="daily", help="Report frequency")
    
    # List users command
    list_parser = subparsers.add_parser("list-users", help="List all users")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == "api":
        run_api_server(args.host, args.port, args.reload)
    elif args.command == "test":
        code = run_tests(args.path, args.verbose)
        sys.exit(code)
    elif args.command == "example":
        run_example()
    elif args.command == "create-user":
        create_user(
            args.user_id,
            language=args.language,
            report_frequency=args.report_frequency
        )
    elif args.command == "list-users":
        list_users()


if __name__ == "__main__":
    main()
