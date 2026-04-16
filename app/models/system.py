from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class MonitoredSystem(Base):
    __tablename__ = "monitored_systems"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Endpoints
    metrics_url = Column(String(500), nullable=True)
    logs_url = Column(String(500), nullable=True)
    traces_url = Column(String(500), nullable=True)
    health_url = Column(String(500), nullable=True)

    # Status
    status = Column(String(50), default="pending")  # pending, active, error, paused
    last_check = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    # Configuration
    check_interval = Column(Integer, default=60)  # seconds
    timeout = Column(Integer, default=30)  # seconds
    headers = Column(JSON, nullable=True)  # custom headers for auth

    # Metadata
    region = Column(String(50), default="us-east-1")
    environment = Column(String(50), default="production")
    tags = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="systems")
    collector_jobs = relationship("CollectorJob", back_populates="system")

    def __repr__(self):
        return f"<MonitoredSystem {self.name}>"
