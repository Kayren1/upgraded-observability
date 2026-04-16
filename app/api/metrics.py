from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import random

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.workspace import Workspace
from ..models.system import MonitoredSystem
from ..models.alert import AlertRule
from ..schemas.metrics import (
    MetricResponse,
    DashboardMetrics,
    SystemMetrics,
    TimeSeriesPoint
)

router = APIRouter()


def generate_time_series(hours: int = 24, interval_minutes: int = 5) -> List[TimeSeriesPoint]:
    """Generate simulated time series data"""
    points = []
    now = datetime.utcnow()
    base_value = random.uniform(50, 200)

    for i in range(hours * 60 // interval_minutes):
        timestamp = now - timedelta(minutes=i * interval_minutes)
        # Add some variance
        value = base_value + random.gauss(0, 10) + 20 * (0.5 - random.random())
        value = max(0, value)
        points.append(TimeSeriesPoint(timestamp=timestamp, value=round(value, 2)))

    return list(reversed(points))


def generate_system_metrics(system: MonitoredSystem) -> SystemMetrics:
    """Generate simulated metrics for a system"""
    return SystemMetrics(
        system_id=system.id,
        system_name=system.name,
        cpu_usage=round(random.uniform(10, 80), 2),
        memory_usage=round(random.uniform(20, 70), 2),
        request_rate=round(random.uniform(100, 5000), 2),
        error_rate=round(random.uniform(0, 5), 3),
        latency_p50=round(random.uniform(10, 100), 2),
        latency_p95=round(random.uniform(100, 300), 2),
        latency_p99=round(random.uniform(200, 500), 2),
        status=system.status
    )


@router.get("/dashboard/{workspace_id}", response_model=DashboardMetrics)
def get_dashboard_metrics(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    # Get systems
    systems = db.query(MonitoredSystem).filter(
        MonitoredSystem.workspace_id == workspace.id
    ).all()

    # Get alerts
    alerts = db.query(AlertRule).filter(
        AlertRule.workspace_id == workspace.id
    ).all()

    active_systems = len([s for s in systems if s.status == "active"])
    active_alerts = len([a for a in alerts if a.is_active and not a.is_muted])

    # Generate simulated metrics
    system_metrics = [generate_system_metrics(s) for s in systems]

    # Calculate aggregates
    total_requests = sum(s.request_rate for s in system_metrics) if system_metrics else 0
    avg_error_rate = sum(s.error_rate for s in system_metrics) / len(system_metrics) if system_metrics else 0
    avg_latency = sum(s.latency_p50 for s in system_metrics) / len(system_metrics) if system_metrics else 0

    return DashboardMetrics(
        total_systems=len(systems),
        active_systems=active_systems,
        total_alerts=len(alerts),
        active_alerts=active_alerts,
        total_requests=int(total_requests),
        error_rate=round(avg_error_rate, 3),
        avg_latency=round(avg_latency, 2),
        uptime_percentage=round(random.uniform(99.5, 100), 2),
        systems=system_metrics,
        request_history=generate_time_series(),
        error_history=generate_time_series(),
        latency_history=generate_time_series()
    )


@router.get("/system/{system_id}/timeseries")
def get_system_timeseries(
    system_id: int,
    metric: str = "requests",
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    system = db.query(MonitoredSystem).join(Workspace).filter(
        MonitoredSystem.id == system_id,
        Workspace.owner_id == current_user.id
    ).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System not found"
        )

    return {
        "system_id": system_id,
        "metric": metric,
        "data": generate_time_series(hours=hours)
    }


@router.get("/realtime/{workspace_id}")
def get_realtime_metrics(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get real-time metrics snapshot for all systems"""
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    systems = db.query(MonitoredSystem).filter(
        MonitoredSystem.workspace_id == workspace.id
    ).all()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "systems": [
            {
                "id": s.id,
                "name": s.name,
                "status": s.status,
                "cpu": round(random.uniform(10, 80), 2),
                "memory": round(random.uniform(20, 70), 2),
                "requests_per_second": round(random.uniform(10, 500), 2),
                "errors_per_second": round(random.uniform(0, 5), 2),
                "latency_ms": round(random.uniform(10, 200), 2)
            }
            for s in systems
        ]
    }
