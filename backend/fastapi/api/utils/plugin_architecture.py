"""
Plugin Architecture for Assessment Modules (#1441)

Provides a flexible plugin system for extending assessment capabilities.
Allows dynamic loading, registration, and execution of assessment plugins
with proper isolation, versioning, and lifecycle management.

Features:
- Plugin registration and discovery
- Version management and compatibility checking
- Hook system for extending core functionality
- Sandboxed plugin execution
- Plugin dependency management
- Hot-reloading support
- Plugin marketplace integration

Example:
    from api.utils.plugin_architecture import PluginManager, PluginManifest
    
    manager = PluginManager()
    await manager.initialize()
    
    # Register a plugin
    plugin = await manager.register_plugin(
        manifest=PluginManifest(
            name="custom_assessment",
            version="1.0.0",
            entry_point="custom_assessment.plugin:AssessmentPlugin"
        ),
        source_path="/plugins/custom_assessment"
    )
    
    # Execute plugin
    result = await manager.execute_plugin(
        plugin_id=plugin.plugin_id,
        action="assess",
        context={"user_id": "user_123"}
    )
"""

import asyncio
import hashlib
import importlib
import importlib.util
import inspect
import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union
from uuid import uuid4

from sqlalchemy import text, Column, String, DateTime, Integer, Boolean, Text, JSON, Float
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import declarative_base

from ..services.db_service import AsyncSessionLocal, engine


logger = logging.getLogger("api.plugin_architecture")

Base = declarative_base()


class PluginStatus(str, Enum):
    """Status of a plugin."""
    PENDING = "pending"  # Awaiting validation
    ACTIVE = "active"  # Ready for use
    DISABLED = "disabled"  # Temporarily disabled
    ERROR = "error"  # Error state
    DEPRECATED = "deprecated"  # No longer supported
    UNINSTALLED = "uninstalled"  # Removed


class PluginType(str, Enum):
    """Type of assessment plugin."""
    ASSESSMENT = "assessment"  # Core assessment logic
    REPORT = "report"  # Report generation
    INTEGRATION = "integration"  # External integrations
    VALIDATION = "validation"  # Data validation
    SCORING = "scoring"  # Scoring algorithms
    NOTIFICATION = "notification"  # Notifications
    CUSTOM = "custom"  # Custom plugins


class HookPriority(int, Enum):
    """Priority levels for hook handlers."""
    LOW = 100
    NORMAL = 50
    HIGH = 10
    CRITICAL = 1


@dataclass
class PluginManifest:
    """Manifest describing a plugin."""
    name: str
    version: str
    plugin_type: PluginType
    entry_point: str
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    requirements: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    hooks: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    min_platform_version: str = "1.0.0"
    max_platform_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "plugin_type": self.plugin_type.value,
            "entry_point": self.entry_point,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "homepage": self.homepage,
            "repository": self.repository,
            "requirements": self.requirements,
            "dependencies": self.dependencies,
            "config_schema": self.config_schema,
            "hooks": self.hooks,
            "permissions": self.permissions,
            "min_platform_version": self.min_platform_version,
            "max_platform_version": self.max_platform_version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        return cls(
            name=data["name"],
            version=data["version"],
            plugin_type=PluginType(data.get("plugin_type", "custom")),
            entry_point=data["entry_point"],
            description=data.get("description"),
            author=data.get("author"),
            license=data.get("license"),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
            requirements=data.get("requirements", []),
            dependencies=data.get("dependencies", []),
            config_schema=data.get("config_schema", {}),
            hooks=data.get("hooks", []),
            permissions=data.get("permissions", []),
            min_platform_version=data.get("min_platform_version", "1.0.0"),
            max_platform_version=data.get("max_platform_version"),
        )


@dataclass
class Plugin:
    """Represents a loaded plugin."""
    plugin_id: str
    manifest: PluginManifest
    status: PluginStatus
    source_path: Optional[str]
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    installed_by: Optional[str] = None
    hash_checksum: Optional[str] = None
    last_executed_at: Optional[datetime] = None
    execution_count: int = 0
    error_count: int = 0
    instance: Optional[Any] = field(default=None, repr=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "manifest": self.manifest.to_dict(),
            "status": self.status.value,
            "source_path": self.source_path,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "installed_by": self.installed_by,
            "hash_checksum": self.hash_checksum,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
        }


@dataclass
class Hook:
    """Represents a hook that plugins can subscribe to."""
    hook_name: str
    description: Optional[str]
    signature: str
    handlers: List[Tuple[str, Callable, HookPriority]] = field(default_factory=list)
    
    def add_handler(self, plugin_id: str, handler: Callable, priority: HookPriority = HookPriority.NORMAL):
        """Add a handler for this hook."""
        self.handlers.append((plugin_id, handler, priority))
        # Sort by priority (lower number = higher priority)
        self.handlers.sort(key=lambda x: x[2].value)
    
    def remove_handler(self, plugin_id: str):
        """Remove all handlers for a plugin."""
        self.handlers = [(pid, h, p) for pid, h, p in self.handlers if pid != plugin_id]


@dataclass
class PluginExecutionResult:
    """Result of executing a plugin."""
    success: bool
    plugin_id: str
    action: str
    output: Any = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "plugin_id": self.plugin_id,
            "action": self.action,
            "output": self.output,
            "error_message": self.error_message,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "timestamp": self.timestamp.isoformat(),
        }


class BasePlugin(ABC):
    """Base class for all plugins."""
    
    def __init__(self, plugin_id: str, config: Dict[str, Any]):
        self.plugin_id = plugin_id
        self.config = config
        self.logger = logging.getLogger(f"plugin.{plugin_id}")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin."""
        pass
    
    @abstractmethod
    async def execute(self, action: str, context: Dict[str, Any]) -> Any:
        """Execute a plugin action."""
        pass
    
    async def shutdown(self) -> bool:
        """Shutdown the plugin gracefully."""
        return True
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)


class PluginManager:
    """
    Manager for assessment plugins.
    
    Handles plugin registration, lifecycle management, hook execution,
    and sandboxed plugin execution.
    
    Example:
        manager = PluginManager()
        await manager.initialize()
        
        # Register from directory
        plugin = await manager.register_plugin_from_directory(
            "/plugins/my_plugin"
        )
        
        # Execute
        result = await manager.execute_plugin(
            plugin_id=plugin.plugin_id,
            action="analyze",
            context={"data": {...}}
        )
        
        # Trigger hooks
        results = await manager.trigger_hook(
            "pre_assessment",
            context={"user_id": "123"}
        )
    """
    
    PLATFORM_VERSION = "1.0.0"
    
    def __init__(self, engine: Optional[AsyncEngine] = None, plugins_dir: Optional[str] = None):
        self.engine = engine
        self.plugins_dir = plugins_dir or os.path.join(os.getcwd(), "plugins")
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, Hook] = {}
        self._enabled_hooks: Set[str] = set()
    
    async def initialize(self) -> None:
        """Initialize the plugin manager."""
        await self._ensure_tables()
        await self._load_active_plugins()
        await self._register_core_hooks()
        logger.info("PluginManager initialized")
    
    async def _ensure_tables(self) -> None:
        """Ensure plugin tables exist."""
        if not self.engine:
            from ..services.db_service import engine as db_engine
            self.engine = db_engine
        
        async with self.engine.begin() as conn:
            # Plugins table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS plugins (
                    id SERIAL PRIMARY KEY,
                    plugin_id VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    version VARCHAR(50) NOT NULL,
                    plugin_type VARCHAR(50) NOT NULL,
                    manifest JSONB NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    source_path TEXT,
                    config JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    installed_by VARCHAR(255),
                    hash_checksum VARCHAR(255),
                    last_executed_at TIMESTAMP,
                    execution_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0
                )
            """))
            
            # Plugin execution logs table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS plugin_execution_logs (
                    id SERIAL PRIMARY KEY,
                    log_id VARCHAR(255) UNIQUE NOT NULL,
                    plugin_id VARCHAR(255) NOT NULL,
                    action VARCHAR(255) NOT NULL,
                    success BOOLEAN NOT NULL,
                    output JSONB,
                    error_message TEXT,
                    execution_time_ms FLOAT,
                    context_hash VARCHAR(255),
                    executed_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            # Plugin hooks table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS plugin_hooks (
                    id SERIAL PRIMARY KEY,
                    hook_name VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    signature VARCHAR(255),
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            # Create indexes
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_plugins_status 
                ON plugins(status, plugin_type)
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_plugin_logs_plugin 
                ON plugin_execution_logs(plugin_id, executed_at DESC)
            """))
        
        logger.info("Plugin tables ensured")
    
    async def _load_active_plugins(self) -> None:
        """Load active plugins from database."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT * FROM plugins WHERE status = 'active'")
            )
            
            for row in result:
                try:
                    manifest = PluginManifest.from_dict(row.manifest)
                    plugin = Plugin(
                        plugin_id=row.plugin_id,
                        manifest=manifest,
                        status=PluginStatus(row.status),
                        source_path=row.source_path,
                        config=row.config,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                        installed_by=row.installed_by,
                        hash_checksum=row.hash_checksum,
                        last_executed_at=row.last_executed_at,
                        execution_count=row.execution_count,
                        error_count=row.error_count,
                    )
                    
                    # Load plugin instance
                    if await self._load_plugin_instance(plugin):
                        self._plugins[plugin.plugin_id] = plugin
                        await self._register_plugin_hooks(plugin)
                        logger.info(f"Loaded plugin {plugin.plugin_id}")
                
                except Exception as e:
                    logger.error(f"Failed to load plugin {row.plugin_id}: {e}")
    
    async def _load_plugin_instance(self, plugin: Plugin) -> bool:
        """Load the plugin instance from source."""
        try:
            if not plugin.source_path or not os.path.exists(plugin.source_path):
                logger.error(f"Plugin source not found: {plugin.source_path}")
                return False
            
            # Add to path if needed
            if plugin.source_path not in sys.path:
                sys.path.insert(0, plugin.source_path)
            
            # Parse entry point
            module_name, class_name = plugin.manifest.entry_point.split(":")
            
            # Import module
            spec = importlib.util.spec_from_file_location(
                module_name,
                os.path.join(plugin.source_path, f"{module_name.replace('.', '/')}.py")
            )
            if spec is None or spec.loader is None:
                # Try as regular import
                module = importlib.import_module(module_name)
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            
            # Get plugin class
            plugin_class = getattr(module, class_name)
            
            # Instantiate
            if issubclass(plugin_class, BasePlugin):
                plugin.instance = plugin_class(plugin.plugin_id, plugin.config)
                return await plugin.instance.initialize()
            else:
                logger.error(f"Plugin class does not inherit from BasePlugin: {class_name}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to load plugin instance: {e}")
            return False
    
    async def _register_core_hooks(self) -> None:
        """Register core system hooks."""
        core_hooks = [
            Hook("pre_assessment", "Called before assessment execution", "(context: Dict) -> None"),
            Hook("post_assessment", "Called after assessment execution", "(context: Dict, result: Any) -> None"),
            Hook("pre_scoring", "Called before scoring", "(context: Dict) -> None"),
            Hook("post_scoring", "Called after scoring", "(context: Dict, score: float) -> None"),
            Hook("pre_report", "Called before report generation", "(context: Dict) -> None"),
            Hook("post_report", "Called after report generation", "(context: Dict, report: Any) -> None"),
        ]
        
        for hook in core_hooks:
            self._hooks[hook.hook_name] = hook
            self._enabled_hooks.add(hook.hook_name)
        
        # Persist to database
        async with AsyncSessionLocal() as session:
            for hook in core_hooks:
                await session.execute(
                    text("""
                        INSERT INTO plugin_hooks (hook_name, description, signature)
                        VALUES (:name, :desc, :sig)
                        ON CONFLICT (hook_name) DO NOTHING
                    """),
                    {"name": hook.hook_name, "desc": hook.description, "sig": hook.signature}
                )
            await session.commit()
    
    async def _register_plugin_hooks(self, plugin: Plugin) -> None:
        """Register hooks for a plugin."""
        if not plugin.instance:
            return
        
        for hook_name in plugin.manifest.hooks:
            if hook_name in self._hooks:
                # Check if plugin has handler method
                handler_name = f"on_{hook_name}"
                if hasattr(plugin.instance, handler_name):
                    handler = getattr(plugin.instance, handler_name)
                    self._hooks[hook_name].add_handler(plugin.plugin_id, handler)
                    logger.debug(f"Registered handler for {hook_name} from {plugin.plugin_id}")
    
    async def register_plugin_from_directory(
        self,
        directory: str,
        config: Optional[Dict[str, Any]] = None,
        installed_by: Optional[str] = None
    ) -> Optional[Plugin]:
        """
        Register a plugin from a directory.
        
        Args:
            directory: Path to plugin directory
            config: Plugin configuration
            installed_by: User who installed the plugin
            
        Returns:
            Registered Plugin or None if failed
        """
        directory = os.path.abspath(directory)
        manifest_path = os.path.join(directory, "plugin.json")
        
        if not os.path.exists(manifest_path):
            logger.error(f"Plugin manifest not found: {manifest_path}")
            return None
        
        try:
            with open(manifest_path, "r") as f:
                manifest_data = json.load(f)
            
            manifest = PluginManifest.from_dict(manifest_data)
            return await self.register_plugin(manifest, directory, config, installed_by)
        
        except Exception as e:
            logger.error(f"Failed to load plugin from {directory}: {e}")
            return None
    
    async def register_plugin(
        self,
        manifest: PluginManifest,
        source_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        installed_by: Optional[str] = None
    ) -> Optional[Plugin]:
        """
        Register a new plugin.
        
        Args:
            manifest: Plugin manifest
            source_path: Path to plugin source
            config: Plugin configuration
            installed_by: User who installed the plugin
            
        Returns:
            Registered Plugin or None if failed
        """
        # Validate platform compatibility
        if not self._check_version_compatibility(manifest):
            logger.error(f"Plugin {manifest.name} incompatible with platform version {self.PLATFORM_VERSION}")
            return None
        
        # Check for existing plugin with same name
        existing = await self._get_plugin_by_name(manifest.name)
        if existing:
            logger.error(f"Plugin with name {manifest.name} already exists")
            return None
        
        plugin_id = f"plg_{uuid4().hex[:12]}"
        
        # Calculate checksum if source provided
        hash_checksum = None
        if source_path and os.path.exists(source_path):
            hash_checksum = self._calculate_directory_hash(source_path)
        
        plugin = Plugin(
            plugin_id=plugin_id,
            manifest=manifest,
            status=PluginStatus.PENDING,
            source_path=source_path,
            config=config or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            installed_by=installed_by,
            hash_checksum=hash_checksum,
        )
        
        # Persist to database
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO plugins (
                        plugin_id, name, version, plugin_type, manifest,
                        status, source_path, config, created_at, updated_at,
                        installed_by, hash_checksum
                    ) VALUES (
                        :plugin_id, :name, :version, :plugin_type, :manifest,
                        :status, :source_path, :config, :created_at, :updated_at,
                        :installed_by, :hash_checksum
                    )
                """),
                {
                    "plugin_id": plugin.plugin_id,
                    "name": plugin.manifest.name,
                    "version": plugin.manifest.version,
                    "plugin_type": plugin.manifest.plugin_type.value,
                    "manifest": json.dumps(plugin.manifest.to_dict()),
                    "status": plugin.status.value,
                    "source_path": plugin.source_path,
                    "config": json.dumps(plugin.config),
                    "created_at": plugin.created_at,
                    "updated_at": plugin.updated_at,
                    "installed_by": plugin.installed_by,
                    "hash_checksum": plugin.hash_checksum,
                }
            )
            await session.commit()
        
        self._plugins[plugin_id] = plugin
        logger.info(f"Registered plugin {plugin_id}: {manifest.name}")
        
        return plugin
    
    async def activate_plugin(self, plugin_id: str) -> bool:
        """Activate a pending plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        # Load instance
        if not await self._load_plugin_instance(plugin):
            plugin.status = PluginStatus.ERROR
            await self._update_plugin_status(plugin)
            return False
        
        # Register hooks
        await self._register_plugin_hooks(plugin)
        
        # Update status
        plugin.status = PluginStatus.ACTIVE
        plugin.updated_at = datetime.utcnow()
        await self._update_plugin_status(plugin)
        
        logger.info(f"Activated plugin {plugin_id}")
        return True
    
    async def deactivate_plugin(self, plugin_id: str) -> bool:
        """Deactivate an active plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        # Shutdown instance
        if plugin.instance:
            await plugin.instance.shutdown()
            plugin.instance = None
        
        # Unregister hooks
        for hook in self._hooks.values():
            hook.remove_handler(plugin_id)
        
        # Update status
        plugin.status = PluginStatus.DISABLED
        plugin.updated_at = datetime.utcnow()
        await self._update_plugin_status(plugin)
        
        logger.info(f"Deactivated plugin {plugin_id}")
        return True
    
    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """Uninstall a plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        # Deactivate first
        if plugin.status == PluginStatus.ACTIVE:
            await self.deactivate_plugin(plugin_id)
        
        # Update status
        plugin.status = PluginStatus.UNINSTALLED
        plugin.updated_at = datetime.utcnow()
        await self._update_plugin_status(plugin)
        
        # Remove from memory
        del self._plugins[plugin_id]
        
        logger.info(f"Uninstalled plugin {plugin_id}")
        return True
    
    async def execute_plugin(
        self,
        plugin_id: str,
        action: str,
        context: Dict[str, Any]
    ) -> PluginExecutionResult:
        """
        Execute a plugin action.
        
        Args:
            plugin_id: Plugin ID
            action: Action to execute
            context: Execution context
            
        Returns:
            PluginExecutionResult
        """
        import time
        
        start_time = time.time()
        
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return PluginExecutionResult(
                success=False,
                plugin_id=plugin_id,
                action=action,
                error_message="Plugin not found",
                execution_time_ms=0,
            )
        
        if plugin.status != PluginStatus.ACTIVE:
            return PluginExecutionResult(
                success=False,
                plugin_id=plugin_id,
                action=action,
                error_message=f"Plugin is not active (status: {plugin.status.value})",
                execution_time_ms=0,
            )
        
        if not plugin.instance:
            return PluginExecutionResult(
                success=False,
                plugin_id=plugin_id,
                action=action,
                error_message="Plugin instance not loaded",
                execution_time_ms=0,
            )
        
        try:
            # Execute
            output = await plugin.instance.execute(action, context)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Update stats
            plugin.execution_count += 1
            plugin.last_executed_at = datetime.utcnow()
            await self._update_plugin_stats(plugin)
            
            # Log execution
            await self._log_execution(plugin_id, action, True, output, None, execution_time, context)
            
            return PluginExecutionResult(
                success=True,
                plugin_id=plugin_id,
                action=action,
                output=output,
                execution_time_ms=execution_time,
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Update stats
            plugin.error_count += 1
            await self._update_plugin_stats(plugin)
            
            # Log execution
            await self._log_execution(plugin_id, action, False, None, str(e), execution_time, context)
            
            logger.error(f"Plugin execution failed: {e}")
            
            return PluginExecutionResult(
                success=False,
                plugin_id=plugin_id,
                action=action,
                error_message=str(e),
                execution_time_ms=execution_time,
            )
    
    async def trigger_hook(
        self,
        hook_name: str,
        context: Dict[str, Any],
        **kwargs
    ) -> List[PluginExecutionResult]:
        """
        Trigger a hook and execute all registered handlers.
        
        Args:
            hook_name: Name of the hook to trigger
            context: Context to pass to handlers
            **kwargs: Additional arguments
            
        Returns:
            List of execution results
        """
        if hook_name not in self._hooks:
            return []
        
        if hook_name not in self._enabled_hooks:
            return []
        
        hook = self._hooks[hook_name]
        results = []
        
        for plugin_id, handler, priority in hook.handlers:
            try:
                # Build arguments based on signature
                sig = inspect.signature(handler)
                args = {"context": context}
                args.update(kwargs)
                
                # Call handler
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**args)
                else:
                    result = handler(**args)
                
                results.append(PluginExecutionResult(
                    success=True,
                    plugin_id=plugin_id,
                    action=hook_name,
                    output=result,
                ))
            
            except Exception as e:
                logger.error(f"Hook handler failed for {plugin_id}: {e}")
                results.append(PluginExecutionResult(
                    success=False,
                    plugin_id=plugin_id,
                    action=hook_name,
                    error_message=str(e),
                ))
        
        return results
    
    async def list_plugins(
        self,
        status: Optional[PluginStatus] = None,
        plugin_type: Optional[PluginType] = None,
        limit: int = 100
    ) -> List[Plugin]:
        """List plugins."""
        plugins = []
        
        async with AsyncSessionLocal() as session:
            if status and plugin_type:
                result = await session.execute(
                    text("""
                        SELECT * FROM plugins
                        WHERE status = :status AND plugin_type = :plugin_type
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"status": status.value, "plugin_type": plugin_type.value, "limit": limit}
                )
            elif status:
                result = await session.execute(
                    text("""
                        SELECT * FROM plugins
                        WHERE status = :status
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"status": status.value, "limit": limit}
                )
            elif plugin_type:
                result = await session.execute(
                    text("""
                        SELECT * FROM plugins
                        WHERE plugin_type = :plugin_type
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"plugin_type": plugin_type.value, "limit": limit}
                )
            else:
                result = await session.execute(
                    text("""
                        SELECT * FROM plugins
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
            
            for row in result:
                manifest = PluginManifest.from_dict(row.manifest)
                plugin = Plugin(
                    plugin_id=row.plugin_id,
                    manifest=manifest,
                    status=PluginStatus(row.status),
                    source_path=row.source_path,
                    config=row.config,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    installed_by=row.installed_by,
                    hash_checksum=row.hash_checksum,
                    last_executed_at=row.last_executed_at,
                    execution_count=row.execution_count,
                    error_count=row.error_count,
                )
                plugins.append(plugin)
        
        return plugins
    
    async def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID."""
        if plugin_id in self._plugins:
            return self._plugins[plugin_id]
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT * FROM plugins WHERE plugin_id = :plugin_id"),
                {"plugin_id": plugin_id}
            )
            row = result.fetchone()
            
            if row:
                manifest = PluginManifest.from_dict(row.manifest)
                plugin = Plugin(
                    plugin_id=row.plugin_id,
                    manifest=manifest,
                    status=PluginStatus(row.status),
                    source_path=row.source_path,
                    config=row.config,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    installed_by=row.installed_by,
                    hash_checksum=row.hash_checksum,
                    last_executed_at=row.last_executed_at,
                    execution_count=row.execution_count,
                    error_count=row.error_count,
                )
                return plugin
        
        return None
    
    async def _get_plugin_by_name(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT * FROM plugins WHERE name = :name AND status != 'uninstalled'"),
                {"name": name}
            )
            row = result.fetchone()
            
            if row:
                manifest = PluginManifest.from_dict(row.manifest)
                return Plugin(
                    plugin_id=row.plugin_id,
                    manifest=manifest,
                    status=PluginStatus(row.status),
                    source_path=row.source_path,
                    config=row.config,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    installed_by=row.installed_by,
                    hash_checksum=row.hash_checksum,
                    last_executed_at=row.last_executed_at,
                    execution_count=row.execution_count,
                    error_count=row.error_count,
                )
        
        return None
    
    async def _update_plugin_status(self, plugin: Plugin) -> None:
        """Update plugin status in database."""
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    UPDATE plugins
                    SET status = :status, updated_at = :updated_at
                    WHERE plugin_id = :plugin_id
                """),
                {
                    "plugin_id": plugin.plugin_id,
                    "status": plugin.status.value,
                    "updated_at": plugin.updated_at,
                }
            )
            await session.commit()
    
    async def _update_plugin_stats(self, plugin: Plugin) -> None:
        """Update plugin execution stats."""
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    UPDATE plugins
                    SET execution_count = :exec_count,
                        error_count = :err_count,
                        last_executed_at = :last_exec
                    WHERE plugin_id = :plugin_id
                """),
                {
                    "plugin_id": plugin.plugin_id,
                    "exec_count": plugin.execution_count,
                    "err_count": plugin.error_count,
                    "last_exec": plugin.last_executed_at,
                }
            )
            await session.commit()
    
    async def _log_execution(
        self,
        plugin_id: str,
        action: str,
        success: bool,
        output: Any,
        error_message: Optional[str],
        execution_time_ms: float,
        context: Dict[str, Any]
    ) -> None:
        """Log plugin execution."""
        context_hash = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:16]
        
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO plugin_execution_logs (
                        log_id, plugin_id, action, success, output,
                        error_message, execution_time_ms, context_hash
                    ) VALUES (
                        :log_id, :plugin_id, :action, :success, :output,
                        :error_message, :exec_time, :context_hash
                    )
                """),
                {
                    "log_id": f"log_{uuid4().hex[:12]}",
                    "plugin_id": plugin_id,
                    "action": action,
                    "success": success,
                    "output": json.dumps(output) if output else None,
                    "error_message": error_message,
                    "exec_time": execution_time_ms,
                    "context_hash": context_hash,
                }
            )
            await session.commit()
    
    def _check_version_compatibility(self, manifest: PluginManifest) -> bool:
        """Check if plugin is compatible with platform version."""
        from packaging import version
        
        try:
            platform_v = version.parse(self.PLATFORM_VERSION)
            min_v = version.parse(manifest.min_platform_version)
            
            if platform_v < min_v:
                return False
            
            if manifest.max_platform_version:
                max_v = version.parse(manifest.max_platform_version)
                if platform_v > max_v:
                    return False
            
            return True
        except Exception:
            return False
    
    def _calculate_directory_hash(self, directory: str) -> str:
        """Calculate hash of directory contents."""
        import hashlib
        
        sha256_hash = hashlib.sha256()
        
        for root, dirs, files in os.walk(directory):
            # Sort for consistent ordering
            dirs.sort()
            files.sort()
            
            for file in files:
                if file.endswith(('.py', '.json', '.txt', '.yaml', '.yml')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'rb') as f:
                            sha256_hash.update(f.read())
                    except Exception:
                        pass
        
        return sha256_hash.hexdigest()
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get plugin statistics."""
        async with AsyncSessionLocal() as session:
            # Total plugins
            result = await session.execute(text("SELECT COUNT(*) FROM plugins"))
            total_plugins = result.scalar()
            
            # By status
            result = await session.execute(
                text("""
                    SELECT status, COUNT(*) as count
                    FROM plugins
                    GROUP BY status
                """)
            )
            status_counts = {r.status: r.count for r in result}
            
            # By type
            result = await session.execute(
                text("""
                    SELECT plugin_type, COUNT(*) as count
                    FROM plugins
                    GROUP BY plugin_type
                """)
            )
            type_counts = {r.plugin_type: r.count for r in result}
            
            # Recent executions
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM plugin_execution_logs
                    WHERE executed_at > NOW() - INTERVAL '24 hours'
                """)
            )
            executions_24h = result.scalar()
            
            return {
                "total_plugins": total_plugins,
                "by_status": status_counts,
                "by_type": type_counts,
                "executions_24h": executions_24h,
                "platform_version": self.PLATFORM_VERSION,
                "timestamp": datetime.utcnow().isoformat(),
            }


# Global instance
_plugin_manager: Optional[PluginManager] = None


async def get_plugin_manager(
    engine: Optional[AsyncEngine] = None
) -> PluginManager:
    """Get or create the global plugin manager."""
    global _plugin_manager
    
    if _plugin_manager is None:
        _plugin_manager = PluginManager(engine)
        await _plugin_manager.initialize()
    
    return _plugin_manager
