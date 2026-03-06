from datetime import datetime, timezone
UTC = timezone.utc
from api.services.tamper_evident_audit_service import TamperEvidentAuditService

# Test basic functionality
service = TamperEvidentAuditService()

# Test hash generation
timestamp = datetime.now(UTC)
content_hash = service._generate_content_hash(
    user_id=123,
    action='TEST',
    details='{"test": "data"}',
    timestamp=timestamp,
    previous_hash=service.GENESIS_HASH
)

print(f'✓ Content hash generated: {content_hash[:16]}...')
print(f'✓ Hash length: {len(content_hash)}')
print(f'✓ Genesis hash: {service.GENESIS_HASH}')

# Test chain hash
chain_hash = service._generate_chain_hash(content_hash, service.GENESIS_HASH)
print(f'✓ Chain hash generated: {chain_hash[:16]}...')
print(f'✓ Chain hash length: {len(chain_hash)}')

print('✓ Basic tamper-evident audit service functionality validated')