"""
Phase 26.3 Wave 1 External Opportunity Connectors.

Exposes the connector registry and the four Wave 1 connectors:
- RemotiveConnector
- ArbeitnowConnector
- CodeforcesConnector
- GreenhouseConnector
"""

from app.services.connectors.arbeitnow import ArbeitnowConnector
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorBatchResult,
    ConnectorRunSummary,
    ConnectorStatus,
)
from app.services.connectors.codeforces import CodeforcesConnector
from app.services.connectors.greenhouse import GreenhouseConnector
from app.services.connectors.orchestrator import ConnectorOrchestrator
from app.services.connectors.remotive import RemotiveConnector

__all__ = [
    "BaseOpportunityConnector",
    "ConnectorBatchResult",
    "ConnectorRunSummary",
    "ConnectorStatus",
    "ConnectorOrchestrator",
    "RemotiveConnector",
    "ArbeitnowConnector",
    "CodeforcesConnector",
    "GreenhouseConnector",
]
