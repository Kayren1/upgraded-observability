from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Rule configuration
    metric_name = Column(String(255), nullable=False)
    condition = Column(String(50), nullable=False)  # gt, lt, eq, gte, lte
    threshold = Column(Float, nullable=False)
    duration = Column(Integer, default=60)  # seconds

    # Notification settings
    severity = Column(String(50), default="warning")  # info, warning, critical
    notification_channels = Column(JSON, nullable=True)  # email, slack, webhook

    # Status
    is_active = Column(Boolean, default=True)
    is_muted = Column(Boolean, default=False)
    last_triggered = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship("Workspace", back_populates="alerts")
    history = relationship("AlertHistory", back_populates="alert")

    def __repr__(self):
        return f"<AlertRule {self.name}>"


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False)

    # Event details
    status = Column(String(50), nullable=False)  # triggered, resolved, acknowledged
    value = Column(Float, nullable=True)
    message = Column(Text, nullable=True)

    # Timestamps
    triggered_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    alert = relationship("AlertRule", back_populates="history")

    def __repr__(self):
        return f"<AlertHistory {self.id}>"
