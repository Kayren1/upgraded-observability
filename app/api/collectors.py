from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import random

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.collector import CollectorAgent, CollectorJob
from ..schemas.collector import CollectorAgentResponse, CollectorJobResponse

router = APIRouter()


@router.get("/agents", response_model=List[CollectorAgentResponse])
def list_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    agents = db.query(CollectorAgent).all()
    return agents


@router.get("/agents/{agent_id}", response_model=CollectorAgentResponse)
def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    agent = db.query(CollectorAgent).filter(CollectorAgent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    return agent


@router.get("/jobs", response_model=List[CollectorJobResponse])
def list_jobs(
    status: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(CollectorJob)

    if status:
        query = query.filter(CollectorJob.status == status)

    jobs = query.order_by(CollectorJob.created_at.desc()).limit(limit).all()
    return jobs


@router.get("/jobs/{job_id}", response_model=CollectorJobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(CollectorJob).filter(CollectorJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return job


@router.get("/stats")
def get_collector_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get aggregated collector statistics"""
    total_agents = db.query(CollectorAgent).count()
    active_agents = db.query(CollectorAgent).filter(
        CollectorAgent.status == "active"
    ).count()

    total_jobs = db.query(CollectorJob).count()
    pending_jobs = db.query(CollectorJob).filter(
        CollectorJob.status == "pending"
    ).count()
    running_jobs = db.query(CollectorJob).filter(
        CollectorJob.status == "running"
    ).count()
    completed_jobs = db.query(CollectorJob).filter(
        CollectorJob.status == "completed"
    ).count()
    failed_jobs = db.query(CollectorJob).filter(
        CollectorJob.status == "failed"
    ).count()

    # Calculate average job duration
    completed = db.query(CollectorJob).filter(
        CollectorJob.status == "completed",
        CollectorJob.duration_ms.isnot(None)
    ).all()

    avg_duration = sum(j.duration_ms for j in completed) / len(completed) if completed else 0

    return {
        "agents": {
            "total": total_agents,
            "active": active_agents,
            "inactive": total_agents - active_agents
        },
        "jobs": {
            "total": total_jobs,
            "pending": pending_jobs,
            "running": running_jobs,
            "completed": completed_jobs,
            "failed": failed_jobs
        },
        "performance": {
            "avg_job_duration_ms": round(avg_duration, 2),
            "success_rate": round(completed_jobs / total_jobs * 100, 2) if total_jobs > 0 else 100
        }
    }


@router.get("/regions")
def get_regions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available collector regions"""
    agents = db.query(CollectorAgent).all()

    regions = {}
    for agent in agents:
        if agent.region not in regions:
            regions[agent.region] = {
                "region": agent.region,
                "agents": 0,
                "active_agents": 0,
                "total_capacity": 0,
                "current_load": 0
            }

        regions[agent.region]["agents"] += 1
        regions[agent.region]["total_capacity"] += agent.max_jobs
        regions[agent.region]["current_load"] += agent.current_jobs

        if agent.status == "active":
            regions[agent.region]["active_agents"] += 1

    return list(regions.values())
