from datetime import datetime
import httpx
import random
from . import celery_app
from ..core.database import SessionLocal
from ..models.system import MonitoredSystem
from ..models.collector import CollectorJob, CollectorAgent
from ..models.metrics import MetricSnapshot


@celery_app.task(bind=True, max_retries=3)
def collect_metrics(self, system_id: int, job_id: int):
    """
    Collect metrics from a monitored system
    """
    db = SessionLocal()

    try:
        # Get job and system
        job = db.query(CollectorJob).filter(CollectorJob.id == job_id).first()
        system = db.query(MonitoredSystem).filter(MonitoredSystem.id == system_id).first()

        if not job or not system:
            return {"status": "error", "message": "Job or system not found"}

        # Update job status
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        # Simulate metric collection
        metrics_collected = 0
        bytes_processed = 0

        if system.metrics_url:
            try:
                # In production, this would actually fetch from the URL
                # For now, we simulate

                # Generate simulated metrics
                metric_names = [
                    "http_requests_total",
                    "http_request_duration_seconds",
                    "process_cpu_seconds_total",
                    "process_resident_memory_bytes",
                    "http_requests_in_flight"
                ]

                for metric_name in metric_names:
                    snapshot = MetricSnapshot(
                        system_id=system.id,
                        metric_name=metric_name,
                        metric_type="gauge",
                        value=random.uniform(0, 1000),
                        labels={"system": system.name, "env": system.environment}
                    )
                    db.add(snapshot)
                    metrics_collected += 1
                    bytes_processed += 100  # Simulated

                db.commit()

                # Update system status
                system.status = "active"
                system.last_check = datetime.utcnow()
                system.last_error = None

            except Exception as e:
                system.status = "error"
                system.last_error = str(e)

        # Update job completion
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.duration_ms = int((job.completed_at - job.started_at).total_seconds() * 1000)
        job.metrics_collected = metrics_collected
        job.bytes_processed = bytes_processed

        db.commit()

        return {
            "status": "success",
            "metrics_collected": metrics_collected,
            "bytes_processed": bytes_processed
        }

    except Exception as e:
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
        raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


@celery_app.task
def process_alerts(workspace_id: int):
    """
    Process alert rules for a workspace
    """
    db = SessionLocal()

    try:
        from ..models.alert import AlertRule, AlertHistory

        alerts = db.query(AlertRule).filter(
            AlertRule.workspace_id == workspace_id,
            AlertRule.is_active == True,
            AlertRule.is_muted == False
        ).all()

        triggered = 0

        for alert in alerts:
            # Get recent metrics
            recent_value = random.uniform(0, 1000)  # Simulated

            # Evaluate condition
            triggered_now = False

            if alert.condition == "gt" and recent_value > alert.threshold:
                triggered_now = True
            elif alert.condition == "lt" and recent_value < alert.threshold:
                triggered_now = True
            elif alert.condition == "eq" and recent_value == alert.threshold:
                triggered_now = True
            elif alert.condition == "gte" and recent_value >= alert.threshold:
                triggered_now = True
            elif alert.condition == "lte" and recent_value <= alert.threshold:
                triggered_now = True

            if triggered_now:
                # Create alert history
                history = AlertHistory(
                    alert_id=alert.id,
                    status="triggered",
                    value=recent_value,
                    message=f"{alert.metric_name} is {recent_value} ({alert.condition} {alert.threshold})"
                )
                db.add(history)

                alert.last_triggered = datetime.utcnow()
                alert.trigger_count += 1
                triggered += 1

        db.commit()

        return {"triggered_alerts": triggered}

    finally:
        db.close()


@celery_app.task
def cleanup_old_metrics(days: int = 30):
    """
    Clean up metrics older than specified days
    """
    db = SessionLocal()

    try:
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        deleted = db.query(MetricSnapshot).filter(
            MetricSnapshot.timestamp < cutoff
        ).delete()

        db.commit()

        return {"deleted_metrics": deleted}

    finally:
        db.close()
