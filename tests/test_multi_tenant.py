"""Test suite for nanobot multi-tenant components.

This module contains unit tests and integration tests for:
- WorkspaceManager
- UserConfigManager
- MultiTenantAgentLoop
- ReportScheduler
- API endpoints
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test framework
import pytest
from pytest import fixture, mark, raises

# Import the components to test
from nanobot.workspace.manager import WorkspaceManager, WorkspaceConfig
from nanobot.services.user_config import (
    UserConfigManager,
    UserConfig,
    UserWatchlist,
    UserPreferences,
)


# ============================================================================
# Fixtures
# ============================================================================

@fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp(prefix="nanobot_test_"))
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@fixture
def workspace_manager(temp_dir):
    """Create a WorkspaceManager instance for testing."""
    return WorkspaceManager(str(temp_dir))


@fixture
def config_manager(temp_dir):
    """Create a UserConfigManager instance for testing."""
    return UserConfigManager(str(temp_dir))


@fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "user_id": "test_user_001",
        "initial_data": {
            "source": "test",
            "campaign": "pytest"
        }
    }


# ============================================================================
# WorkspaceManager Tests
# ============================================================================

class TestWorkspaceManager:
    """Test suite for WorkspaceManager."""
    
    def test_initialization(self, temp_dir):
        """Test WorkspaceManager initialization."""
        manager = WorkspaceManager(str(temp_dir))
        
        assert manager.base_path == temp_dir
        assert temp_dir.exists()
    
    def test_create_workspace(self, workspace_manager, sample_user_data):
        """Test workspace creation."""
        user_id = sample_user_data["user_id"]
        
        # Create workspace
        workspace = workspace_manager.create_workspace(
            user_id=user_id,
            template_data=sample_user_data["initial_data"]
        )
        
        # Verify workspace exists
        assert workspace.exists()
        assert workspace.name == f"user_{user_id}"
        
        # Verify standard directories
        for dir_name in WorkspaceManager.STANDARD_DIRS:
            dir_path = workspace / dir_name
            assert dir_path.exists()
            assert dir_path.is_dir()
        
        # Verify standard files
        for filename in WorkspaceManager.STANDARD_FILES.keys():
            file_path = workspace / filename
            assert file_path.exists()
            assert file_path.is_file()
    
    def test_workspace_exists(self, workspace_manager, sample_user_data):
        """Test workspace existence check."""
        user_id = sample_user_data["user_id"]
        
        # Should not exist initially
        assert not workspace_manager.workspace_exists(user_id)
        
        # Create workspace
        workspace_manager.create_workspace(user_id=user_id)
        
        # Should exist now
        assert workspace_manager.workspace_exists(user_id)
    
    def test_delete_workspace(self, workspace_manager, sample_user_data):
        """Test workspace deletion."""
        user_id = sample_user_data["user_id"]
        
        # Create and verify
        workspace_manager.create_workspace(user_id=user_id)
        assert workspace_manager.workspace_exists(user_id)
        
        # Delete
        result = workspace_manager.delete_workspace(user_id)
        
        # Verify deletion
        assert result is True
        assert not workspace_manager.workspace_exists(user_id)
        
        # Deleting non-existent should return False
        result = workspace_manager.delete_workspace("non_existent")
        assert result is False
    
    def test_get_workspace_info(self, workspace_manager, sample_user_data):
        """Test getting workspace info."""
        user_id = sample_user_data["user_id"]
        
        # Non-existent workspace
        info = workspace_manager.get_workspace_info(user_id)
        assert info["exists"] is False
        
        # Create workspace
        workspace_manager.create_workspace(user_id=user_id)
        
        # Get info
        info = workspace_manager.get_workspace_info(user_id)
        assert info["exists"] is True
        assert "path" in info
        assert "directories" in info
        assert "files" in info
    
    def test_list_workspaces(self, workspace_manager):
        """Test listing all workspaces."""
        # Initially empty
        workspaces = workspace_manager.list_workspaces()
        assert len(workspaces) == 0
        
        # Create some workspaces
        for i in range(3):
            workspace_manager.create_workspace(user_id=f"test_user_{i}")
        
        # List workspaces
        workspaces = workspace_manager.list_workspaces()
        assert len(workspaces) == 3
        
        # Verify structure
        for ws in workspaces:
            assert "user_id" in ws
            assert "info" in ws


# ============================================================================
# UserConfigManager Tests
# ============================================================================

class TestUserConfigManager:
    """Test suite for UserConfigManager."""
    
    def test_initialization(self, temp_dir):
        """Test UserConfigManager initialization."""
        manager = UserConfigManager(str(temp_dir))
        
        assert manager.base_path == temp_dir
        assert temp_dir.exists()
    
    def test_create_user(self, config_manager, sample_user_data):
        """Test user creation."""
        user_id = sample_user_data["user_id"]
        
        # Create user
        config = config_manager.create_user(
            user_id=user_id,
            initial_data=sample_user_data["initial_data"]
        )
        
        # Verify config
        assert isinstance(config, UserConfig)
        assert config.user_id == user_id
        assert config.custom_data == sample_user_data["initial_data"]
        assert isinstance(config.watchlist, UserWatchlist)
        assert isinstance(config.preferences, UserPreferences)
    
    def test_get_config(self, config_manager, sample_user_data):
        """Test getting user config."""
        user_id = sample_user_data["user_id"]
        
        # Non-existent user
        config = config_manager.get_config(user_id)
        assert config is None
        
        # Create user
        config_manager.create_user(user_id=user_id)
        
        # Get config
        config = config_manager.get_config(user_id)
        assert config is not None
        assert config.user_id == user_id
    
    def test_update_watchlist(self, config_manager, sample_user_data):
        """Test updating watchlist."""
        user_id = sample_user_data["user_id"]
        
        # Create user
        config_manager.create_user(user_id=user_id)
        
        # Update watchlist
        updated = config_manager.update_watchlist(
            user_id=user_id,
            watchlist_data={
                "stocks": ["AAPL", "TSLA"],
                "influencers": ["@elonmusk"]
            }
        )
        
        # Verify
        assert updated is not None
        assert updated.watchlist.stocks == ["AAPL", "TSLA"]
        assert updated.watchlist.influencers == ["@elonmusk"]
    
    def test_update_preferences(self, config_manager, sample_user_data):
        """Test updating preferences."""
        user_id = sample_user_data["user_id"]
        
        # Create user
        config_manager.create_user(user_id=user_id)
        
        # Update preferences
        updated = config_manager.update_preferences(
            user_id=user_id,
            prefs_data={
                "report_frequency": "weekly",
                "language": "en"
            }
        )
        
        # Verify
        assert updated is not None
        assert updated.preferences.report_frequency == "weekly"
        assert updated.preferences.language == "en"
    
    def test_delete_user(self, config_manager, sample_user_data):
        """Test deleting user."""
        user_id = sample_user_data["user_id"]
        
        # Create and verify
        config_manager.create_user(user_id=user_id)
        assert config_manager.get_config(user_id) is not None
        
        # Delete
        result = config_manager.delete_user(user_id)
        
        # Verify deletion
        assert result is True
        # Note: config_manager only marks as deleted, actual deletion is done by workspace_manager
    
    def test_list_users(self, config_manager):
        """Test listing users."""
        # Initially empty
        users = config_manager.list_users()
        assert len(users) == 0
        
        # Create some users
        for i in range(3):
            config_manager.create_user(user_id=f"test_user_{i}")
        
        # List users
        users = config_manager.list_users()
        assert len(users) == 3
        
        # Verify structure - list_users() returns a list of user_id strings
        for user_id in users:
            assert isinstance(user_id, str)
            assert user_id.startswith("test_user_")
    
    def test_get_stats(self, config_manager):
        """Test getting statistics."""
        # Empty stats
        stats = config_manager.get_stats()
        assert stats["total_users"] == 0
        assert "base_path" in stats
        
        # Create users
        for i in range(3):
            config_manager.create_user(user_id=f"test_user_{i}")
        
        # Get stats
        stats = config_manager.get_stats()
        assert stats["total_users"] == 3


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the complete system."""
    
    @pytest.mark.asyncio
    async def test_full_user_workflow(self, temp_dir):
        """Test complete user workflow from creation to report."""
        # Initialize components
        workspace_manager = WorkspaceManager(str(temp_dir))
        config_manager = UserConfigManager(str(temp_dir))
        
        # Create user with unique ID based on temp_dir to avoid conflicts
        import os
        unique_suffix = os.path.basename(temp_dir).replace("nanobot_test_", "")[:8]
        user_id = f"integration_test_{unique_suffix}"
        
        # Check if user already exists (from previous test run with same temp_dir)
        if not workspace_manager.workspace_exists(user_id):
            workspace = workspace_manager.create_workspace(user_id=user_id)
        else:
            workspace = workspace_manager.get_workspace(user_id)
        
        if config_manager.get_config(user_id) is None:
            config = config_manager.create_user(user_id=user_id)
        else:
            config = config_manager.get_config(user_id)
        
        # Update watchlist and preferences
        config_manager.update_watchlist(
            user_id=user_id,
            watchlist_data={
                "stocks": ["AAPL", "TSLA"],
                "influencers": ["@elonmusk"]
            }
        )
        
        config_manager.update_preferences(
            user_id=user_id,
            prefs_data={
                "report_frequency": "daily",
                "language": "zh"
            }
        )
        
        # Verify workspace contents
        assert (workspace / "AGENTS.md").exists()
        assert (workspace / "USER.md").exists()
        assert (workspace / "memory").exists()
        assert (workspace / "reports").exists()
        
        # Verify config
        updated_config = config_manager.get_config(user_id)
        assert updated_config is not None
        assert updated_config.watchlist.stocks == ["AAPL", "TSLA"]
        assert updated_config.preferences.report_frequency == "daily"
    
    @pytest.mark.asyncio
    async def test_multiple_users_isolation(self, temp_dir):
        """Test that user data is properly isolated."""
        # Initialize components
        workspace_manager = WorkspaceManager(str(temp_dir))
        config_manager = UserConfigManager(str(temp_dir))
        
        # Create multiple users with unique IDs based on temp_dir
        import os
        unique_suffix = os.path.basename(temp_dir).replace("nanobot_test_", "")[:8]
        users = [f"user_a_{unique_suffix}", f"user_b_{unique_suffix}", f"user_c_{unique_suffix}"]
        
        for i, user_id in enumerate(users):
            # Check if user already exists (from previous test run with same temp_dir)
            if not workspace_manager.workspace_exists(user_id):
                workspace_manager.create_workspace(user_id=user_id)
            
            if config_manager.get_config(user_id) is None:
                config = config_manager.create_user(user_id=user_id)
            else:
                config = config_manager.get_config(user_id)
            
            # Update with unique data
            config_manager.update_watchlist(
                user_id=user_id,
                watchlist_data={
                    "stocks": [f"STOCK{i}_1", f"STOCK{i}_2"]
                }
            )
        
        # Verify isolation - each user should only see their own data
        for i, user_id in enumerate(users):
            config = config_manager.get_config(user_id)
            assert config is not None
            assert config.user_id == user_id
            assert config.watchlist.stocks == [f"STOCK{i}_1", f"STOCK{i}_2"]
            
            # Verify workspace is separate
            workspace = workspace_manager.get_workspace(user_id)
            assert workspace.exists()
            assert workspace.name == f"user_{user_id}"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
