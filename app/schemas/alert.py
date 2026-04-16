from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict


class AlertRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    metric_name: str
    condition: str  # gt, lt, eq, gte, lte
    threshold: float
    duration: int = 60
    severity: str = "warning"
    notification_channels: Optional[List[Dict[str, str]]] = None


class AlertRuleResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    description: Optional[str]
    metric_name: str
    condition: str
    threshold: float
    duration: int
    severity: str
    notification_channels: Optional[List[Dict[str, str]]]
    is_active: bool
    is_muted: bool
    last_triggered: Optional[datetime]
    trigger_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertHistoryResponse(BaseModel):
    id: int
    alert_id: int
    status: str
    value: Optional[float]
    message: Optional[str]
    triggered_at: datetime
    resolved_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[int]

    class Config:
        from_attributes = True
