from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, List, Any


class MetricResponse(BaseModel):
    id: int
    system_id: int
    metric_name: str
    metric_type: str
    value: float
    labels: Optional[Dict[str, str]]
    timestamp: datetime

    class Config:
        from_attributes = True


class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    value: float


class TimeSeriesData(BaseModel):
    metric_name: str
    data: List[TimeSeriesPoint]


class SystemMetrics(BaseModel):
    system_id: int
    system_name: str
    cpu_usage: float
    memory_usage: float
    request_rate: float
    error_rate: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    status: str


class DashboardMetrics(BaseModel):
    total_systems: int
    active_systems: int
    total_alerts: int
    active_alerts: int
    total_requests: int
    error_rate: float
    avg_latency: float
    uptime_percentage: float
    systems: List[SystemMetrics]
    request_history: List[TimeSeriesPoint]
    error_history: List[TimeSeriesPoint]
    latency_history: List[TimeSeriesPoint]
