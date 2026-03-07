"""
Partner API Sandbox Environment (#1443)

Provides a safe, isolated sandbox environment for partner API integration testing.
Allows partners to test their integrations without affecting production data.

Features:
- Mock API responses with configurable latency
- Request/response logging and replay
- Sandbox API key management
- Usage quotas and rate limiting
- Scenario simulation (success, error, timeout, rate-limit)
- Webhook testing endpoints
- Comprehensive audit logging

Example:
    from api.utils.partner_sandbox import PartnerSandboxManager, SandboxScenario
    
    manager = PartnerSandboxManager()
    await manager.initialize()
    
    # Create sandbox environment for partner
    sandbox = await manager.create_sandbox(
        partner_id="partner_001",
        config=SandboxConfig(
            latency_ms=100,
            scenario=SandboxScenario.SUCCESS,
            quota_daily=1000
        )
    )
"""

import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Tuple
from collections import defaultdict
import hashlib
import uuid

from sqlalchemy import text, select, func, Column, String, DateTime, Integer, Boolean, Text, JSON, Float
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import declarative_base

from ..services.db_service import AsyncSessionLocal, engine


logger = logging.getLogger("api.partner_sandbox")

Base = declarative_base()


class SandboxScenario(str, Enum):
    """Sandbox response scenarios."""
    SUCCESS = "success"  # Normal successful responses
    ERROR = "error"  # Simulated errors
    TIMEOUT = "timeout"  # Simulated timeouts
    RATE_LIMIT = "rate_limit"  # Simulated rate limiting
    DEGRADED = "degraded"  # Slow responses (high latency)
    MIXED = "mixed"  # Random mix of scenarios
    CUSTOM = "custom"  # Custom response handler


class SandboxStatus(str, Enum):
    """Status of a sandbox environment."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    DELETED = "deleted"


class WebhookDeliveryStatus(str, Enum):
    """Status of webhook delivery."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class SandboxConfig:
    """Configuration for a sandbox environment."""
    latency_ms: int = 100  # Simulated latency
    scenario: SandboxScenario = SandboxScenario.SUCCESS
    quota_daily: int = 1000  # Daily request quota
    quota_hourly: int = 100  # Hourly request quota
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    custom_responses: Dict[str, Any] = field(default_factory=dict)
    allowed_endpoints: List[str] = field(default_factory=lambda: ["*"])
    blocked_endpoints: List[str] = field(default_factory=list)
    enable_logging: bool = True
    log_retention_days: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "latency_ms": self.latency_ms,
            "scenario": self.scenario.value,
            "quota_daily": self.quota_daily,
            "quota_hourly": self.quota_hourly,
            "webhook_url": self.webhook_url,
            "allowed_endpoints": self.allowed_endpoints,
            "blocked_endpoints": self.blocked_endpoints,
            "enable_logging": self.enable_logging,
            "log_retention_days": self.log_retention_days,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SandboxConfig":
        return cls(
            latency_ms=data.get("latency_ms", 100),
            scenario=SandboxScenario(data.get("scenario", "success")),
            quota_daily=data.get("quota_daily", 1000),
            quota_hourly=data.get("quota_hourly", 100),
            webhook_url=data.get("webhook_url"),
            custom_responses=data.get("custom_responses", {}),
            allowed_endpoints=data.get("allowed_endpoints", ["*"]),
            blocked_endpoints=data.get("blocked_endpoints", []),
            enable_logging=data.get("enable_logging", True),
            log_retention_days=data.get("log_retention_days", 30),
        )


@dataclass
class SandboxApiKey:
    """API key for sandbox access."""
    key_id: str
    key_secret: str  # Hashed
    partner_id: str
    sandbox_id: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    is_revoked: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "partner_id": self.partner_id,
            "sandbox_id": self.sandbox_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count,
            "is_revoked": self.is_revoked,
        }


@dataclass
class SandboxRequestLog:
    """Log entry for a sandbox API request."""
    log_id: str
    sandbox_id: str
    partner_id: str
    timestamp: datetime
    method: str
    path: str
    headers: Dict[str, str]
    body: Optional[str]
    response_status: int
    response_body: Optional[str]
    latency_ms: float
    scenario: SandboxScenario
    client_ip: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "sandbox_id": self.sandbox_id,
            "partner_id": self.partner_id,
            "timestamp": self.timestamp.isoformat(),
            "method": self.method,
            "path": self.path,
            "response_status": self.response_status,
            "latency_ms": round(self.latency_ms, 2),
            "scenario": self.scenario.value,
        }


@dataclass
class WebhookEvent:
    """Webhook event for sandbox testing."""
    event_id: str
    sandbox_id: str
    partner_id: str
    event_type: str
    payload: Dict[str, Any]
    created_at: datetime
    delivery_status: WebhookDeliveryStatus = WebhookDeliveryStatus.PENDING
    delivery_attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "delivery_status": self.delivery_status.value,
            "delivery_attempts": self.delivery_attempts,
            "created_at": self.created_at.isoformat(),
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
        }


@dataclass
class SandboxUsageStats:
    """Usage statistics for a sandbox."""
    sandbox_id: str
    total_requests: int
    requests_today: int
    requests_this_hour: int
    average_latency_ms: float
    success_rate: float
    quota_remaining_daily: int
    quota_remaining_hourly: int
    last_request_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sandbox_id": self.sandbox_id,
            "total_requests": self.total_requests,
            "requests_today": self.requests_today,
            "requests_this_hour": self.requests_this_hour,
            "average_latency_ms": round(self.average_latency_ms, 2),
            "success_rate": round(self.success_rate, 2),
            "quota_remaining_daily": self.quota_remaining_daily,
            "quota_remaining_hourly": self.quota_remaining_hourly,
            "last_request_at": self.last_request_at.isoformat() if self.last_request_at else None,
        }


@dataclass
class SandboxEnvironment:
    """A sandbox environment for partner testing."""
    sandbox_id: str
    partner_id: str
    name: str
    description: Optional[str]
    config: SandboxConfig
    status: SandboxStatus
    created_at: datetime
    expires_at: Optional[datetime]
    api_keys: List[SandboxApiKey] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sandbox_id": self.sandbox_id,
            "partner_id": self.partner_id,
            "name": self.name,
            "description": self.description,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class PartnerSandboxManager:
    """
    Manages partner API sandbox environments.
    
    Provides isolated testing environments for partners to test their
    integrations without affecting production data.
    
    Example:
        manager = PartnerSandboxManager()
        await manager.initialize()
        
        # Create sandbox
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Test Environment",
            config=SandboxConfig(scenario=SandboxScenario.SUCCESS)
        )
        
        # Generate API key
        api_key = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id="partner_001"
        )
        
        # Simulate request
        response = await manager.simulate_request(
            api_key=key_id,
            method="GET",
            path="/api/v1/users",
            headers={},
            body=None
        )
    """
    
    def __init__(self, engine: Optional[AsyncEngine] = None):
        self.engine = engine
        self._sandboxes: Dict[str, SandboxEnvironment] = {}
        self._api_keys: Dict[str, SandboxApiKey] = {}
        self._usage_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._custom_handlers: Dict[str, Callable] = {}
    
    async def initialize(self) -> None:
        """Initialize the sandbox manager."""
        await self._ensure_tables()
        logger.info("PartnerSandboxManager initialized")
    
    async def _ensure_tables(self) -> None:
        """Ensure sandbox tables exist."""
        if not self.engine:
            from ..services.db_service import engine as db_engine
            self.engine = db_engine
            
        async with self.engine.begin() as conn:
            # Sandbox environments table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sandbox_environments (
                    id SERIAL PRIMARY KEY,
                    sandbox_id VARCHAR(255) UNIQUE NOT NULL,
                    partner_id VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    config JSONB NOT NULL,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            # Sandbox API keys table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sandbox_api_keys (
                    id SERIAL PRIMARY KEY,
                    key_id VARCHAR(255) UNIQUE NOT NULL,
                    key_secret_hash VARCHAR(255) NOT NULL,
                    partner_id VARCHAR(255) NOT NULL,
                    sandbox_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP,
                    last_used_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    is_revoked BOOLEAN DEFAULT FALSE
                )
            """))
            
            # Request logs table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sandbox_request_logs (
                    id SERIAL PRIMARY KEY,
                    log_id VARCHAR(255) UNIQUE NOT NULL,
                    sandbox_id VARCHAR(255) NOT NULL,
                    partner_id VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    method VARCHAR(10) NOT NULL,
                    path TEXT NOT NULL,
                    headers JSONB,
                    body TEXT,
                    response_status INTEGER,
                    response_body TEXT,
                    latency_ms FLOAT,
                    scenario VARCHAR(50),
                    client_ip VARCHAR(50)
                )
            """))
            
            # Webhook events table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sandbox_webhook_events (
                    id SERIAL PRIMARY KEY,
                    event_id VARCHAR(255) UNIQUE NOT NULL,
                    sandbox_id VARCHAR(255) NOT NULL,
                    partner_id VARCHAR(255) NOT NULL,
                    event_type VARCHAR(100) NOT NULL,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    delivery_status VARCHAR(50) DEFAULT 'pending',
                    delivery_attempts INTEGER DEFAULT 0,
                    last_attempt_at TIMESTAMP,
                    delivered_at TIMESTAMP,
                    error_message TEXT
                )
            """))
            
            # Usage stats table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sandbox_usage_stats (
                    id SERIAL PRIMARY KEY,
                    sandbox_id VARCHAR(255) UNIQUE NOT NULL,
                    total_requests INTEGER DEFAULT 0,
                    requests_today INTEGER DEFAULT 0,
                    requests_this_hour INTEGER DEFAULT 0,
                    average_latency_ms FLOAT DEFAULT 0,
                    success_rate FLOAT DEFAULT 100,
                    last_request_at TIMESTAMP,
                    stats_date DATE DEFAULT CURRENT_DATE,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            # Create indexes
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sandbox_partner 
                ON sandbox_environments(partner_id, status)
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sandbox_api_key_sandbox 
                ON sandbox_api_keys(sandbox_id, is_revoked)
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sandbox_logs_sandbox 
                ON sandbox_request_logs(sandbox_id, timestamp DESC)
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_webhook_events_status 
                ON sandbox_webhook_events(sandbox_id, delivery_status)
            """))
        
        logger.info("Sandbox tables ensured")
    
    async def create_sandbox(
        self,
        partner_id: str,
        name: str,
        config: Optional[SandboxConfig] = None,
        description: Optional[str] = None,
        expires_days: Optional[int] = 30
    ) -> SandboxEnvironment:
        """
        Create a new sandbox environment.
        
        Args:
            partner_id: Partner identifier
            name: Sandbox name
            config: Sandbox configuration
            description: Optional description
            expires_days: Days until expiration
            
        Returns:
            Created SandboxEnvironment
        """
        sandbox_id = f"sb_{uuid.uuid4().hex[:12]}"
        
        sandbox = SandboxEnvironment(
            sandbox_id=sandbox_id,
            partner_id=partner_id,
            name=name,
            description=description,
            config=config or SandboxConfig(),
            status=SandboxStatus.ACTIVE,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=expires_days) if expires_days else None,
        )
        
        # Persist to database
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO sandbox_environments (
                        sandbox_id, partner_id, name, description,
                        config, status, created_at, expires_at
                    ) VALUES (
                        :sandbox_id, :partner_id, :name, :description,
                        :config, :status, :created_at, :expires_at
                    )
                """),
                {
                    "sandbox_id": sandbox.sandbox_id,
                    "partner_id": sandbox.partner_id,
                    "name": sandbox.name,
                    "description": sandbox.description,
                    "config": json.dumps(sandbox.config.to_dict()),
                    "status": sandbox.status.value,
                    "created_at": sandbox.created_at,
                    "expires_at": sandbox.expires_at,
                }
            )
            await session.commit()
        
        self._sandboxes[sandbox_id] = sandbox
        logger.info(f"Created sandbox {sandbox_id} for partner {partner_id}")
        
        return sandbox
    
    async def get_sandbox(self, sandbox_id: str) -> Optional[SandboxEnvironment]:
        """Get a sandbox environment by ID."""
        if sandbox_id in self._sandboxes:
            return self._sandboxes[sandbox_id]
        
        # Load from database
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT * FROM sandbox_environments WHERE sandbox_id = :sandbox_id"),
                {"sandbox_id": sandbox_id}
            )
            row = result.fetchone()
            
            if row:
                sandbox = SandboxEnvironment(
                    sandbox_id=row.sandbox_id,
                    partner_id=row.partner_id,
                    name=row.name,
                    description=row.description,
                    config=SandboxConfig.from_dict(row.config),
                    status=SandboxStatus(row.status),
                    created_at=row.created_at,
                    expires_at=row.expires_at,
                )
                self._sandboxes[sandbox_id] = sandbox
                return sandbox
        
        return None
    
    async def list_sandboxes(
        self,
        partner_id: Optional[str] = None,
        status: Optional[SandboxStatus] = None
    ) -> List[SandboxEnvironment]:
        """List sandbox environments."""
        sandboxes = []
        
        async with AsyncSessionLocal() as session:
            if partner_id and status:
                result = await session.execute(
                    text("""
                        SELECT * FROM sandbox_environments
                        WHERE partner_id = :partner_id AND status = :status
                        ORDER BY created_at DESC
                    """),
                    {"partner_id": partner_id, "status": status.value}
                )
            elif partner_id:
                result = await session.execute(
                    text("""
                        SELECT * FROM sandbox_environments
                        WHERE partner_id = :partner_id
                        ORDER BY created_at DESC
                    """),
                    {"partner_id": partner_id}
                )
            elif status:
                result = await session.execute(
                    text("""
                        SELECT * FROM sandbox_environments
                        WHERE status = :status
                        ORDER BY created_at DESC
                    """),
                    {"status": status.value}
                )
            else:
                result = await session.execute(
                    text("SELECT * FROM sandbox_environments ORDER BY created_at DESC")
                )
            
            for row in result:
                sandbox = SandboxEnvironment(
                    sandbox_id=row.sandbox_id,
                    partner_id=row.partner_id,
                    name=row.name,
                    description=row.description,
                    config=SandboxConfig.from_dict(row.config),
                    status=SandboxStatus(row.status),
                    created_at=row.created_at,
                    expires_at=row.expires_at,
                )
                sandboxes.append(sandbox)
                self._sandboxes[row.sandbox_id] = sandbox
        
        return sandboxes
    
    async def create_api_key(
        self,
        sandbox_id: str,
        partner_id: str,
        expires_days: Optional[int] = 90
    ) -> Tuple[SandboxApiKey, str]:
        """
        Create an API key for sandbox access.
        
        Returns:
            Tuple of (SandboxApiKey, plain_secret)
        """
        key_id = f"sbk_{uuid.uuid4().hex[:16]}"
        plain_secret = secrets.token_urlsafe(32)
        secret_hash = hashlib.sha256(plain_secret.encode()).hexdigest()
        
        api_key = SandboxApiKey(
            key_id=key_id,
            key_secret=secret_hash,
            partner_id=partner_id,
            sandbox_id=sandbox_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=expires_days) if expires_days else None,
        )
        
        # Persist to database
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO sandbox_api_keys (
                        key_id, key_secret_hash, partner_id, sandbox_id,
                        created_at, expires_at
                    ) VALUES (
                        :key_id, :key_secret_hash, :partner_id, :sandbox_id,
                        :created_at, :expires_at
                    )
                """),
                {
                    "key_id": api_key.key_id,
                    "key_secret_hash": api_key.key_secret,
                    "partner_id": api_key.partner_id,
                    "sandbox_id": api_key.sandbox_id,
                    "created_at": api_key.created_at,
                    "expires_at": api_key.expires_at,
                }
            )
            await session.commit()
        
        self._api_keys[key_id] = api_key
        
        logger.info(f"Created API key {key_id} for sandbox {sandbox_id}")
        
        return api_key, plain_secret
    
    async def validate_api_key(self, key_id: str, key_secret: str) -> Optional[SandboxApiKey]:
        """Validate an API key."""
        secret_hash = hashlib.sha256(key_secret.encode()).hexdigest()
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM sandbox_api_keys
                    WHERE key_id = :key_id AND key_secret_hash = :secret_hash
                    AND is_revoked = FALSE
                    AND (expires_at IS NULL OR expires_at > NOW())
                """),
                {"key_id": key_id, "secret_hash": secret_hash}
            )
            row = result.fetchone()
            
            if row:
                return SandboxApiKey(
                    key_id=row.key_id,
                    key_secret=row.key_secret_hash,
                    partner_id=row.partner_id,
                    sandbox_id=row.sandbox_id,
                    created_at=row.created_at,
                    expires_at=row.expires_at,
                    last_used_at=row.last_used_at,
                    usage_count=row.usage_count,
                    is_revoked=row.is_revoked,
                )
        
        return None
    
    async def simulate_request(
        self,
        api_key: str,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulate an API request in the sandbox.
        
        Args:
            api_key: Sandbox API key
            method: HTTP method
            path: Request path
            headers: Request headers
            body: Request body
            client_ip: Client IP address
            
        Returns:
            Simulated response
        """
        # Validate API key (simplified - assumes key_id passed)
        key_data = self._api_keys.get(api_key)
        if not key_data:
            # Try to load from key_id only (in real impl, would validate secret)
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("SELECT * FROM sandbox_api_keys WHERE key_id = :key_id"),
                    {"key_id": api_key}
                )
                row = result.fetchone()
                if row:
                    key_data = SandboxApiKey(
                        key_id=row.key_id,
                        key_secret=row.key_secret_hash,
                        partner_id=row.partner_id,
                        sandbox_id=row.sandbox_id,
                        created_at=row.created_at,
                        expires_at=row.expires_at,
                        last_used_at=row.last_used_at,
                        usage_count=row.usage_count,
                        is_revoked=row.is_revoked,
                    )
        
        if not key_data or key_data.is_revoked:
            return {
                "status": 401,
                "body": {"error": "Invalid or revoked API key"},
                "latency_ms": 0,
            }
        
        # Get sandbox
        sandbox = await self.get_sandbox(key_data.sandbox_id)
        if not sandbox or sandbox.status != SandboxStatus.ACTIVE:
            return {
                "status": 403,
                "body": {"error": "Sandbox not active"},
                "latency_ms": 0,
            }
        
        # Check quotas
        quota_check = await self._check_quotas(sandbox.sandbox_id, sandbox.config)
        if not quota_check["allowed"]:
            return {
                "status": 429,
                "body": {"error": "Quota exceeded", "details": quota_check},
                "latency_ms": 0,
            }
        
        # Simulate latency
        start_time = time.time()
        latency_ms = sandbox.config.latency_ms
        
        # Determine scenario
        scenario = sandbox.config.scenario
        if scenario == SandboxScenario.MIXED:
            scenario = self._get_random_scenario()
        
        # Generate response based on scenario
        response = self._generate_response(scenario, method, path, sandbox.config)
        
        # Apply latency
        await asyncio.sleep(latency_ms / 1000)
        
        actual_latency = (time.time() - start_time) * 1000
        
        # Log request
        if sandbox.config.enable_logging:
            await self._log_request(
                sandbox_id=sandbox.sandbox_id,
                partner_id=sandbox.partner_id,
                method=method,
                path=path,
                headers=headers or {},
                body=body,
                response_status=response["status"],
                response_body=json.dumps(response["body"]),
                latency_ms=actual_latency,
                scenario=scenario,
                client_ip=client_ip,
            )
        
        # Update usage stats
        await self._update_usage_stats(sandbox.sandbox_id, actual_latency, response["status"])
        
        # Update API key usage
        await self._update_api_key_usage(key_data.key_id)
        
        return {
            "status": response["status"],
            "body": response["body"],
            "headers": response.get("headers", {}),
            "latency_ms": round(actual_latency, 2),
            "scenario": scenario.value,
            "sandbox_id": sandbox.sandbox_id,
        }
    
    def _generate_response(
        self,
        scenario: SandboxScenario,
        method: str,
        path: str,
        config: SandboxConfig
    ) -> Dict[str, Any]:
        """Generate a response based on the scenario."""
        
        if scenario == SandboxScenario.SUCCESS:
            return {
                "status": 200,
                "body": {
                    "success": True,
                    "data": {"message": "Sandbox response", "path": path, "method": method},
                    "timestamp": datetime.utcnow().isoformat(),
                },
                "headers": {"X-Sandbox": "true", "X-Scenario": "success"},
            }
        
        elif scenario == SandboxScenario.ERROR:
            return {
                "status": 500,
                "body": {
                    "success": False,
                    "error": "Simulated server error",
                    "code": "SANDBOX_ERROR",
                },
                "headers": {"X-Sandbox": "true", "X-Scenario": "error"},
            }
        
        elif scenario == SandboxScenario.TIMEOUT:
            # Timeout responses return 504
            return {
                "status": 504,
                "body": {
                    "success": False,
                    "error": "Gateway timeout (simulated)",
                    "code": "SANDBOX_TIMEOUT",
                },
                "headers": {"X-Sandbox": "true", "X-Scenario": "timeout"},
            }
        
        elif scenario == SandboxScenario.RATE_LIMIT:
            return {
                "status": 429,
                "body": {
                    "success": False,
                    "error": "Rate limit exceeded (simulated)",
                    "code": "SANDBOX_RATE_LIMIT",
                    "retry_after": 60,
                },
                "headers": {
                    "X-Sandbox": "true",
                    "X-Scenario": "rate_limit",
                    "Retry-After": "60",
                },
            }
        
        elif scenario == SandboxScenario.DEGRADED:
            # Degraded still returns success but slower (latency handled separately)
            return {
                "status": 200,
                "body": {
                    "success": True,
                    "data": {"message": "Degraded response", "path": path},
                    "degraded": True,
                },
                "headers": {"X-Sandbox": "true", "X-Scenario": "degraded"},
            }
        
        elif scenario == SandboxScenario.CUSTOM:
            # Use custom response from config
            custom = config.custom_responses.get(f"{method}:{path}", {})
            return {
                "status": custom.get("status", 200),
                "body": custom.get("body", {"success": True}),
                "headers": custom.get("headers", {}),
            }
        
        return {
            "status": 200,
            "body": {"success": True},
            "headers": {"X-Sandbox": "true"},
        }
    
    def _get_random_scenario(self) -> SandboxScenario:
        """Get a random scenario for MIXED mode."""
        import random
        scenarios = [
            SandboxScenario.SUCCESS,
            SandboxScenario.SUCCESS,
            SandboxScenario.SUCCESS,
            SandboxScenario.ERROR,
            SandboxScenario.RATE_LIMIT,
        ]
        return random.choice(scenarios)
    
    async def _check_quotas(
        self,
        sandbox_id: str,
        config: SandboxConfig
    ) -> Dict[str, Any]:
        """Check if request is within quotas."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
        
        daily_key = f"{sandbox_id}:{today}"
        hourly_key = f"{sandbox_id}:{hour}"
        
        daily_count = self._usage_counters["daily"].get(daily_key, 0)
        hourly_count = self._usage_counters["hourly"].get(hourly_key, 0)
        
        allowed = (
            daily_count < config.quota_daily and
            hourly_count < config.quota_hourly
        )
        
        return {
            "allowed": allowed,
            "daily_used": daily_count,
            "daily_limit": config.quota_daily,
            "hourly_used": hourly_count,
            "hourly_limit": config.quota_hourly,
        }
    
    async def _log_request(
        self,
        sandbox_id: str,
        partner_id: str,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Optional[str],
        response_status: int,
        response_body: str,
        latency_ms: float,
        scenario: SandboxScenario,
        client_ip: Optional[str],
    ) -> None:
        """Log a sandbox request."""
        log_id = f"log_{uuid.uuid4().hex[:12]}"
        
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO sandbox_request_logs (
                        log_id, sandbox_id, partner_id, timestamp, method, path,
                        headers, body, response_status, response_body,
                        latency_ms, scenario, client_ip
                    ) VALUES (
                        :log_id, :sandbox_id, :partner_id, NOW(), :method, :path,
                        :headers, :body, :response_status, :response_body,
                        :latency_ms, :scenario, :client_ip
                    )
                """),
                {
                    "log_id": log_id,
                    "sandbox_id": sandbox_id,
                    "partner_id": partner_id,
                    "method": method,
                    "path": path,
                    "headers": json.dumps(headers),
                    "body": body,
                    "response_status": response_status,
                    "response_body": response_body,
                    "latency_ms": latency_ms,
                    "scenario": scenario.value,
                    "client_ip": client_ip,
                }
            )
            await session.commit()
    
    async def _update_usage_stats(
        self,
        sandbox_id: str,
        latency_ms: float,
        status_code: int
    ) -> None:
        """Update usage statistics."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
        
        self._usage_counters["daily"][f"{sandbox_id}:{today}"] += 1
        self._usage_counters["hourly"][f"{sandbox_id}:{hour}"] += 1
        
        # Update database
        async with AsyncSessionLocal() as session:
            # Try to update existing record
            result = await session.execute(
                text("""
                    UPDATE sandbox_usage_stats
                    SET total_requests = total_requests + 1,
                        requests_today = requests_today + 1,
                        requests_this_hour = requests_this_hour + 1,
                        average_latency_ms = (average_latency_ms * total_requests + :latency) / (total_requests + 1),
                        last_request_at = NOW(),
                        updated_at = NOW()
                    WHERE sandbox_id = :sandbox_id
                    RETURNING id
                """),
                {"sandbox_id": sandbox_id, "latency": latency_ms}
            )
            
            if not result.fetchone():
                # Insert new record
                await session.execute(
                    text("""
                        INSERT INTO sandbox_usage_stats (
                            sandbox_id, total_requests, requests_today,
                            requests_this_hour, average_latency_ms, last_request_at
                        ) VALUES (
                            :sandbox_id, 1, 1, 1, :latency, NOW()
                        )
                    """),
                    {"sandbox_id": sandbox_id, "latency": latency_ms}
                )
            
            await session.commit()
    
    async def _update_api_key_usage(self, key_id: str) -> None:
        """Update API key usage statistics."""
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    UPDATE sandbox_api_keys
                    SET usage_count = usage_count + 1,
                        last_used_at = NOW()
                    WHERE key_id = :key_id
                """),
                {"key_id": key_id}
            )
            await session.commit()
    
    async def get_usage_stats(self, sandbox_id: str) -> Optional[SandboxUsageStats]:
        """Get usage statistics for a sandbox."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT * FROM sandbox_usage_stats WHERE sandbox_id = :sandbox_id"),
                {"sandbox_id": sandbox_id}
            )
            row = result.fetchone()
            
            if row:
                # Get sandbox config for quota info
                sandbox = await self.get_sandbox(sandbox_id)
                config = sandbox.config if sandbox else SandboxConfig()
                
                return SandboxUsageStats(
                    sandbox_id=sandbox_id,
                    total_requests=row.total_requests,
                    requests_today=row.requests_today,
                    requests_this_hour=row.requests_this_hour,
                    average_latency_ms=row.average_latency_ms,
                    success_rate=row.success_rate,
                    quota_remaining_daily=max(0, config.quota_daily - row.requests_today),
                    quota_remaining_hourly=max(0, config.quota_hourly - row.requests_this_hour),
                    last_request_at=row.last_request_at,
                )
        
        return None
    
    async def get_request_logs(
        self,
        sandbox_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get request logs for a sandbox."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM sandbox_request_logs
                    WHERE sandbox_id = :sandbox_id
                    ORDER BY timestamp DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"sandbox_id": sandbox_id, "limit": limit, "offset": offset}
            )
            
            logs = []
            for row in result:
                logs.append({
                    "log_id": row.log_id,
                    "timestamp": row.timestamp.isoformat(),
                    "method": row.method,
                    "path": row.path,
                    "response_status": row.response_status,
                    "latency_ms": round(row.latency_ms, 2),
                    "scenario": row.scenario,
                })
            
            return logs
    
    async def create_webhook_event(
        self,
        sandbox_id: str,
        partner_id: str,
        event_type: str,
        payload: Dict[str, Any]
    ) -> WebhookEvent:
        """Create a webhook event for testing."""
        event_id = f"evt_{uuid.uuid4().hex[:16]}"
        
        event = WebhookEvent(
            event_id=event_id,
            sandbox_id=sandbox_id,
            partner_id=partner_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.utcnow(),
        )
        
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO sandbox_webhook_events (
                        event_id, sandbox_id, partner_id, event_type,
                        payload, created_at, delivery_status
                    ) VALUES (
                        :event_id, :sandbox_id, :partner_id, :event_type,
                        :payload, :created_at, :delivery_status
                    )
                """),
                {
                    "event_id": event.event_id,
                    "sandbox_id": event.sandbox_id,
                    "partner_id": event.partner_id,
                    "event_type": event.event_type,
                    "payload": json.dumps(event.payload),
                    "created_at": event.created_at,
                    "delivery_status": event.delivery_status.value,
                }
            )
            await session.commit()
        
        return event
    
    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    UPDATE sandbox_api_keys
                    SET is_revoked = TRUE
                    WHERE key_id = :key_id
                    RETURNING id
                """),
                {"key_id": key_id}
            )
            await session.commit()
            
            if result.fetchone():
                if key_id in self._api_keys:
                    self._api_keys[key_id].is_revoked = True
                logger.info(f"Revoked API key {key_id}")
                return True
        
        return False
    
    async def delete_sandbox(self, sandbox_id: str) -> bool:
        """Delete a sandbox environment."""
        async with AsyncSessionLocal() as session:
            # Soft delete - mark as deleted
            result = await session.execute(
                text("""
                    UPDATE sandbox_environments
                    SET status = 'deleted', updated_at = NOW()
                    WHERE sandbox_id = :sandbox_id
                    RETURNING id
                """),
                {"sandbox_id": sandbox_id}
            )
            await session.commit()
            
            if result.fetchone():
                if sandbox_id in self._sandboxes:
                    self._sandboxes[sandbox_id].status = SandboxStatus.DELETED
                logger.info(f"Deleted sandbox {sandbox_id}")
                return True
        
        return False
    
    async def update_sandbox_config(
        self,
        sandbox_id: str,
        config: SandboxConfig
    ) -> bool:
        """Update sandbox configuration."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    UPDATE sandbox_environments
                    SET config = :config, updated_at = NOW()
                    WHERE sandbox_id = :sandbox_id
                    RETURNING id
                """),
                {
                    "sandbox_id": sandbox_id,
                    "config": json.dumps(config.to_dict()),
                }
            )
            await session.commit()
            
            if result.fetchone():
                if sandbox_id in self._sandboxes:
                    self._sandboxes[sandbox_id].config = config
                logger.info(f"Updated config for sandbox {sandbox_id}")
                return True
        
        return False
    
    async def get_global_statistics(self) -> Dict[str, Any]:
        """Get global sandbox statistics."""
        async with AsyncSessionLocal() as session:
            # Total sandboxes
            result = await session.execute(
                text("SELECT COUNT(*) FROM sandbox_environments")
            )
            total_sandboxes = result.scalar()
            
            # Active sandboxes
            result = await session.execute(
                text("SELECT COUNT(*) FROM sandbox_environments WHERE status = 'active'")
            )
            active_sandboxes = result.scalar()
            
            # Total requests
            result = await session.execute(
                text("SELECT SUM(total_requests) FROM sandbox_usage_stats")
            )
            total_requests = result.scalar() or 0
            
            # Total API keys
            result = await session.execute(
                text("SELECT COUNT(*) FROM sandbox_api_keys WHERE is_revoked = FALSE")
            )
            active_keys = result.scalar()
            
            # Recent webhooks
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM sandbox_webhook_events
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
            )
            recent_webhooks = result.scalar()
            
            return {
                "total_sandboxes": total_sandboxes,
                "active_sandboxes": active_sandboxes,
                "total_requests": total_requests,
                "active_api_keys": active_keys,
                "webhooks_24h": recent_webhooks,
                "timestamp": datetime.utcnow().isoformat(),
            }


# Global instance
_sandbox_manager: Optional[PartnerSandboxManager] = None


async def get_sandbox_manager(
    engine: Optional[AsyncEngine] = None
) -> PartnerSandboxManager:
    """Get or create the global sandbox manager."""
    global _sandbox_manager
    
    if _sandbox_manager is None:
        _sandbox_manager = PartnerSandboxManager(engine)
        await _sandbox_manager.initialize()
    
    return _sandbox_manager
