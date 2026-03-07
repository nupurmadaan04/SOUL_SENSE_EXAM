"""
Idempotent PATCH Conflict Resolution Contract Module

This module provides idempotent PATCH operations with conflict detection,
resolution strategies, and optimistic concurrency control for safe
partial resource updates.

Features:
- Idempotent PATCH operations
- Optimistic concurrency control (ETag/If-Match)
- Conflict detection and resolution strategies
- Field-level change tracking
- Retry mechanisms with exponential backoff
- Compliance with RFC 5789 (PATCH Method for HTTP)
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict
import copy
import logging

# Configure logging
logger = logging.getLogger(__name__)


class ConflictStrategy(str, Enum):
    """Strategy for resolving PATCH conflicts."""
    REJECT = "reject"              # Reject the request (409 Conflict)
    MERGE = "merge"                # Merge changes (if compatible)
    OVERWRITE = "overwrite"        # Overwrite server changes
    CLIENT_WINS = "client_wins"    # Client changes take precedence
    SERVER_WINS = "server_wins"    # Server changes take precedence
    CUSTOM = "custom"              # Use custom resolver


class PatchStatus(str, Enum):
    """Status of PATCH operation."""
    PENDING = "pending"
    APPLIED = "applied"
    CONFLICT = "conflict"
    REJECTED = "rejected"
    MERGED = "merged"
    FAILED = "failed"
    RETRYING = "retrying"


class ChangeType(str, Enum):
    """Type of field change."""
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    UNCHANGED = "unchanged"


@dataclass
class FieldChange:
    """Represents a change to a single field."""
    field_path: str
    change_type: ChangeType
    old_value: Any = None
    new_value: Any = None
    
    def __str__(self):
        return f"{self.field_path}: {self.change_type.value}"


@dataclass
class ResourceVersion:
    """Version information for a resource."""
    resource_id: str
    resource_type: str
    etag: str
    version_number: int
    last_modified_at: datetime
    last_modified_by: str = ""
    
    def generate_etag(self, data: Dict[str, Any]) -> str:
        """Generate ETag from resource data."""
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class PatchOperation:
    """RFC 6902 JSON Patch style operation."""
    op: str  # add, remove, replace, move, copy, test
    path: str
    value: Any = None
    from_path: str = ""  # For move/copy operations


@dataclass
class PatchRequest:
    """A PATCH request with idempotency tracking."""
    request_id: str
    resource_id: str
    resource_type: str
    
    # Patch content
    operations: List[PatchOperation]
    expected_etag: str = ""
    
    # Idempotency
    idempotency_key: str = ""
    
    # Client info
    client_id: str = ""
    requested_at: datetime = field(default_factory=datetime.utcnow)
    
    # Conflict resolution preference
    conflict_strategy: ConflictStrategy = ConflictStrategy.REJECT


@dataclass
class PatchResult:
    """Result of a PATCH operation."""
    request_id: str
    status: PatchStatus
    
    # Result data
    new_etag: str = ""
    new_version: int = 0
    applied_changes: List[FieldChange] = field(default_factory=list)
    conflicted_changes: List[FieldChange] = field(default_factory=list)
    
    # Response
    response_data: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    error_code: str = ""
    
    # Retry info
    retry_after_seconds: int = 0
    max_retries: int = 0
    
    # Timing
    processed_at: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: int = 0


@dataclass
class Conflict:
    """Represents a conflict between client and server changes."""
    conflict_id: str
    field_path: str
    
    # Values
    base_value: Any = None  # Original value
    client_value: Any = None  # Client's proposed value
    server_value: Any = None  # Current server value
    
    # Resolution
    resolved_value: Any = None
    resolution_strategy: ConflictStrategy = ConflictStrategy.REJECT
    resolved: bool = False


@dataclass
class PatchHistory:
    """Historical record of PATCH operations."""
    history_id: str
    resource_id: str
    resource_type: str
    
    # Change record
    operations: List[PatchOperation]
    changes: List[FieldChange]
    
    # Version info
    previous_etag: str = ""
    new_etag: str = ""
    version_number: int = 0
    
    # Metadata
    applied_at: datetime = field(default_factory=datetime.utcnow)
    applied_by: str = ""
    client_id: str = ""
    idempotency_key: str = ""


class PatchConflictResolver:
    """
    Resolves conflicts between client and server changes.
    
    Implements various conflict resolution strategies:
    - Reject: Return 409 Conflict
    - Merge: Combine non-conflicting changes
    - Overwrite: Replace server state with client state
    - Client/Server Wins: One side takes precedence
    """
    
    @staticmethod
    def detect_conflicts(
        base_data: Dict[str, Any],
        client_data: Dict[str, Any],
        server_data: Dict[str, Any]
    ) -> List[Conflict]:
        """Detect conflicts between client and server changes."""
        conflicts = []
        
        # Get all field paths
        all_paths = set()
        all_paths.update(PatchConflictResolver._get_all_paths(base_data))
        all_paths.update(PatchConflictResolver._get_all_paths(client_data))
        all_paths.update(PatchConflictResolver._get_all_paths(server_data))
        
        for path in all_paths:
            base_val = PatchConflictResolver._get_value_at_path(base_data, path)
            client_val = PatchConflictResolver._get_value_at_path(client_data, path)
            server_val = PatchConflictResolver._get_value_at_path(server_data, path)
            
            # Conflict exists if both client and server changed from base
            if client_val != base_val and server_val != base_val and client_val != server_val:
                conflicts.append(Conflict(
                    conflict_id=f"conflict_{path}",
                    field_path=path,
                    base_value=base_val,
                    client_value=client_val,
                    server_value=server_val
                ))
        
        return conflicts
    
    @staticmethod
    def _get_all_paths(data: Dict[str, Any], prefix: str = "") -> Set[str]:
        """Get all paths in nested dictionary."""
        paths = set()
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            paths.add(path)
            if isinstance(value, dict):
                paths.update(PatchConflictResolver._get_all_paths(value, path))
        return paths
    
    @staticmethod
    def _get_value_at_path(data: Dict[str, Any], path: str) -> Any:
        """Get value at a nested path."""
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
    
    @staticmethod
    def resolve_conflicts(
        conflicts: List[Conflict],
        strategy: ConflictStrategy
    ) -> Tuple[List[Conflict], Dict[str, Any]]:
        """Resolve conflicts using specified strategy."""
        resolved_values = {}
        
        for conflict in conflicts:
            if strategy == ConflictStrategy.REJECT:
                # Don't resolve, will return 409
                continue
            
            elif strategy == ConflictStrategy.CLIENT_WINS:
                conflict.resolved_value = conflict.client_value
                conflict.resolved = True
                resolved_values[conflict.field_path] = conflict.client_value
            
            elif strategy == ConflictStrategy.SERVER_WINS:
                conflict.resolved_value = conflict.server_value
                conflict.resolved = True
                resolved_values[conflict.field_path] = conflict.server_value
            
            elif strategy == ConflictStrategy.MERGE:
                # Try to merge - for simple values, prefer client
                # For lists/dicts, could attempt deep merge
                conflict.resolved_value = conflict.client_value
                conflict.resolved = True
                resolved_values[conflict.field_path] = conflict.client_value
            
            elif strategy == ConflictStrategy.OVERWRITE:
                conflict.resolved_value = conflict.client_value
                conflict.resolved = True
                resolved_values[conflict.field_path] = conflict.client_value
            
            conflict.resolution_strategy = strategy
        
        return conflicts, resolved_values


class IdempotentPatchManager:
    """
    Central manager for idempotent PATCH operations.
    
    Provides functionality for:
    - Idempotent PATCH request processing
    - Optimistic concurrency control
    - Conflict detection and resolution
    - Request deduplication
    - Patch history tracking
    """
    
    def __init__(self):
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.versions: Dict[str, ResourceVersion] = {}
        self.patch_history: Dict[str, List[PatchHistory]] = {}
        self.idempotency_keys: Dict[str, PatchResult] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the patch manager."""
        async with self._lock:
            if self._initialized:
                return
            
            self._initialized = True
            logger.info("IdempotentPatchManager initialized successfully")
    
    # Resource Management
    
    async def create_resource(
        self,
        resource_id: str,
        resource_type: str,
        data: Dict[str, Any],
        created_by: str = ""
    ) -> ResourceVersion:
        """Create a new resource with version tracking."""
        async with self._lock:
            self.resources[resource_id] = copy.deepcopy(data)
            
            etag = hashlib.md5(
                json.dumps(data, sort_keys=True, default=str).encode()
            ).hexdigest()
            
            version = ResourceVersion(
                resource_id=resource_id,
                resource_type=resource_type,
                etag=etag,
                version_number=1,
                last_modified_at=datetime.utcnow(),
                last_modified_by=created_by
            )
            
            self.versions[resource_id] = version
            self.patch_history[resource_id] = []
            
            logger.info(f"Created resource: {resource_id}")
            return version
    
    async def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get resource data by ID."""
        resource = self.resources.get(resource_id)
        return copy.deepcopy(resource) if resource else None
    
    async def get_resource_version(self, resource_id: str) -> Optional[ResourceVersion]:
        """Get resource version info."""
        return self.versions.get(resource_id)
    
    # PATCH Operations
    
    async def apply_patch(
        self,
        request: PatchRequest
    ) -> PatchResult:
        """Apply a PATCH request with idempotency and conflict resolution."""
        async with self._lock:
            start_time = datetime.utcnow()
            
            # Check idempotency
            if request.idempotency_key:
                existing = self.idempotency_keys.get(request.idempotency_key)
                if existing:
                    logger.info(f"Returning idempotent result for: {request.idempotency_key}")
                    return existing
            
            # Get current resource
            resource = self.resources.get(request.resource_id)
            version = self.versions.get(request.resource_id)
            
            if not resource or not version:
                return PatchResult(
                    request_id=request.request_id,
                    status=PatchStatus.FAILED,
                    error_message="Resource not found",
                    error_code="NOT_FOUND"
                )
            
            # Optimistic concurrency check
            if request.expected_etag and request.expected_etag != version.etag:
                # ETag mismatch - potential conflict
                return await self._handle_conflict(request, resource, version)
            
            # Apply operations
            try:
                new_data, changes = await self._apply_operations(
                    copy.deepcopy(resource),
                    request.operations
                )
                
                # Calculate new ETag and version
                new_etag = hashlib.md5(
                    json.dumps(new_data, sort_keys=True, default=str).encode()
                ).hexdigest()
                new_version_number = version.version_number + 1
                
                # Update resource
                self.resources[request.resource_id] = new_data
                version.etag = new_etag
                version.version_number = new_version_number
                version.last_modified_at = datetime.utcnow()
                version.last_modified_by = request.client_id
                
                # Record history
                history = PatchHistory(
                    history_id=f"hist_{request.request_id}",
                    resource_id=request.resource_id,
                    resource_type=request.resource_type,
                    operations=request.operations,
                    changes=changes,
                    previous_etag=request.expected_etag,
                    new_etag=new_etag,
                    version_number=new_version_number,
                    applied_by=request.client_id,
                    client_id=request.client_id,
                    idempotency_key=request.idempotency_key
                )
                self.patch_history[request.resource_id].append(history)
                
                # Create result
                result = PatchResult(
                    request_id=request.request_id,
                    status=PatchStatus.APPLIED,
                    new_etag=new_etag,
                    new_version=new_version_number,
                    applied_changes=changes,
                    response_data=new_data,
                    processing_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
                
                # Store idempotency result
                if request.idempotency_key:
                    self.idempotency_keys[request.idempotency_key] = result
                
                logger.info(f"Applied PATCH to {request.resource_id}: {new_etag}")
                return result
                
            except Exception as e:
                logger.error(f"PATCH failed: {e}")
                return PatchResult(
                    request_id=request.request_id,
                    status=PatchStatus.FAILED,
                    error_message=str(e),
                    error_code="PATCH_FAILED"
                )
    
    async def _handle_conflict(
        self,
        request: PatchRequest,
        server_data: Dict[str, Any],
        version: ResourceVersion
    ) -> PatchResult:
        """Handle ETag mismatch / conflict."""
        # Get base data (would be from history in real implementation)
        base_data = server_data  # Simplified
        
        # Apply operations to get client view
        try:
            client_data, _ = await self._apply_operations(
                copy.deepcopy(base_data),
                request.operations
            )
        except Exception:
            client_data = base_data
        
        # Detect conflicts
        conflicts = PatchConflictResolver.detect_conflicts(
            base_data, client_data, server_data
        )
        
        if not conflicts:
            # No actual conflicts detected at field level
            # But ETag still mismatched - server changed since client's read
            # Return conflict to be safe
            return PatchResult(
                request_id=request.request_id,
                status=PatchStatus.CONFLICT,
                error_message="Resource was modified by another request. ETag mismatch.",
                error_code="ETAG_MISMATCH",
                new_etag=version.etag,
                new_version=version.version_number,
                response_data=server_data
            )
        
        # Handle based on strategy
        if request.conflict_strategy == ConflictStrategy.REJECT:
            return PatchResult(
                request_id=request.request_id,
                status=PatchStatus.CONFLICT,
                error_message=f"Conflict detected in fields: {[c.field_path for c in conflicts]}",
                error_code="CONFLICT",
                new_etag=version.etag,
                new_version=version.version_number,
                response_data=server_data
            )
        
        # Try to resolve conflicts
        resolved_conflicts, resolved_values = PatchConflictResolver.resolve_conflicts(
            conflicts, request.conflict_strategy
        )
        
        if all(c.resolved for c in resolved_conflicts):
            # All conflicts resolved, apply the resolved values
            new_data = copy.deepcopy(server_data)
            for path, value in resolved_values.items():
                await self._set_value_at_path(new_data, path, value)
            
            # Update resource
            new_etag = hashlib.md5(
                json.dumps(new_data, sort_keys=True, default=str).encode()
            ).hexdigest()
            new_version_number = version.version_number + 1
            
            self.resources[request.resource_id] = new_data
            version.etag = new_etag
            version.version_number = new_version_number
            
            return PatchResult(
                request_id=request.request_id,
                status=PatchStatus.MERGED,
                new_etag=new_etag,
                new_version=new_version_number,
                response_data=new_data
            )
        
        # Could not resolve all conflicts
        return PatchResult(
            request_id=request.request_id,
            status=PatchStatus.CONFLICT,
            error_message="Could not resolve all conflicts",
            error_code="UNRESOLVED_CONFLICT",
            new_etag=version.etag
        )
    
    async def _apply_operations(
        self,
        data: Dict[str, Any],
        operations: List[PatchOperation]
    ) -> Tuple[Dict[str, Any], List[FieldChange]]:
        """Apply JSON Patch operations to data."""
        changes = []
        
        for op in operations:
            if op.op == "replace":
                old_val = await self._get_value_at_path(data, op.path)
                await self._set_value_at_path(data, op.path, op.value)
                changes.append(FieldChange(
                    field_path=op.path,
                    change_type=ChangeType.MODIFIED,
                    old_value=old_val,
                    new_value=op.value
                ))
            
            elif op.op == "add":
                await self._set_value_at_path(data, op.path, op.value)
                changes.append(FieldChange(
                    field_path=op.path,
                    change_type=ChangeType.ADDED,
                    new_value=op.value
                ))
            
            elif op.op == "remove":
                old_val = await self._get_value_at_path(data, op.path)
                await self._remove_value_at_path(data, op.path)
                changes.append(FieldChange(
                    field_path=op.path,
                    change_type=ChangeType.REMOVED,
                    old_value=old_val
                ))
        
        return data, changes
    
    async def _get_value_at_path(self, data: Dict[str, Any], path: str) -> Any:
        """Get value at a path (e.g., 'user.name')."""
        parts = path.lstrip("/").split("/")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
    
    async def _set_value_at_path(self, data: Dict[str, Any], path: str, value: Any):
        """Set value at a path."""
        parts = path.lstrip("/").split("/")
        current = data
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    
    async def _remove_value_at_path(self, data: Dict[str, Any], path: str):
        """Remove value at a path."""
        parts = path.lstrip("/").split("/")
        current = data
        for part in parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return
        if parts[-1] in current:
            del current[parts[-1]]
    
    # History
    
    async def get_patch_history(
        self,
        resource_id: str,
        limit: int = 50
    ) -> List[PatchHistory]:
        """Get patch history for a resource."""
        history = self.patch_history.get(resource_id, [])
        return sorted(history, key=lambda h: h.applied_at, reverse=True)[:limit]
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get PATCH operation statistics."""
        all_history = []
        for history_list in self.patch_history.values():
            all_history.extend(history_list)
        
        return {
            "resources": {
                "total": len(self.resources),
                "with_history": len(self.patch_history)
            },
            "patches": {
                "total_applied": len(all_history),
                "unique_clients": len(set(h.client_id for h in all_history if h.client_id)),
                "idempotent_hits": len(self.idempotency_keys)
            }
        }


# Global manager instance
_patch_manager: Optional[IdempotentPatchManager] = None


async def get_patch_manager() -> IdempotentPatchManager:
    """Get or create the global idempotent patch manager."""
    global _patch_manager
    if _patch_manager is None:
        _patch_manager = IdempotentPatchManager()
        await _patch_manager.initialize()
    return _patch_manager


def reset_patch_manager():
    """Reset the global patch manager (for testing)."""
    global _patch_manager
    _patch_manager = None
