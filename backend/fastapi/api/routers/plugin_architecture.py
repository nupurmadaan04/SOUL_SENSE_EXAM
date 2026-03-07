"""
Plugin Architecture API Router (#1441)

REST API endpoints for managing assessment plugins.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.db_service import get_db
from ..utils.plugin_architecture import (
    get_plugin_manager,
    PluginManager,
    PluginManifest,
    Plugin,
    PluginStatus,
    PluginType,
    HookPriority,
    BasePlugin,
)
from .auth import require_admin, get_current_user


router = APIRouter(tags=["Plugin Architecture"], prefix="/plugins")


# --- Pydantic Schemas ---

class PluginManifestRequest(BaseModel):
    """Schema for plugin manifest."""
    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    plugin_type: PluginType = Field(..., description="Type of plugin")
    entry_point: str = Field(..., description="Entry point (module:class)")
    description: Optional[str] = Field(None)
    author: Optional[str] = Field(None)
    license: Optional[str] = Field(None)
    homepage: Optional[str] = Field(None)
    repository: Optional[str] = Field(None)
    requirements: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    hooks: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    min_platform_version: str = Field(default="1.0.0")
    max_platform_version: Optional[str] = Field(None)


class PluginRegisterRequest(BaseModel):
    """Schema for registering a plugin."""
    manifest: PluginManifestRequest
    source_path: Optional[str] = Field(None)
    config: Dict[str, Any] = Field(default_factory=dict)


class PluginResponse(BaseModel):
    """Schema for plugin response."""
    plugin_id: str
    manifest: Dict[str, Any]
    status: str
    source_path: Optional[str]
    config: Dict[str, Any]
    created_at: str
    updated_at: str
    installed_by: Optional[str]
    hash_checksum: Optional[str]
    last_executed_at: Optional[str]
    execution_count: int
    error_count: int


class PluginExecuteRequest(BaseModel):
    """Schema for plugin execution."""
    action: str = Field(..., description="Action to execute")
    context: Dict[str, Any] = Field(default_factory=dict)


class PluginExecutionResponse(BaseModel):
    """Schema for plugin execution result."""
    success: bool
    plugin_id: str
    action: str
    output: Optional[Any]
    error_message: Optional[str]
    execution_time_ms: float
    timestamp: str


class HookResponse(BaseModel):
    """Schema for hook response."""
    hook_name: str
    description: Optional[str]
    signature: str
    handler_count: int


class TriggerHookRequest(BaseModel):
    """Schema for triggering a hook."""
    context: Dict[str, Any] = Field(default_factory=dict)
    additional_args: Dict[str, Any] = Field(default_factory=dict)


class PluginStatisticsResponse(BaseModel):
    """Schema for plugin statistics."""
    total_plugins: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    executions_24h: int
    platform_version: str
    timestamp: str


# --- API Endpoints ---

@router.post(
    "/register",
    response_model=PluginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register plugin",
    description="Registers a new assessment plugin."
)
async def register_plugin(
    request: PluginRegisterRequest,
    current_user: Any = Depends(require_admin)
) -> PluginResponse:
    """Register a new plugin."""
    manager = await get_plugin_manager()
    
    manifest = PluginManifest(
        name=request.manifest.name,
        version=request.manifest.version,
        plugin_type=request.manifest.plugin_type,
        entry_point=request.manifest.entry_point,
        description=request.manifest.description,
        author=request.manifest.author,
        license=request.manifest.license,
        homepage=request.manifest.homepage,
        repository=request.manifest.repository,
        requirements=request.manifest.requirements,
        dependencies=request.manifest.dependencies,
        config_schema=request.manifest.config_schema,
        hooks=request.manifest.hooks,
        permissions=request.manifest.permissions,
        min_platform_version=request.manifest.min_platform_version,
        max_platform_version=request.manifest.max_platform_version,
    )
    
    plugin = await manager.register_plugin(
        manifest=manifest,
        source_path=request.source_path,
        config=request.config,
        installed_by=getattr(current_user, 'id', None) if current_user else None,
    )
    
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to register plugin"
        )
    
    return PluginResponse(**plugin.to_dict())


@router.post(
    "/register-from-directory",
    response_model=PluginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register plugin from directory",
    description="Registers a plugin from a local directory."
)
async def register_plugin_from_directory(
    directory: str = Form(..., description="Path to plugin directory"),
    config: str = Form(default="{}", description="JSON configuration"),
    current_user: Any = Depends(require_admin)
) -> PluginResponse:
    """Register a plugin from a directory."""
    manager = await get_plugin_manager()
    
    import json
    config_dict = json.loads(config)
    
    plugin = await manager.register_plugin_from_directory(
        directory=directory,
        config=config_dict,
        installed_by=getattr(current_user, 'id', None) if current_user else None,
    )
    
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to register plugin from directory"
        )
    
    return PluginResponse(**plugin.to_dict())


@router.get(
    "",
    response_model=List[PluginResponse],
    summary="List plugins",
    description="Returns list of registered plugins."
)
async def list_plugins(
    status: Optional[PluginStatus] = Query(None, description="Filter by status"),
    plugin_type: Optional[PluginType] = Query(None, description="Filter by type"),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: Any = Depends(require_admin)
) -> List[PluginResponse]:
    """List plugins."""
    manager = await get_plugin_manager()
    plugins = await manager.list_plugins(status=status, plugin_type=plugin_type, limit=limit)
    return [PluginResponse(**p.to_dict()) for p in plugins]


@router.get(
    "/{plugin_id}",
    response_model=PluginResponse,
    summary="Get plugin details",
    description="Returns details for a specific plugin."
)
async def get_plugin(
    plugin_id: str,
    current_user: Any = Depends(require_admin)
) -> PluginResponse:
    """Get plugin details."""
    manager = await get_plugin_manager()
    plugin = await manager.get_plugin(plugin_id)
    
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin {plugin_id} not found"
        )
    
    return PluginResponse(**plugin.to_dict())


@router.post(
    "/{plugin_id}/activate",
    response_model=PluginResponse,
    summary="Activate plugin",
    description="Activates a pending plugin."
)
async def activate_plugin(
    plugin_id: str,
    current_user: Any = Depends(require_admin)
) -> PluginResponse:
    """Activate a plugin."""
    manager = await get_plugin_manager()
    
    success = await manager.activate_plugin(plugin_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to activate plugin {plugin_id}"
        )
    
    plugin = await manager.get_plugin(plugin_id)
    return PluginResponse(**plugin.to_dict())


@router.post(
    "/{plugin_id}/deactivate",
    response_model=PluginResponse,
    summary="Deactivate plugin",
    description="Deactivates an active plugin."
)
async def deactivate_plugin(
    plugin_id: str,
    current_user: Any = Depends(require_admin)
) -> PluginResponse:
    """Deactivate a plugin."""
    manager = await get_plugin_manager()
    
    success = await manager.deactivate_plugin(plugin_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to deactivate plugin {plugin_id}"
        )
    
    plugin = await manager.get_plugin(plugin_id)
    return PluginResponse(**plugin.to_dict())


@router.post(
    "/{plugin_id}/execute",
    response_model=PluginExecutionResponse,
    summary="Execute plugin",
    description="Executes a plugin action."
)
async def execute_plugin(
    plugin_id: str,
    request: PluginExecuteRequest,
    current_user: Any = Depends(require_admin)
) -> PluginExecutionResponse:
    """Execute a plugin."""
    manager = await get_plugin_manager()
    
    result = await manager.execute_plugin(
        plugin_id=plugin_id,
        action=request.action,
        context=request.context,
    )
    
    return PluginExecutionResponse(**result.to_dict())


@router.post(
    "/{plugin_id}/uninstall",
    status_code=status.HTTP_200_OK,
    summary="Uninstall plugin",
    description="Uninstalls a plugin."
)
async def uninstall_plugin(
    plugin_id: str,
    current_user: Any = Depends(require_admin)
) -> Dict[str, str]:
    """Uninstall a plugin."""
    manager = await get_plugin_manager()
    
    success = await manager.uninstall_plugin(plugin_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin {plugin_id} not found"
        )
    
    return {"status": "uninstalled", "plugin_id": plugin_id}


@router.get(
    "/hooks/available",
    response_model=List[HookResponse],
    summary="List available hooks",
    description="Returns list of available hooks."
)
async def list_hooks(
    current_user: Any = Depends(require_admin)
) -> List[HookResponse]:
    """List available hooks."""
    manager = await get_plugin_manager()
    
    hooks = []
    for hook_name, hook in manager._hooks.items():
        hooks.append(HookResponse(
            hook_name=hook_name,
            description=hook.description,
            signature=hook.signature,
            handler_count=len(hook.handlers),
        ))
    
    return hooks


@router.post(
    "/hooks/{hook_name}/trigger",
    response_model=List[PluginExecutionResponse],
    summary="Trigger hook",
    description="Triggers a hook and executes all registered handlers."
)
async def trigger_hook(
    hook_name: str,
    request: TriggerHookRequest,
    current_user: Any = Depends(require_admin)
) -> List[PluginExecutionResponse]:
    """Trigger a hook."""
    manager = await get_plugin_manager()
    
    if hook_name not in manager._hooks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hook {hook_name} not found"
        )
    
    results = await manager.trigger_hook(
        hook_name=hook_name,
        context=request.context,
        **request.additional_args
    )
    
    return [PluginExecutionResponse(**r.to_dict()) for r in results]


@router.get(
    "/statistics/global",
    response_model=PluginStatisticsResponse,
    summary="Get statistics",
    description="Returns global plugin statistics."
)
async def get_statistics(
    current_user: Any = Depends(require_admin)
) -> PluginStatisticsResponse:
    """Get plugin statistics."""
    manager = await get_plugin_manager()
    stats = await manager.get_statistics()
    return PluginStatisticsResponse(**stats)


@router.get(
    "/types/list",
    response_model=List[Dict[str, str]],
    summary="List plugin types",
    description="Returns available plugin types."
)
async def list_plugin_types(
    current_user: Any = Depends(get_current_user)
) -> List[Dict[str, str]]:
    """List plugin types."""
    return [
        {"value": t.value, "name": t.name.replace("_", " ").title()}
        for t in PluginType
    ]


@router.post(
    "/initialize",
    status_code=status.HTTP_200_OK,
    summary="Initialize manager",
    description="Initializes the plugin manager."
)
async def initialize_manager(
    current_user: Any = Depends(require_admin)
) -> Dict[str, str]:
    """Initialize plugin manager."""
    manager = await get_plugin_manager()
    await manager.initialize()
    return {"status": "initialized"}
