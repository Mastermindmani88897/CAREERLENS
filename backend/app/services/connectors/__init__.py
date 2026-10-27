"""
Phase 26 External Opportunity Connectors Registry.

Exposes the connector registry across Wave 1 and Wave 2:
Wave 1:
- RemotiveConnector
- ArbeitnowConnector
- CodeforcesConnector
- GreenhouseConnector

Wave 2:
- AdzunaConnector
- USAJOBSConnector
- LeverConnector
- RemoteOKConnector

Orchestration:
- ConnectorOrchestrator
- BaseOpportunityConnector, ConnectorStatus, ConnectorBatchResult, ConnectorRunSummary
"""

from app.services.connectors.adzuna import AdzunaConnector
from app.services.connectors.arbeitnow import ArbeitnowConnector
from app.services.connectors.base import (
    BaseOpportunityConnector,
    ConnectorBatchResult,
    ConnectorRunSummary,
    ConnectorStatus,
)
from app.services.connectors.codeforces import CodeforcesConnector
from app.services.connectors.greenhouse import GreenhouseConnector
from app.services.connectors.lever import LeverConnector
from app.services.connectors.orchestrator import ConnectorOrchestrator, get_all_connectors
from app.services.connectors.remoteok import RemoteOKConnector
from app.services.connectors.remotive import RemotiveConnector
from app.services.connectors.usajobs import USAJOBSConnector

__all__ = [
    "BaseOpportunityConnector",
    "ConnectorBatchResult",
    "ConnectorRunSummary",
    "ConnectorStatus",
    "ConnectorOrchestrator",
    "get_all_connectors",
    # Wave 1
    "RemotiveConnector",
    "ArbeitnowConnector",
    "CodeforcesConnector",
    "GreenhouseConnector",
    # Wave 2
    "AdzunaConnector",
    "USAJOBSConnector",
    "LeverConnector",
    "RemoteOKConnector",
]
