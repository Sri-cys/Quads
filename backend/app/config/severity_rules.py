"""
Severity determination rules and thresholds for Quads Agent 1 (Impact Analysis).
All constants are centrally configurable here without touching impact_agent.py or impact_service.py.
"""

# Days of cover threshold for CRITICAL severity
CRITICAL_DAYS_OF_COVER_THRESHOLD: float = 3.0

# Available inventory threshold for CRITICAL severity when a supply gap exists
CRITICAL_INVENTORY_ZERO_THRESHOLD: float = 0.0

# Days of cover threshold for HIGH severity
HIGH_DAYS_OF_COVER_THRESHOLD: float = 7.0

# Days of cover threshold for MEDIUM severity
MEDIUM_DAYS_OF_COVER_THRESHOLD: float = 14.0

# Severity Tier Names
SEVERITY_CRITICAL: str = "CRITICAL"
SEVERITY_HIGH: str = "HIGH"
SEVERITY_MEDIUM: str = "MEDIUM"
SEVERITY_LOW: str = "LOW"

# Valid Recovery Priority Decisions at Checkpoint 1
VALID_CHECKPOINT_PRIORITIES: set[str] = {"TIME", "COST", "RISK", "BALANCED"}
