from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class CollectorAgent(Base):
    __tablename__ = "collector_agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    region = Column(String(50), nullable=False)

    # Status
    status = Column(String(50), default="active")  # active, inactive, maintenance
    last_heartbeat = Column(DateTime, nullable=True)

    # Capacity
    current_jobs = Column(Integer, default=0)
    max_jobs = Column(Integer, default=100)
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)

    # Network info
    ip_address = Column(String(50), nullable=True)
    hostname = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    jobs = relationship("CollectorJob", back_populates="agent")

    def __repr__(self):
        return f"<CollectorAgent {self.name} ({self.region})>"


class CollectorJob(Base):
    __tablename__ = "collector_jobs"

    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(Integer, ForeignKey("monitored_systems.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("collector_agents.id"), nullable=True)

    # Job details
    job_type = Column(String(50), nullable=False)  # metrics, logs, traces, health
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    priority = Column(Integer, default=5)

    # Execution details
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Result summary
    metrics_collected = Column(Integer, default=0)
    bytes_processed = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_at = Column(DateTime, nullable=True)

    # Relationships
    system = relationship("MonitoredSystem", back_populates="collector_jobs")
    agent = relationship("CollectorAgent", back_populates="jobs")

    def __repr__(self):
        return f"<CollectorJob {self.id} ({self.job_type})>"
