"""Human-in-the-Loop Approval & Review Gate Engine."""

import enum
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class ApprovalRequest:
    request_id: str
    action_type: str  # e.g., "FILE_DELETE", "COMMAND_EXEC", "MULTI_FILE_REFACTOR", "GIT_COMMIT"
    description: str
    risk_level: RiskLevel
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action_type": self.action_type,
            "description": self.description,
            "risk_level": self.risk_level.value if hasattr(self.risk_level, "value") else str(self.risk_level),
            "payload": self.payload,
            "status": self.status,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "reason": self.reason,
        }


class HumanApprovalGate:
    """Manages pending human verification gates for critical agent operations."""

    def __init__(self):
        self._requests: Dict[str, ApprovalRequest] = {}

    def request_approval(
        self,
        action_type: str,
        description: str,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        payload: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        req_id = f"appr_{uuid.uuid4().hex[:8]}"
        req = ApprovalRequest(
            request_id=req_id,
            action_type=action_type,
            description=description,
            risk_level=risk_level,
            payload=payload or {},
        )
        self._requests[req_id] = req
        return req

    def approve(self, request_id: str, approver: str = "human_operator", reason: str = "Approved by engineer") -> ApprovalRequest:
        req = self._requests.get(request_id)
        if not req:
            raise ValueError(f"Approval request '{request_id}' not found.")
        req.status = "APPROVED"
        req.resolved_at = datetime.utcnow().isoformat()
        req.resolved_by = approver
        req.reason = reason
        return req

    def reject(self, request_id: str, rejector: str = "human_operator", reason: str = "Rejected by engineer") -> ApprovalRequest:
        req = self._requests.get(request_id)
        if not req:
            raise ValueError(f"Approval request '{request_id}' not found.")
        req.status = "REJECTED"
        req.resolved_at = datetime.utcnow().isoformat()
        req.resolved_by = rejector
        req.reason = reason
        return req

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def list_requests(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        reqs = list(self._requests.values())
        if status and status != "ALL":
            reqs = [r for r in reqs if r.status == status]
        return [r.to_dict() for r in reqs]
