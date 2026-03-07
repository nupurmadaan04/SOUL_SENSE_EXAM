"""
Tests for Partner API Sandbox Environment (#1443)

Comprehensive tests for partner sandbox management and simulation.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base

# Import the module under test
import sys
sys.path.insert(0, 'backend/fastapi')

from api.utils.partner_sandbox import (
    PartnerSandboxManager,
    SandboxConfig,
    SandboxScenario,
    SandboxStatus,
    SandboxEnvironment,
    SandboxApiKey,
    SandboxUsageStats,
    WebhookDeliveryStatus,
    WebhookEvent,
    get_sandbox_manager,
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
    """Create initialized sandbox manager."""
    mgr = PartnerSandboxManager(async_engine)
    
    # Create tables
    async with async_engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sandbox_environments (
                id INTEGER PRIMARY KEY,
                sandbox_id TEXT UNIQUE NOT NULL,
                partner_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                config TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sandbox_api_keys (
                id INTEGER PRIMARY KEY,
                key_id TEXT UNIQUE NOT NULL,
                key_secret_hash TEXT NOT NULL,
                partner_id TEXT NOT NULL,
                sandbox_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_used_at TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                is_revoked BOOLEAN DEFAULT 0
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sandbox_request_logs (
                id INTEGER PRIMARY KEY,
                log_id TEXT UNIQUE NOT NULL,
                sandbox_id TEXT NOT NULL,
                partner_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                headers TEXT,
                body TEXT,
                response_status INTEGER,
                response_body TEXT,
                latency_ms REAL,
                scenario TEXT,
                client_ip TEXT
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sandbox_webhook_events (
                id INTEGER PRIMARY KEY,
                event_id TEXT UNIQUE NOT NULL,
                sandbox_id TEXT NOT NULL,
                partner_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivery_status TEXT DEFAULT 'pending',
                delivery_attempts INTEGER DEFAULT 0,
                last_attempt_at TIMESTAMP,
                delivered_at TIMESTAMP,
                error_message TEXT
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sandbox_usage_stats (
                id INTEGER PRIMARY KEY,
                sandbox_id TEXT UNIQUE NOT NULL,
                total_requests INTEGER DEFAULT 0,
                requests_today INTEGER DEFAULT 0,
                requests_this_hour INTEGER DEFAULT 0,
                average_latency_ms REAL DEFAULT 0,
                success_rate REAL DEFAULT 100,
                last_request_at TIMESTAMP,
                stats_date DATE DEFAULT CURRENT_DATE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    
    await mgr.initialize()
    yield mgr


@pytest.fixture
def sample_config():
    """Create sample sandbox configuration."""
    return SandboxConfig(
        latency_ms=50,
        scenario=SandboxScenario.SUCCESS,
        quota_daily=1000,
        quota_hourly=100,
    )


# --- Test Classes ---

class TestSandboxConfig:
    """Test sandbox configuration model."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = SandboxConfig()
        
        assert config.latency_ms == 100
        assert config.scenario == SandboxScenario.SUCCESS
        assert config.quota_daily == 1000
        assert config.quota_hourly == 100
        assert config.enable_logging is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = SandboxConfig(
            latency_ms=200,
            scenario=SandboxScenario.ERROR,
            quota_daily=500,
            webhook_url="https://example.com/webhook",
        )
        
        assert config.latency_ms == 200
        assert config.scenario == SandboxScenario.ERROR
        assert config.quota_daily == 500
        assert config.webhook_url == "https://example.com/webhook"
    
    def test_config_serialization(self):
        """Test config to/from dict."""
        original = SandboxConfig(
            latency_ms=150,
            scenario=SandboxScenario.TIMEOUT,
            allowed_endpoints=["/api/v1/*"],
        )
        
        data = original.to_dict()
        restored = SandboxConfig.from_dict(data)
        
        assert restored.latency_ms == 150
        assert restored.scenario == SandboxScenario.TIMEOUT
        assert restored.allowed_endpoints == ["/api/v1/*"]


class TestSandboxEnvironment:
    """Test sandbox environment model."""
    
    def test_environment_creation(self):
        """Test creating a sandbox environment."""
        env = SandboxEnvironment(
            sandbox_id="sb_001",
            partner_id="partner_001",
            name="Test Sandbox",
            description="A test sandbox",
            config=SandboxConfig(),
            status=SandboxStatus.ACTIVE,
            created_at=datetime.utcnow(),
            expires_at=None,
        )
        
        assert env.sandbox_id == "sb_001"
        assert env.partner_id == "partner_001"
        assert env.name == "Test Sandbox"
        assert env.status == SandboxStatus.ACTIVE
    
    def test_environment_to_dict(self):
        """Test environment serialization."""
        env = SandboxEnvironment(
            sandbox_id="sb_001",
            partner_id="partner_001",
            name="Test Sandbox",
            description=None,
            config=SandboxConfig(),
            status=SandboxStatus.ACTIVE,
            created_at=datetime.utcnow(),
            expires_at=None,
        )
        
        data = env.to_dict()
        assert data["sandbox_id"] == "sb_001"
        assert data["partner_id"] == "partner_001"
        assert data["status"] == "active"
        assert "config" in data


class TestSandboxApiKey:
    """Test sandbox API key model."""
    
    def test_api_key_creation(self):
        """Test creating an API key."""
        key = SandboxApiKey(
            key_id="sbk_001",
            key_secret="secret_hash",
            partner_id="partner_001",
            sandbox_id="sb_001",
            created_at=datetime.utcnow(),
        )
        
        assert key.key_id == "sbk_001"
        assert key.partner_id == "partner_001"
        assert key.sandbox_id == "sb_001"
        assert key.usage_count == 0
        assert not key.is_revoked
    
    def test_api_key_to_dict(self):
        """Test API key serialization."""
        key = SandboxApiKey(
            key_id="sbk_001",
            key_secret="secret_hash",
            partner_id="partner_001",
            sandbox_id="sb_001",
            created_at=datetime.utcnow(),
        )
        
        data = key.to_dict()
        assert data["key_id"] == "sbk_001"
        assert data["partner_id"] == "partner_001"
        assert "key_secret" not in data  # Secret should not be in dict


class TestWebhookEvent:
    """Test webhook event model."""
    
    def test_event_creation(self):
        """Test creating a webhook event."""
        event = WebhookEvent(
            event_id="evt_001",
            sandbox_id="sb_001",
            partner_id="partner_001",
            event_type="user.created",
            payload={"user_id": "123"},
            created_at=datetime.utcnow(),
        )
        
        assert event.event_id == "evt_001"
        assert event.event_type == "user.created"
        assert event.delivery_status == WebhookDeliveryStatus.PENDING
        assert event.delivery_attempts == 0


class TestSandboxManager:
    """Test sandbox manager functionality."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, async_engine):
        """Test manager initialization."""
        mgr = PartnerSandboxManager(async_engine)
        await mgr.initialize()
        assert mgr._sandboxes == {}
    
    @pytest.mark.asyncio
    async def test_create_sandbox(self, manager, sample_config):
        """Test creating a sandbox."""
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Test Sandbox",
            config=sample_config,
            expires_days=30,
        )
        
        assert sandbox.sandbox_id.startswith("sb_")
        assert sandbox.partner_id == "partner_001"
        assert sandbox.name == "Test Sandbox"
        assert sandbox.status == SandboxStatus.ACTIVE
        assert sandbox.expires_at is not None
    
    @pytest.mark.asyncio
    async def test_get_sandbox(self, manager, sample_config):
        """Test retrieving a sandbox."""
        created = await manager.create_sandbox(
            partner_id="partner_001",
            name="Test Sandbox",
            config=sample_config,
        )
        
        retrieved = await manager.get_sandbox(created.sandbox_id)
        
        assert retrieved is not None
        assert retrieved.sandbox_id == created.sandbox_id
        assert retrieved.name == "Test Sandbox"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_sandbox(self, manager):
        """Test retrieving non-existent sandbox."""
        sandbox = await manager.get_sandbox("nonexistent")
        assert sandbox is None
    
    @pytest.mark.asyncio
    async def test_list_sandboxes(self, manager, sample_config):
        """Test listing sandboxes."""
        # Create multiple sandboxes
        for i in range(3):
            await manager.create_sandbox(
                partner_id=f"partner_{i}",
                name=f"Sandbox {i}",
                config=sample_config,
            )
        
        sandboxes = await manager.list_sandboxes()
        assert len(sandboxes) >= 3
    
    @pytest.mark.asyncio
    async def test_list_sandboxes_by_partner(self, manager, sample_config):
        """Test listing sandboxes by partner."""
        await manager.create_sandbox(
            partner_id="specific_partner",
            name="Specific Sandbox",
            config=sample_config,
        )
        
        sandboxes = await manager.list_sandboxes(partner_id="specific_partner")
        assert len(sandboxes) >= 1
        assert all(s.partner_id == "specific_partner" for s in sandboxes)
    
    @pytest.mark.asyncio
    async def test_create_api_key(self, manager, sample_config):
        """Test creating an API key."""
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Test Sandbox",
            config=sample_config,
        )
        
        api_key, secret = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        assert api_key.key_id.startswith("sbk_")
        assert api_key.sandbox_id == sandbox.sandbox_id
        assert len(secret) > 20  # Should be a secure secret
    
    @pytest.mark.asyncio
    async def test_simulate_request_success(self, manager, sample_config):
        """Test simulating a successful request."""
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Test Sandbox",
            config=sample_config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        response = await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/api/v1/users",
        )
        
        assert response["status"] == 200
        assert response["body"]["success"] is True
        assert response["scenario"] == "success"
        assert "latency_ms" in response
    
    @pytest.mark.asyncio
    async def test_simulate_request_error_scenario(self, manager):
        """Test simulating a request with error scenario."""
        config = SandboxConfig(scenario=SandboxScenario.ERROR)
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Error Sandbox",
            config=config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        response = await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/api/v1/users",
        )
        
        assert response["status"] == 500
        assert response["body"]["success"] is False
        assert response["scenario"] == "error"
    
    @pytest.mark.asyncio
    async def test_simulate_request_rate_limit(self, manager):
        """Test simulating rate limited request."""
        config = SandboxConfig(scenario=SandboxScenario.RATE_LIMIT)
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Rate Limited Sandbox",
            config=config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        response = await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/api/v1/users",
        )
        
        assert response["status"] == 429
        assert "retry_after" in response["body"] or response["body"].get("code") == "SANDBOX_RATE_LIMIT"
    
    @pytest.mark.asyncio
    async def test_simulate_request_invalid_key(self, manager):
        """Test simulating request with invalid API key."""
        response = await manager.simulate_request(
            api_key="invalid_key",
            method="GET",
            path="/api/v1/users",
        )
        
        assert response["status"] == 401
        assert "error" in response["body"]
    
    @pytest.mark.asyncio
    async def test_get_usage_stats(self, manager, sample_config):
        """Test getting usage statistics."""
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Test Sandbox",
            config=sample_config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        # Make some requests
        for _ in range(5):
            await manager.simulate_request(
                api_key=api_key.key_id,
                method="GET",
                path="/api/v1/users",
            )
        
        stats = await manager.get_usage_stats(sandbox.sandbox_id)
        
        assert stats is not None
        assert stats.total_requests >= 5
        assert stats.sandbox_id == sandbox.sandbox_id
    
    @pytest.mark.asyncio
    async def test_get_request_logs(self, manager, sample_config):
        """Test getting request logs."""
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Test Sandbox",
            config=sample_config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        # Make a request
        await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/api/v1/users",
        )
        
        logs = await manager.get_request_logs(sandbox.sandbox_id)
        
        assert len(logs) >= 1
        assert logs[0]["method"] == "GET"
        assert logs[0]["path"] == "/api/v1/users"
    
    @pytest.mark.asyncio
    async def test_create_webhook_event(self, manager, sample_config):
        """Test creating a webhook event."""
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Test Sandbox",
            config=sample_config,
        )
        
        event = await manager.create_webhook_event(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
            event_type="user.created",
            payload={"user_id": "123"},
        )
        
        assert event.event_id.startswith("evt_")
        assert event.event_type == "user.created"
        assert event.delivery_status == WebhookDeliveryStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_revoke_api_key(self, manager, sample_config):
        """Test revoking an API key."""
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Test Sandbox",
            config=sample_config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        success = await manager.revoke_api_key(api_key.key_id)
        assert success is True
        
        # Verify key is revoked
        response = await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/api/v1/users",
        )
        assert response["status"] == 401
    
    @pytest.mark.asyncio
    async def test_delete_sandbox(self, manager, sample_config):
        """Test deleting a sandbox."""
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Test Sandbox",
            config=sample_config,
        )
        
        success = await manager.delete_sandbox(sandbox.sandbox_id)
        assert success is True
        
        # Verify sandbox is deleted
        retrieved = await manager.get_sandbox(sandbox.sandbox_id)
        assert retrieved.status == SandboxStatus.DELETED
    
    @pytest.mark.asyncio
    async def test_update_sandbox_config(self, manager, sample_config):
        """Test updating sandbox configuration."""
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Test Sandbox",
            config=sample_config,
        )
        
        new_config = SandboxConfig(
            latency_ms=500,
            scenario=SandboxScenario.DEGRADED,
            quota_daily=2000,
        )
        
        success = await manager.update_sandbox_config(sandbox.sandbox_id, new_config)
        assert success is True
        
        # Verify update
        updated = await manager.get_sandbox(sandbox.sandbox_id)
        assert updated.config.latency_ms == 500
        assert updated.config.scenario == SandboxScenario.DEGRADED
        assert updated.config.quota_daily == 2000
    
    @pytest.mark.asyncio
    async def test_get_global_statistics(self, manager, sample_config):
        """Test getting global statistics."""
        # Create multiple sandboxes and make requests
        for i in range(3):
            sandbox = await manager.create_sandbox(
                partner_id=f"partner_{i}",
                name=f"Sandbox {i}",
                config=sample_config,
            )
            
            api_key, _ = await manager.create_api_key(
                sandbox_id=sandbox.sandbox_id,
                partner_id=sandbox.partner_id,
            )
            
            await manager.simulate_request(
                api_key=api_key.key_id,
                method="GET",
                path="/api/v1/test",
            )
        
        stats = await manager.get_global_statistics()
        
        assert stats["total_sandboxes"] >= 3
        assert stats["total_requests"] >= 3
        assert "timestamp" in stats


class TestSandboxScenarios:
    """Test all sandbox scenarios."""
    
    @pytest.mark.asyncio
    async def test_success_scenario(self, manager):
        """Test success scenario."""
        config = SandboxConfig(scenario=SandboxScenario.SUCCESS)
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Success Sandbox",
            config=config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        response = await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/test",
        )
        
        assert response["status"] == 200
        assert response["body"]["success"] is True
    
    @pytest.mark.asyncio
    async def test_error_scenario(self, manager):
        """Test error scenario."""
        config = SandboxConfig(scenario=SandboxScenario.ERROR)
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Error Sandbox",
            config=config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        response = await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/test",
        )
        
        assert response["status"] == 500
        assert response["body"]["success"] is False
    
    @pytest.mark.asyncio
    async def test_timeout_scenario(self, manager):
        """Test timeout scenario."""
        config = SandboxConfig(scenario=SandboxScenario.TIMEOUT)
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Timeout Sandbox",
            config=config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        response = await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/test",
        )
        
        assert response["status"] == 504
    
    @pytest.mark.asyncio
    async def test_rate_limit_scenario(self, manager):
        """Test rate limit scenario."""
        config = SandboxConfig(scenario=SandboxScenario.RATE_LIMIT)
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Rate Limit Sandbox",
            config=config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        response = await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/test",
        )
        
        assert response["status"] == 429
    
    @pytest.mark.asyncio
    async def test_degraded_scenario(self, manager):
        """Test degraded scenario."""
        config = SandboxConfig(scenario=SandboxScenario.DEGRADED)
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Degraded Sandbox",
            config=config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        response = await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/test",
        )
        
        assert response["status"] == 200
        assert response["body"].get("degraded") is True
    
    @pytest.mark.asyncio
    async def test_custom_scenario(self, manager):
        """Test custom scenario."""
        config = SandboxConfig(
            scenario=SandboxScenario.CUSTOM,
            custom_responses={
                "GET:/custom": {
                    "status": 201,
                    "body": {"custom": True},
                }
            }
        )
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Custom Sandbox",
            config=config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        response = await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/custom",
        )
        
        assert response["status"] == 201
        assert response["body"]["custom"] is True


class TestQuotaManagement:
    """Test quota management."""
    
    @pytest.mark.asyncio
    async def test_quota_tracking(self, manager):
        """Test that quotas are tracked correctly."""
        config = SandboxConfig(quota_hourly=10)
        sandbox = await manager.create_sandbox(
            partner_id="partner_001",
            name="Quota Sandbox",
            config=config,
        )
        
        api_key, _ = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        # Make requests
        for i in range(5):
            response = await manager.simulate_request(
                api_key=api_key.key_id,
                method="GET",
                path="/test",
            )
            assert response["status"] == 200
        
        # Check usage stats
        stats = await manager.get_usage_stats(sandbox.sandbox_id)
        assert stats.requests_this_hour == 5
        assert stats.quota_remaining_hourly == 5


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(self, manager):
        """Test revoking a non-existent API key."""
        success = await manager.revoke_api_key("nonexistent_key")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_sandbox(self, manager):
        """Test deleting a non-existent sandbox."""
        success = await manager.delete_sandbox("nonexistent_sandbox")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_sandbox(self, manager, sample_config):
        """Test updating a non-existent sandbox."""
        success = await manager.update_sandbox_config("nonexistent", sample_config)
        assert success is False
    
    @pytest.mark.asyncio
    async def test_get_stats_nonexistent_sandbox(self, manager):
        """Test getting stats for non-existent sandbox."""
        stats = await manager.get_usage_stats("nonexistent")
        assert stats is None


class TestIntegration:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_full_partner_workflow(self, async_engine):
        """Test complete partner workflow."""
        manager = PartnerSandboxManager(async_engine)
        
        # Create tables
        async with async_engine.begin() as conn:
            for table_sql in [
                """CREATE TABLE IF NOT EXISTS sandbox_environments (
                    id INTEGER PRIMARY KEY,
                    sandbox_id TEXT UNIQUE NOT NULL,
                    partner_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    config TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                """CREATE TABLE IF NOT EXISTS sandbox_api_keys (
                    id INTEGER PRIMARY KEY,
                    key_id TEXT UNIQUE NOT NULL,
                    key_secret_hash TEXT NOT NULL,
                    partner_id TEXT NOT NULL,
                    sandbox_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    last_used_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    is_revoked BOOLEAN DEFAULT 0
                )""",
                """CREATE TABLE IF NOT EXISTS sandbox_request_logs (
                    id INTEGER PRIMARY KEY,
                    log_id TEXT UNIQUE NOT NULL,
                    sandbox_id TEXT NOT NULL,
                    partner_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    headers TEXT,
                    body TEXT,
                    response_status INTEGER,
                    response_body TEXT,
                    latency_ms REAL,
                    scenario TEXT,
                    client_ip TEXT
                )""",
                """CREATE TABLE IF NOT EXISTS sandbox_webhook_events (
                    id INTEGER PRIMARY KEY,
                    event_id TEXT UNIQUE NOT NULL,
                    sandbox_id TEXT NOT NULL,
                    partner_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivery_status TEXT DEFAULT 'pending',
                    delivery_attempts INTEGER DEFAULT 0,
                    last_attempt_at TIMESTAMP,
                    delivered_at TIMESTAMP,
                    error_message TEXT
                )""",
                """CREATE TABLE IF NOT EXISTS sandbox_usage_stats (
                    id INTEGER PRIMARY KEY,
                    sandbox_id TEXT UNIQUE NOT NULL,
                    total_requests INTEGER DEFAULT 0,
                    requests_today INTEGER DEFAULT 0,
                    requests_this_hour INTEGER DEFAULT 0,
                    average_latency_ms REAL DEFAULT 0,
                    success_rate REAL DEFAULT 100,
                    last_request_at TIMESTAMP,
                    stats_date DATE DEFAULT CURRENT_DATE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
            ]:
                await conn.execute(text(table_sql))
        
        await manager.initialize()
        
        # 1. Create sandbox
        sandbox = await manager.create_sandbox(
            partner_id="integration_partner",
            name="Integration Test",
            config=SandboxConfig(scenario=SandboxScenario.SUCCESS),
        )
        
        # 2. Create API key
        api_key, secret = await manager.create_api_key(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
        )
        
        # 3. Simulate multiple requests
        for i in range(10):
            response = await manager.simulate_request(
                api_key=api_key.key_id,
                method="GET",
                path=f"/api/v1/resource/{i}",
            )
            assert response["status"] == 200
        
        # 4. Create webhook event
        event = await manager.create_webhook_event(
            sandbox_id=sandbox.sandbox_id,
            partner_id=sandbox.partner_id,
            event_type="resource.created",
            payload={"id": "123"},
        )
        
        # 5. Check usage stats
        stats = await manager.get_usage_stats(sandbox.sandbox_id)
        assert stats.total_requests == 10
        
        # 6. Check logs
        logs = await manager.get_request_logs(sandbox.sandbox_id)
        assert len(logs) == 10
        
        # 7. Update config
        new_config = SandboxConfig(scenario=SandboxScenario.ERROR)
        await manager.update_sandbox_config(sandbox.sandbox_id, new_config)
        
        # 8. Test new config
        response = await manager.simulate_request(
            api_key=api_key.key_id,
            method="GET",
            path="/test",
        )
        assert response["status"] == 500
        
        # 9. Revoke key
        await manager.revoke_api_key(api_key.key_id)
        
        # 10. Delete sandbox
        await manager.delete_sandbox(sandbox.sandbox_id)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
