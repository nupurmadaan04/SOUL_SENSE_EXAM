"""
Tests for Plugin Architecture (#1441)

Comprehensive tests for plugin management, hook system,
and plugin execution.
"""

import asyncio
import os
import pytest
import tempfile
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base

# Import the module under test
import sys
sys.path.insert(0, 'backend/fastapi')

from api.utils.plugin_architecture import (
    PluginManager,
    Plugin,
    PluginManifest,
    PluginStatus,
    PluginType,
    Hook,
    HookPriority,
    BasePlugin,
    PluginExecutionResult,
    get_plugin_manager,
)


Base = declarative_base()


# Test Fixtures

@pytest.fixture
async def async_engine():
    """Create test async engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def manager(async_engine):
    """Create initialized plugin manager."""
    mgr = PluginManager(async_engine, plugins_dir="/tmp/test_plugins")
    
    # Create tables
    async with async_engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS plugins (
                id INTEGER PRIMARY KEY,
                plugin_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                plugin_type TEXT NOT NULL,
                manifest TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                source_path TEXT,
                config TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                installed_by TEXT,
                hash_checksum TEXT,
                last_executed_at TIMESTAMP,
                execution_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS plugin_execution_logs (
                id INTEGER PRIMARY KEY,
                log_id TEXT UNIQUE NOT NULL,
                plugin_id TEXT NOT NULL,
                action TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                output TEXT,
                error_message TEXT,
                execution_time_ms REAL,
                context_hash TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS plugin_hooks (
                id INTEGER PRIMARY KEY,
                hook_name TEXT UNIQUE NOT NULL,
                description TEXT,
                signature TEXT,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    
    await mgr.initialize()
    yield mgr


@pytest.fixture
def sample_manifest():
    """Create sample plugin manifest."""
    return PluginManifest(
        name="test_plugin",
        version="1.0.0",
        plugin_type=PluginType.ASSESSMENT,
        entry_point="test_plugin:TestPlugin",
        description="A test plugin",
        author="Test Author",
        hooks=["pre_assessment", "post_assessment"],
    )


# --- Test Classes ---

class TestPluginManifest:
    """Test plugin manifest."""
    
    def test_manifest_creation(self):
        """Test creating manifest."""
        manifest = PluginManifest(
            name="my_plugin",
            version="1.0.0",
            plugin_type=PluginType.ASSESSMENT,
            entry_point="my_plugin:MyPlugin",
            description="My plugin",
        )
        
        assert manifest.name == "my_plugin"
        assert manifest.version == "1.0.0"
        assert manifest.plugin_type == PluginType.ASSESSMENT
        assert manifest.entry_point == "my_plugin:MyPlugin"
    
    def test_manifest_to_dict(self):
        """Test manifest serialization."""
        manifest = PluginManifest(
            name="my_plugin",
            version="1.0.0",
            plugin_type=PluginType.CUSTOM,
            entry_point="my_plugin:MyPlugin",
            hooks=["hook1", "hook2"],
        )
        
        data = manifest.to_dict()
        assert data["name"] == "my_plugin"
        assert data["plugin_type"] == "custom"
        assert data["hooks"] == ["hook1", "hook2"]
    
    def test_manifest_from_dict(self):
        """Test manifest deserialization."""
        data = {
            "name": "my_plugin",
            "version": "2.0.0",
            "plugin_type": "scoring",
            "entry_point": "my_plugin:MyPlugin",
        }
        
        manifest = PluginManifest.from_dict(data)
        assert manifest.name == "my_plugin"
        assert manifest.version == "2.0.0"
        assert manifest.plugin_type == PluginType.SCORING


class TestHook:
    """Test hook system."""
    
    def test_hook_creation(self):
        """Test creating hook."""
        hook = Hook(
            hook_name="test_hook",
            description="Test hook",
            signature="(context) -> None",
        )
        
        assert hook.hook_name == "test_hook"
        assert hook.description == "Test hook"
        assert len(hook.handlers) == 0
    
    def test_add_handler(self):
        """Test adding handler to hook."""
        hook = Hook("test_hook", "Test", "()")
        
        def handler1():
            pass
        
        def handler2():
            pass
        
        hook.add_handler("plugin1", handler1, HookPriority.NORMAL)
        hook.add_handler("plugin2", handler2, HookPriority.HIGH)
        
        assert len(hook.handlers) == 2
        # High priority should be first
        assert hook.handlers[0][0] == "plugin2"
    
    def test_remove_handler(self):
        """Test removing handler from hook."""
        hook = Hook("test_hook", "Test", "()")
        
        def handler():
            pass
        
        hook.add_handler("plugin1", handler)
        assert len(hook.handlers) == 1
        
        hook.remove_handler("plugin1")
        assert len(hook.handlers) == 0


class TestBasePlugin:
    """Test base plugin class."""
    
    def test_base_plugin_creation(self):
        """Test creating base plugin."""
        class TestPlugin(BasePlugin):
            async def initialize(self):
                return True
            
            async def execute(self, action, context):
                return {"result": "success"}
        
        plugin = TestPlugin("test_id", {"key": "value"})
        assert plugin.plugin_id == "test_id"
        assert plugin.config["key"] == "value"
    
    def test_get_config(self):
        """Test get config method."""
        class TestPlugin(BasePlugin):
            async def initialize(self):
                return True
            
            async def execute(self, action, context):
                return {}
        
        plugin = TestPlugin("test", {"existing": "value"})
        assert plugin.get_config("existing") == "value"
        assert plugin.get_config("missing") is None
        assert plugin.get_config("missing", "default") == "default"


class TestPluginManager:
    """Test plugin manager functionality."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, async_engine):
        """Test manager initialization."""
        mgr = PluginManager(async_engine)
        await mgr.initialize()
        assert len(mgr._hooks) > 0  # Core hooks registered
    
    @pytest.mark.asyncio
    async def test_register_plugin(self, manager, sample_manifest):
        """Test registering a plugin."""
        plugin = await manager.register_plugin(
            manifest=sample_manifest,
            config={"test": "config"},
            installed_by="user_001",
        )
        
        assert plugin.plugin_id.startswith("plg_")
        assert plugin.manifest.name == "test_plugin"
        assert plugin.status == PluginStatus.PENDING
        assert plugin.config["test"] == "config"
        assert plugin.installed_by == "user_001"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_plugin(self, manager, sample_manifest):
        """Test registering duplicate plugin name."""
        await manager.register_plugin(manifest=sample_manifest)
        
        # Try to register again with same name
        result = await manager.register_plugin(manifest=sample_manifest)
        assert result is None  # Should fail
    
    @pytest.mark.asyncio
    async def test_get_plugin(self, manager, sample_manifest):
        """Test retrieving a plugin."""
        created = await manager.register_plugin(manifest=sample_manifest)
        
        retrieved = await manager.get_plugin(created.plugin_id)
        
        assert retrieved is not None
        assert retrieved.plugin_id == created.plugin_id
        assert retrieved.manifest.name == "test_plugin"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_plugin(self, manager):
        """Test retrieving non-existent plugin."""
        plugin = await manager.get_plugin("nonexistent")
        assert plugin is None
    
    @pytest.mark.asyncio
    async def test_list_plugins(self, manager, sample_manifest):
        """Test listing plugins."""
        # Register multiple plugins
        for i in range(3):
            manifest = PluginManifest(
                name=f"plugin_{i}",
                version="1.0.0",
                plugin_type=PluginType.ASSESSMENT,
                entry_point=f"plugin_{i}:Plugin",
            )
            await manager.register_plugin(manifest=manifest)
        
        plugins = await manager.list_plugins()
        assert len(plugins) >= 3
    
    @pytest.mark.asyncio
    async def test_list_plugins_by_status(self, manager, sample_manifest):
        """Test listing plugins by status."""
        await manager.register_plugin(manifest=sample_manifest)
        
        pending = await manager.list_plugins(status=PluginStatus.PENDING)
        assert len(pending) >= 1
    
    @pytest.mark.asyncio
    async def test_list_plugins_by_type(self, manager):
        """Test listing plugins by type."""
        manifest = PluginManifest(
            name="scoring_plugin",
            version="1.0.0",
            plugin_type=PluginType.SCORING,
            entry_point="scoring:ScoringPlugin",
        )
        await manager.register_plugin(manifest=manifest)
        
        scoring = await manager.list_plugins(plugin_type=PluginType.SCORING)
        assert len(scoring) >= 1
    
    @pytest.mark.asyncio
    async def test_deactivate_plugin(self, manager, sample_manifest):
        """Test deactivating a plugin."""
        # First create and try to activate (will fail due to no source)
        plugin = await manager.register_plugin(manifest=sample_manifest)
        
        # Deactivate should work even if not activated
        success = await manager.deactivate_plugin(plugin.plugin_id)
        assert success is True
        
        updated = await manager.get_plugin(plugin.plugin_id)
        assert updated.status == PluginStatus.DISABLED
    
    @pytest.mark.asyncio
    async def test_uninstall_plugin(self, manager, sample_manifest):
        """Test uninstalling a plugin."""
        plugin = await manager.register_plugin(manifest=sample_manifest)
        
        success = await manager.uninstall_plugin(plugin.plugin_id)
        assert success is True
        
        # Should no longer exist
        retrieved = await manager.get_plugin(plugin.plugin_id)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_version_compatibility(self, manager):
        """Test version compatibility checking."""
        # Compatible version
        compatible = PluginManifest(
            name="compatible",
            version="1.0.0",
            plugin_type=PluginType.ASSESSMENT,
            entry_point="test:Test",
            min_platform_version="1.0.0",
        )
        assert manager._check_version_compatibility(compatible) is True
        
        # Incompatible version (too high min)
        incompatible = PluginManifest(
            name="incompatible",
            version="1.0.0",
            plugin_type=PluginType.ASSESSMENT,
            entry_point="test:Test",
            min_platform_version="2.0.0",
        )
        assert manager._check_version_compatibility(incompatible) is False
    
    @pytest.mark.asyncio
    async def test_trigger_hook_empty(self, manager):
        """Test triggering hook with no handlers."""
        results = await manager.trigger_hook("pre_assessment", {})
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, manager, sample_manifest):
        """Test getting statistics."""
        await manager.register_plugin(manifest=sample_manifest)
        
        stats = await manager.get_statistics()
        
        assert stats["total_plugins"] >= 1
        assert "by_status" in stats
        assert "by_type" in stats
        assert "timestamp" in stats


class TestHookExecution:
    """Test hook execution."""
    
    @pytest.mark.asyncio
    async def test_trigger_hook_with_handlers(self, manager):
        """Test triggering hook with registered handlers."""
        # Create a simple handler
        results = []
        
        async def test_handler(context):
            results.append(context)
            return {"handled": True}
        
        # Register handler
        if "pre_assessment" in manager._hooks:
            manager._hooks["pre_assessment"].add_handler("test", test_handler)
        
        # Trigger hook
        context = {"user_id": "123"}
        hook_results = await manager.trigger_hook("pre_assessment", context)
        
        assert len(hook_results) >= 1
        assert hook_results[0].success is True


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_plugin(self, manager):
        """Test executing non-existent plugin."""
        result = await manager.execute_plugin("nonexistent", "action", {})
        
        assert result.success is False
        assert "not found" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_inactive_plugin(self, manager, sample_manifest):
        """Test executing inactive plugin."""
        plugin = await manager.register_plugin(manifest=sample_manifest)
        # Don't activate
        
        result = await manager.execute_plugin(plugin.plugin_id, "action", {})
        
        assert result.success is False
        assert "not active" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_directory_hash_empty(self, manager):
        """Test directory hash with empty directory."""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            hash1 = manager._calculate_directory_hash(tmpdir)
            hash2 = manager._calculate_directory_hash(tmpdir)
            assert hash1 == hash2  # Consistent


class TestIntegration:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_full_plugin_lifecycle(self, async_engine):
        """Test complete plugin lifecycle."""
        manager = PluginManager(async_engine)
        
        # Create tables
        async with async_engine.begin() as conn:
            for table_sql in [
                """CREATE TABLE IF NOT EXISTS plugins (
                    id INTEGER PRIMARY KEY,
                    plugin_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    plugin_type TEXT NOT NULL,
                    manifest TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    source_path TEXT,
                    config TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    installed_by TEXT,
                    hash_checksum TEXT,
                    last_executed_at TIMESTAMP,
                    execution_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0
                )""",
                """CREATE TABLE IF NOT EXISTS plugin_execution_logs (
                    id INTEGER PRIMARY KEY,
                    log_id TEXT UNIQUE NOT NULL,
                    plugin_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    output TEXT,
                    error_message TEXT,
                    execution_time_ms REAL,
                    context_hash TEXT,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                """CREATE TABLE IF NOT EXISTS plugin_hooks (
                    id INTEGER PRIMARY KEY,
                    hook_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    signature TEXT,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
            ]:
                await conn.execute(text(table_sql))
        
        await manager.initialize()
        
        # 1. Register plugin
        manifest = PluginManifest(
            name="integration_test",
            version="1.0.0",
            plugin_type=PluginType.CUSTOM,
            entry_point="test:TestPlugin",
            description="Integration test plugin",
            hooks=["pre_assessment"],
        )
        
        plugin = await manager.register_plugin(
            manifest=manifest,
            config={"key": "value"},
        )
        
        assert plugin.status == PluginStatus.PENDING
        
        # 2. Get plugin
        retrieved = await manager.get_plugin(plugin.plugin_id)
        assert retrieved.manifest.name == "integration_test"
        
        # 3. List plugins
        plugins = await manager.list_plugins()
        assert len(plugins) >= 1
        
        # 4. Deactivate (cleanup)
        await manager.deactivate_plugin(plugin.plugin_id)
        
        # 5. Uninstall
        await manager.uninstall_plugin(plugin.plugin_id)
        
        # Verify removed
        assert await manager.get_plugin(plugin.plugin_id) is None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
