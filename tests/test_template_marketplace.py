"""
Comprehensive tests for Template Marketplace module.

Tests cover:
- Unit tests for templates, versions, reviews
- Integration tests for full workflows
- Security and edge case tests
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from backend.fastapi.api.utils.template_marketplace import (
    TemplateMarketplaceManager,
    TemplateFormat,
    TemplateCategory,
    TemplateStatus,
    LicenseType,
    ReviewStatus,
    Template,
    TemplateVersion,
    TemplateReview,
    UserTemplateLibrary,
    TemplateExportJob,
    TemplateVariable,
    TemplateValidator,
    get_marketplace_manager,
    reset_marketplace_manager
)


# Fixtures

def get_manager_sync():
    """Get marketplace manager synchronously."""
    reset_marketplace_manager()
    return asyncio.run(get_marketplace_manager())


@pytest.fixture
def marketplace_manager():
    """Fixture for marketplace manager."""
    manager = get_manager_sync()
    yield manager
    reset_marketplace_manager()


@pytest.fixture
def sample_template_data():
    """Sample template data for testing."""
    return {
        "name": "Test Template",
        "description": "A test template",
        "category": TemplateCategory.BUSINESS,
        "formats": [TemplateFormat.PDF, TemplateFormat.HTML],
        "created_by": "test_user"
    }


# Unit Tests

class TestTemplateFormats:
    """Test template format enums."""
    
    def test_format_values(self):
        """Test that all formats have correct values."""
        assert TemplateFormat.PDF.value == "pdf"
        assert TemplateFormat.EXCEL.value == "excel"
        assert TemplateFormat.CSV.value == "csv"
        assert TemplateFormat.HTML.value == "html"
    
    def test_all_formats(self):
        """Test that all expected formats exist."""
        formats = [f.value for f in TemplateFormat]
        assert "pdf" in formats
        assert "excel" in formats
        assert "json" in formats
        assert "markdown" in formats


class TestTemplateCategories:
    """Test template category enums."""
    
    def test_category_values(self):
        """Test that all categories have correct values."""
        assert TemplateCategory.ASSESSMENT.value == "assessment"
        assert TemplateCategory.FINANCIAL.value == "financial"
        assert TemplateCategory.CUSTOM.value == "custom"


class TestTemplateStatus:
    """Test template status enums."""
    
    def test_status_values(self):
        """Test that all statuses have correct values."""
        assert TemplateStatus.DRAFT.value == "draft"
        assert TemplateStatus.PUBLISHED.value == "published"
        assert TemplateStatus.ARCHIVED.value == "archived"


class TestLicenseTypes:
    """Test license type enums."""
    
    def test_license_values(self):
        """Test that all license types have correct values."""
        assert LicenseType.FREE.value == "free"
        assert LicenseType.PAID.value == "paid"
        assert LicenseType.SUBSCRIPTION.value == "subscription"


class TestTemplateValidator:
    """Test template validation utilities."""
    
    def test_valid_variable_name(self):
        """Test valid variable names."""
        assert TemplateValidator.validate_variable_name("name") is True
        assert TemplateValidator.validate_variable_name("user_name") is True
        assert TemplateValidator.validate_variable_name("_private") is True
        assert TemplateValidator.validate_variable_name("name123") is True
    
    def test_invalid_variable_name(self):
        """Test invalid variable names."""
        assert TemplateValidator.validate_variable_name("123name") is False
        assert TemplateValidator.validate_variable_name("name-with-dash") is False
        assert TemplateValidator.validate_variable_name("name with space") is False
        assert TemplateValidator.validate_variable_name("") is False
    
    def test_validate_template_content(self):
        """Test template content validation."""
        content = "Hello {{name}}, your email is {{email}}"
        variables = [
            TemplateVariable(name="name", display_name="Name", description="User name", variable_type="string"),
            TemplateVariable(name="email", display_name="Email", description="User email", variable_type="string")
        ]
        
        errors = TemplateValidator.validate_template_content(content, variables)
        assert len(errors) == 0
    
    def test_validate_undefined_variable(self):
        """Test detecting undefined variables."""
        content = "Hello {{name}}, your code is {{code}}"
        variables = [
            TemplateVariable(name="name", display_name="Name", description="User name", variable_type="string")
        ]
        
        errors = TemplateValidator.validate_template_content(content, variables)
        assert len(errors) == 2  # undefined 'code' and unused 'name'
        
        undefined_errors = [e for e in errors if e["type"] == "undefined_variable"]
        assert len(undefined_errors) == 1
        assert undefined_errors[0]["variable"] == "code"


class TestMarketplaceManagerInitialization:
    """Test marketplace manager initialization."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, marketplace_manager):
        """Test that manager initializes correctly."""
        assert marketplace_manager._initialized is True
        assert len(marketplace_manager.templates) > 0  # Sample templates loaded
    
    @pytest.mark.asyncio
    async def test_default_categories_initialized(self, marketplace_manager):
        """Test that default categories are initialized."""
        assert len(marketplace_manager.categories) == len(TemplateCategory)
        
        for category in TemplateCategory:
            assert category in marketplace_manager.categories
            assert "name" in marketplace_manager.categories[category]


class TestTemplateCRUD:
    """Test template CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_template(self, marketplace_manager, sample_template_data):
        """Test creating a template."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        assert template.template_id is not None
        assert template.name == sample_template_data["name"]
        assert template.status == TemplateStatus.DRAFT
        assert template.license_type == LicenseType.FREE
    
    @pytest.mark.asyncio
    async def test_create_paid_template(self, marketplace_manager):
        """Test creating a paid template."""
        template = await marketplace_manager.create_template(
            name="Premium Template",
            description="A premium template",
            category=TemplateCategory.FINANCIAL,
            formats=[TemplateFormat.PDF],
            created_by="test_user",
            license_type=LicenseType.PAID,
            price=29.99
        )
        
        assert template.license_type == LicenseType.PAID
        assert template.price == 29.99
    
    @pytest.mark.asyncio
    async def test_get_template(self, marketplace_manager, sample_template_data):
        """Test retrieving a template."""
        created = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        retrieved = await marketplace_manager.get_template(created.template_id)
        assert retrieved is not None
        assert retrieved.template_id == created.template_id
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_template(self, marketplace_manager):
        """Test retrieving non-existent template returns None."""
        template = await marketplace_manager.get_template("nonexistent_id")
        assert template is None
    
    @pytest.mark.asyncio
    async def test_update_template(self, marketplace_manager, sample_template_data):
        """Test updating a template."""
        created = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        updated = await marketplace_manager.update_template(
            created.template_id,
            {"name": "Updated Name", "description": "Updated Description"},
            "test_user"
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated Description"
    
    @pytest.mark.asyncio
    async def test_delete_template(self, marketplace_manager, sample_template_data):
        """Test deleting a template."""
        created = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        success = await marketplace_manager.delete_template(created.template_id)
        assert success is True
        
        # Verify deletion
        template = await marketplace_manager.get_template(created.template_id)
        assert template is None
    
    @pytest.mark.asyncio
    async def test_list_templates(self, marketplace_manager):
        """Test listing templates."""
        result = await marketplace_manager.list_templates()
        assert "templates" in result
        assert "total" in result
        assert "has_more" in result


class TestVersionManagement:
    """Test template version management."""
    
    @pytest.mark.asyncio
    async def test_create_version(self, marketplace_manager, sample_template_data):
        """Test creating a template version."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        version = await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.0.0",
            content="<html>{{name}}</html>",
            changes_description="Initial version",
            created_by="test_user"
        )
        
        assert version is not None
        assert version.version_number == "1.0.0"
        assert version.is_current is True
    
    @pytest.mark.asyncio
    async def test_get_current_version(self, marketplace_manager, sample_template_data):
        """Test getting current version."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.0.0",
            content="<html>V1</html>",
            changes_description="Initial version",
            created_by="test_user"
        )
        
        current = await marketplace_manager.get_current_version(template.template_id)
        assert current is not None
        assert current.version_number == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_set_current_version(self, marketplace_manager, sample_template_data):
        """Test setting a specific version as current."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        v1 = await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.0.0",
            content="<html>V1</html>",
            changes_description="Initial version",
            created_by="test_user"
        )
        
        v2 = await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.1.0",
            content="<html>V2</html>",
            changes_description="Updated version",
            created_by="test_user",
            make_current=False
        )
        
        # Set v1 as current
        success = await marketplace_manager.set_current_version(
            template.template_id,
            v1.version_id
        )
        assert success is True
        
        current = await marketplace_manager.get_current_version(template.template_id)
        assert current.version_id == v1.version_id


class TestReviewSystem:
    """Test review and rating system."""
    
    @pytest.mark.asyncio
    async def test_add_review(self, marketplace_manager, sample_template_data):
        """Test adding a review."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        review = await marketplace_manager.add_review(
            template_id=template.template_id,
            user_id="user_123",
            rating=5,
            title="Great template!",
            comment="This is an excellent template."
        )
        
        assert review is not None
        assert review.rating == 5
        assert review.template_id == template.template_id
        
        # Check template rating updated
        template = await marketplace_manager.get_template(template.template_id)
        assert template.total_reviews == 1
        assert template.average_rating == 5.0
    
    @pytest.mark.asyncio
    async def test_add_multiple_reviews(self, marketplace_manager, sample_template_data):
        """Test adding multiple reviews updates average correctly."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        await marketplace_manager.add_review(template.template_id, "user1", 5)
        await marketplace_manager.add_review(template.template_id, "user2", 3)
        await marketplace_manager.add_review(template.template_id, "user3", 4)
        
        template = await marketplace_manager.get_template(template.template_id)
        assert template.total_reviews == 3
        assert template.average_rating == 4.0  # (5+3+4)/3
    
    @pytest.mark.asyncio
    async def test_get_reviews(self, marketplace_manager, sample_template_data):
        """Test getting reviews for a template."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        await marketplace_manager.add_review(template.template_id, "user1", 5)
        await marketplace_manager.add_review(template.template_id, "user2", 4)
        
        reviews = await marketplace_manager.get_reviews(template.template_id)
        assert len(reviews) == 2


class TestUserLibrary:
    """Test user library management."""
    
    @pytest.mark.asyncio
    async def test_add_to_library(self, marketplace_manager, sample_template_data):
        """Test adding template to library."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        # Create version first
        version = await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.0.0",
            content="<html>Test</html>",
            changes_description="Initial",
            created_by="test_user"
        )
        
        entry = await marketplace_manager.add_to_library(
            user_id="user_123",
            template_id=template.template_id
        )
        
        assert entry is not None
        assert entry.user_id == "user_123"
        assert entry.template_id == template.template_id
    
    @pytest.mark.asyncio
    async def test_get_user_library(self, marketplace_manager, sample_template_data):
        """Test getting user's library."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.0.0",
            content="<html>Test</html>",
            changes_description="Initial",
            created_by="test_user"
        )
        
        await marketplace_manager.add_to_library("user_lib", template.template_id)
        
        library = await marketplace_manager.get_user_library("user_lib")
        assert len(library) == 1
        assert library[0].user_id == "user_lib"
    
    @pytest.mark.asyncio
    async def test_remove_from_library(self, marketplace_manager, sample_template_data):
        """Test removing template from library."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.0.0",
            content="<html>Test</html>",
            changes_description="Initial",
            created_by="test_user"
        )
        
        entry = await marketplace_manager.add_to_library("user_remove", template.template_id)
        
        success = await marketplace_manager.remove_from_library("user_remove", entry.library_id)
        assert success is True
        
        library = await marketplace_manager.get_user_library("user_remove")
        assert len(library) == 0


class TestExportJobs:
    """Test export job processing."""
    
    @pytest.mark.asyncio
    async def test_create_export_job(self, marketplace_manager, sample_template_data):
        """Test creating an export job."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.0.0",
            content="<html>{{name}}</html>",
            changes_description="Initial",
            created_by="test_user"
        )
        
        job = await marketplace_manager.create_export_job(
            template_id=template.template_id,
            user_id="user_123",
            output_format=TemplateFormat.PDF,
            data={"name": "Test User"}
        )
        
        assert job is not None
        assert job.status == "pending"
        assert job.output_format == TemplateFormat.PDF
    
    @pytest.mark.asyncio
    async def test_update_export_job_status(self, marketplace_manager, sample_template_data):
        """Test updating export job status."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.0.0",
            content="<html>Test</html>",
            changes_description="Initial",
            created_by="test_user"
        )
        
        job = await marketplace_manager.create_export_job(
            template_id=template.template_id,
            user_id="user_123",
            output_format=TemplateFormat.PDF,
            data={}
        )
        
        updated = await marketplace_manager.update_export_job_status(
            job.job_id,
            "completed",
            output_url="https://example.com/export.pdf",
            file_size_bytes=1024,
            checksum="abc123"
        )
        
        assert updated is not None
        assert updated.status == "completed"
        assert updated.output_url == "https://example.com/export.pdf"


class TestAnalytics:
    """Test analytics tracking."""
    
    @pytest.mark.asyncio
    async def test_track_event(self, marketplace_manager, sample_template_data):
        """Test tracking an event."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        await marketplace_manager.track_event(
            template_id=template.template_id,
            event_type="view",
            user_id="user_123"
        )
        
        # Check template view count updated
        template = await marketplace_manager.get_template(template.template_id)
        assert template.view_count == 1
    
    @pytest.mark.asyncio
    async def test_get_analytics(self, marketplace_manager, sample_template_data):
        """Test getting analytics."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        await marketplace_manager.track_event(template.template_id, "view", "user1")
        await marketplace_manager.track_event(template.template_id, "view", "user2")
        await marketplace_manager.track_event(template.template_id, "download", "user1")
        
        events = await marketplace_manager.get_analytics(template_id=template.template_id)
        assert len(events) == 3


class TestStatistics:
    """Test statistics generation."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, marketplace_manager):
        """Test getting marketplace statistics."""
        stats = await marketplace_manager.get_statistics()
        
        assert "templates" in stats
        assert "engagement" in stats
        assert "jobs" in stats
        
        assert "total" in stats["templates"]
        assert "total_downloads" in stats["engagement"]


# Integration Tests

class TestIntegrationWorkflows:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_full_template_lifecycle(self, marketplace_manager):
        """Test complete template lifecycle from creation to publication."""
        # Create template
        template = await marketplace_manager.create_template(
            name="Integration Test Template",
            description="Testing full lifecycle",
            category=TemplateCategory.BUSINESS,
            formats=[TemplateFormat.PDF],
            created_by="integration_user"
        )
        
        # Create version
        version = await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.0.0",
            content="<html>Integration Test</html>",
            changes_description="Initial version",
            created_by="integration_user"
        )
        
        # Publish template
        await marketplace_manager.update_template(
            template.template_id,
            {"status": TemplateStatus.PUBLISHED},
            "integration_user"
        )
        
        # Add review
        await marketplace_manager.add_review(
            template_id=template.template_id,
            user_id="reviewer",
            rating=5,
            comment="Excellent template!"
        )
        
        # Get final state
        final = await marketplace_manager.get_template(template.template_id)
        assert final.status == TemplateStatus.PUBLISHED
        assert final.total_reviews == 1
        assert final.average_rating == 5.0
    
    @pytest.mark.asyncio
    async def test_full_export_workflow(self, marketplace_manager):
        """Test complete export workflow."""
        # Create template with version
        template = await marketplace_manager.create_template(
            name="Export Test Template",
            description="Testing export workflow",
            category=TemplateCategory.BUSINESS,
            formats=[TemplateFormat.PDF, TemplateFormat.HTML],
            created_by="test_user"
        )
        
        await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.0.0",
            content="<html>{{title}}</html>",
            changes_description="Initial",
            created_by="test_user"
        )
        
        # Create export job
        job = await marketplace_manager.create_export_job(
            template_id=template.template_id,
            user_id="exporter",
            output_format=TemplateFormat.PDF,
            data={"title": "Test Document"}
        )
        
        assert job.status == "pending"
        
        # Complete job
        await marketplace_manager.update_export_job_status(
            job.job_id,
            "completed",
            output_url="https://example.com/output.pdf",
            file_size_bytes=2048
        )
        
        final_job = await marketplace_manager.get_export_job(job.job_id)
        assert final_job.status == "completed"


# Edge Case Tests

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_create_template_without_formats(self, marketplace_manager):
        """Test creating template with empty formats list."""
        template = await marketplace_manager.create_template(
            name="No Formats Template",
            description="Template with no formats",
            category=TemplateCategory.CUSTOM,
            formats=[],  # Empty
            created_by="test_user"
        )
        
        assert template is not None
        assert len(template.formats) == 0
    
    @pytest.mark.asyncio
    async def test_create_version_for_nonexistent_template(self, marketplace_manager):
        """Test creating version for non-existent template returns None."""
        version = await marketplace_manager.create_version(
            template_id="nonexistent",
            version_number="1.0.0",
            content="<html>Test</html>",
            changes_description="Test",
            created_by="test_user"
        )
        
        assert version is None
    
    @pytest.mark.asyncio
    async def test_add_review_with_invalid_rating(self, marketplace_manager, sample_template_data):
        """Test adding review with invalid rating raises error."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        with pytest.raises(ValueError):
            await marketplace_manager.add_review(
                template_id=template.template_id,
                user_id="user_123",
                rating=6  # Invalid rating
            )
    
    @pytest.mark.asyncio
    async def test_export_with_unsupported_format(self, marketplace_manager, sample_template_data):
        """Test export with unsupported format raises error."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=[TemplateFormat.PDF],  # Only PDF
            created_by=sample_template_data["created_by"]
        )
        
        await marketplace_manager.create_version(
            template_id=template.template_id,
            version_number="1.0.0",
            content="<html>Test</html>",
            changes_description="Initial",
            created_by="test_user"
        )
        
        with pytest.raises(ValueError):
            await marketplace_manager.create_export_job(
                template_id=template.template_id,
                user_id="user_123",
                output_format=TemplateFormat.EXCEL,  # Not supported
                data={}
            )


# Performance Tests

class TestPerformance:
    """Performance-related tests."""
    
    @pytest.mark.asyncio
    async def test_bulk_template_creation(self, marketplace_manager):
        """Test creating many templates."""
        start_time = datetime.utcnow()
        
        for i in range(50):
            await marketplace_manager.create_template(
                name=f"Bulk Template {i}",
                description=f"Description {i}",
                category=TemplateCategory.CUSTOM,
                formats=[TemplateFormat.PDF],
                created_by="bulk_user"
            )
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        assert duration < 5  # Should complete in less than 5 seconds
        assert len(marketplace_manager.templates) >= 50
    
    @pytest.mark.asyncio
    async def test_bulk_analytics_tracking(self, marketplace_manager, sample_template_data):
        """Test tracking many analytics events."""
        template = await marketplace_manager.create_template(
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            category=sample_template_data["category"],
            formats=sample_template_data["formats"],
            created_by=sample_template_data["created_by"]
        )
        
        start_time = datetime.utcnow()
        
        for i in range(100):
            await marketplace_manager.track_event(
                template_id=template.template_id,
                event_type="view",
                user_id=f"user_{i}"
            )
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        assert duration < 2  # Should complete quickly
        assert len(marketplace_manager.analytics) >= 100


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
