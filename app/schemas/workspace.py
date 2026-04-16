from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    max_systems: int = 10
    max_alerts: int = 50
    retention_days: int = 30


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    tenant_id: str
    owner_id: int
    is_active: bool
    max_systems: int
    max_alerts: int
    retention_days: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
