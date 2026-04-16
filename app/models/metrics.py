from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON
from datetime import datetime
from ..core.database import Base


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(Integer, ForeignKey("monitored_systems.id"), nullable=False)

    # Metric details
    metric_name = Column(String(255), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)  # counter, gauge, histogram
    value = Column(Float, nullable=False)
    labels = Column(JSON, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<MetricSnapshot {self.metric_name}={self.value}>"
