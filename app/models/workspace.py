from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String(100), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Settings
    max_systems = Column(Integer, default=10)
    max_alerts = Column(Integer, default=50)
    retention_days = Column(Integer, default=30)

    # Relationships
    owner = relationship("User", back_populates="workspaces")
    systems = relationship("MonitoredSystem", back_populates="workspace")
    alerts = relationship("AlertRule", back_populates="workspace")

    def __repr__(self):
        return f"<Workspace {self.name}>"
