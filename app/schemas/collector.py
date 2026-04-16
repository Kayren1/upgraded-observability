from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CollectorAgentResponse(BaseModel):
    id: int
    name: str
    region: str
    status: str
    last_heartbeat: Optional[datetime]
    current_jobs: int
    max_jobs: int
    cpu_usage: float
    memory_usage: float
    ip_address: Optional[str]
    hostname: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectorJobResponse(BaseModel):
    id: int
    system_id: int
    agent_id: Optional[int]
    job_type: str
    status: str
    priority: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    error_message: Optional[str]
    metrics_collected: int
    bytes_processed: int
    created_at: datetime
    scheduled_at: Optional[datetime]

    class Config:
        from_attributes = True
