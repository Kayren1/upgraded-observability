from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, Dict, List, Any


class SystemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    metrics_url: Optional[str] = None
    logs_url: Optional[str] = None
    traces_url: Optional[str] = None
    health_url: Optional[str] = None
    check_interval: int = 60
    timeout: int = 30
    headers: Optional[Dict[str, str]] = None
    region: str = "us-east-1"
    environment: str = "production"
    tags: Optional[Dict[str, str]] = None


class SystemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    metrics_url: Optional[str] = None
    logs_url: Optional[str] = None
    traces_url: Optional[str] = None
    health_url: Optional[str] = None
    check_interval: Optional[int] = None
    timeout: Optional[int] = None
    headers: Optional[Dict[str, str]] = None
    region: Optional[str] = None
    environment: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None


class SystemResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    description: Optional[str]
    metrics_url: Optional[str]
    logs_url: Optional[str]
    traces_url: Optional[str]
    health_url: Optional[str]
    status: str
    last_check: Optional[datetime]
    last_error: Optional[str]
    check_interval: int
    timeout: int
    headers: Optional[Dict[str, str]]
    region: str
    environment: str
    tags: Optional[Dict[str, str]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
