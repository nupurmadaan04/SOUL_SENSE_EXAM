import hashlib
import json
import logging
from datetime import datetime, timezone
UTC = timezone.utc
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from ..models import AuditLog

logger = logging.getLogger(__name__)

class TamperEvidentAuditService:
    """
    Tamper-evident audit logging service with cryptographic hash chaining (#1265).

    Implements SHA-256 hash chaining to ensure log integrity:
    - Each log entry contains hash of previous entry (previous_hash)
    - Each entry has its own content hash (current_hash)
    - Running chain hash for efficient validation (chain_hash)

    This prevents unauthorized modification, deletion, or insertion of log entries.
    """

    # Genesis hash for the first log entry in the chain
    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    @classmethod
    def _generate_content_hash(cls, user_id: int, action: str, details: str,
                              timestamp: datetime, previous_hash: str) -> str:
        """
        Generate SHA-256 hash of log entry content.

        Includes all immutable fields that define the log entry's identity.
        """
        content = {
            "user_id": user_id,
            "action": action,
            "details": details or "",
            "timestamp": timestamp.isoformat(),
            "previous_hash": previous_hash
        }
        content_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()

    @classmethod
    def _generate_chain_hash(cls, current_hash: str, previous_chain_hash: str) -> str:
        """
        Generate running chain hash by combining current entry hash with previous chain hash.
        """
        combined = f"{previous_chain_hash}:{current_hash}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    @classmethod
    async def get_last_log_entry(cls, db_session: AsyncSession) -> Optional[AuditLog]:
        """
        Get the most recent audit log entry for hash chaining.
        """
        try:
            stmt = select(AuditLog).order_by(desc(AuditLog.id)).limit(1)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get last log entry: {e}")
            return None

    @classmethod
    async def log_event_with_hash_chain(cls, user_id: int, action: str,
                                       ip_address: Optional[str] = "SYSTEM",
                                       user_agent: Optional[str] = None,
                                       details: Optional[Dict[str, Any]] = None,
                                       db_session: AsyncSession = None) -> bool:
        """
        Log a security-critical event with tamper-evident hash chaining.

        Creates a new audit log entry with cryptographic links to previous entries,
        ensuring the integrity of the entire audit trail.
        """
        if not db_session:
            logger.error("TamperEvidentAuditService requires a db_session")
            return False

        try:
            # Get the last log entry for chaining
            last_entry = await cls.get_last_log_entry(db_session)

            # Determine previous hash and chain hash
            if last_entry:
                previous_hash = last_entry.current_hash
                previous_chain_hash = last_entry.chain_hash
            else:
                # First entry in the chain
                previous_hash = cls.GENESIS_HASH
                previous_chain_hash = cls.GENESIS_HASH

            # Sanitize inputs (reuse logic from AuditService)
            safe_ua = (user_agent[:250] + "...") if user_agent and len(user_agent) > 250 else user_agent
            safe_details = "{}"
            if details:
                # Filter to allowed fields to prevent PII leakage
                allowed_fields = {
                    "status", "reason", "method", "device", "location",
                    "changed_field", "old_value", "outcome", "session_id",
                    "ip_address", "user_agent", "risk_score", "anomaly_type"
                }
                filtered = {k: v for k, v in details.items() if k in allowed_fields}
                try:
                    safe_details = json.dumps(filtered, sort_keys=True)
                except Exception as e:
                    logger.warning(f"Failed to serialize audit details: {e}")
                    safe_details = "{}"

            timestamp = datetime.now(UTC)

            # Generate content hash for this entry
            current_hash = cls._generate_content_hash(
                user_id=user_id,
                action=action,
                details=safe_details,
                timestamp=timestamp,
                previous_hash=previous_hash
            )

            # Generate running chain hash
            chain_hash = cls._generate_chain_hash(current_hash, previous_chain_hash)

            # Create the tamper-evident log entry
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                details=safe_details,
                timestamp=timestamp,
                previous_hash=previous_hash,
                current_hash=current_hash,
                chain_hash=chain_hash
            )

            db_session.add(log_entry)
            await db_session.commit()

            logger.info(f"TAMPER-EVIDENT AUDIT LOG: User {user_id} performed {action} - Chain hash: {chain_hash[:16]}...")
            return True

        except Exception as e:
            await db_session.rollback()
            logger.critical(f"TAMPER-EVIDENT AUDIT LOG FAILURE: User {user_id} performed {action}. Error: {e}")
            return False

    @classmethod
    async def validate_chain_integrity(cls, db_session: AsyncSession,
                                      max_entries: int = 1000) -> Tuple[bool, List[str]]:
        """
        Validate the integrity of the audit log chain.

        Checks that all hash links are valid and no entries have been tampered with.
        Returns (is_valid, error_messages) tuple.
        """
        errors = []

        try:
            # Get all audit log entries ordered by ID (chronological)
            stmt = select(AuditLog).order_by(AuditLog.id).limit(max_entries)
            result = await db_session.execute(stmt)
            entries = result.scalars().all()

            if not entries:
                return True, []  # Empty chain is valid

            expected_previous_hash = cls.GENESIS_HASH
            expected_chain_hash = cls.GENESIS_HASH

            for entry in entries:
                # Validate content hash
                calculated_content_hash = cls._generate_content_hash(
                    user_id=entry.user_id,
                    action=entry.action,
                    details=entry.details or "",
                    timestamp=entry.timestamp,
                    previous_hash=entry.previous_hash
                )

                if calculated_content_hash != entry.current_hash:
                    errors.append(f"Entry {entry.id}: Content hash mismatch - expected {calculated_content_hash}, got {entry.current_hash}")

                # Validate previous hash link
                if entry.previous_hash != expected_previous_hash:
                    errors.append(f"Entry {entry.id}: Previous hash link broken - expected {expected_previous_hash}, got {entry.previous_hash}")

                # Validate chain hash
                calculated_chain_hash = cls._generate_chain_hash(entry.current_hash, expected_chain_hash)
                if calculated_chain_hash != entry.chain_hash:
                    errors.append(f"Entry {entry.id}: Chain hash mismatch - expected {calculated_chain_hash}, got {entry.chain_hash}")

                # Update expected values for next iteration
                expected_previous_hash = entry.current_hash
                expected_chain_hash = entry.chain_hash

            return len(errors) == 0, errors

        except Exception as e:
            errors.append(f"Chain validation failed with exception: {e}")
            return False, errors

    @classmethod
    async def get_chain_status(cls, db_session: AsyncSession) -> Dict[str, Any]:
        """
        Get comprehensive status of the audit log chain.
        """
        try:
            # Get total count
            stmt = select(func.count(AuditLog.id))
            result = await db_session.execute(stmt)
            total_entries = result.scalar() or 0

            # Get last entry
            last_entry = await cls.get_last_log_entry(db_session)

            # Validate recent entries (last 100)
            is_valid, errors = await cls.validate_chain_integrity(db_session, max_entries=100)

            return {
                "total_entries": total_entries,
                "last_entry_id": last_entry.id if last_entry else None,
                "last_chain_hash": last_entry.chain_hash if last_entry else None,
                "chain_valid": is_valid,
                "validation_errors": errors[:5],  # Limit error messages
                "genesis_hash": cls.GENESIS_HASH
            }

        except Exception as e:
            logger.error(f"Failed to get chain status: {e}")
            return {
                "error": str(e),
                "total_entries": 0,
                "chain_valid": False
            }

    @classmethod
    async def detect_tampering(cls, db_session: AsyncSession) -> List[Dict[str, Any]]:
        """
        Detect potential tampering by finding broken hash links.
        Returns list of suspicious entries with details.
        """
        suspicious_entries = []

        try:
            # Get all entries
            stmt = select(AuditLog).order_by(AuditLog.id)
            result = await db_session.execute(stmt)
            entries = result.scalars().all()

            expected_previous_hash = cls.GENESIS_HASH

            for entry in entries:
                # Check for hash link breaks
                if entry.previous_hash != expected_previous_hash:
                    suspicious_entries.append({
                        "entry_id": entry.id,
                        "user_id": entry.user_id,
                        "action": entry.action,
                        "timestamp": entry.timestamp.isoformat(),
                        "issue": "broken_previous_hash_link",
                        "expected": expected_previous_hash,
                        "actual": entry.previous_hash
                    })

                # Check for content hash validity
                calculated_content_hash = cls._generate_content_hash(
                    user_id=entry.user_id,
                    action=entry.action,
                    details=entry.details or "",
                    timestamp=entry.timestamp,
                    previous_hash=entry.previous_hash
                )

                if calculated_content_hash != entry.current_hash:
                    suspicious_entries.append({
                        "entry_id": entry.id,
                        "user_id": entry.user_id,
                        "action": entry.action,
                        "timestamp": entry.timestamp.isoformat(),
                        "issue": "content_hash_mismatch",
                        "expected": calculated_content_hash,
                        "actual": entry.current_hash
                    })

                expected_previous_hash = entry.current_hash

            return suspicious_entries

        except Exception as e:
            logger.error(f"Failed to detect tampering: {e}")
            return [{"error": str(e)}]