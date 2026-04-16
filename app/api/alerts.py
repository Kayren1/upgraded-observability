from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.workspace import Workspace
from ..models.alert import AlertRule, AlertHistory
from ..schemas.alert import AlertRuleCreate, AlertRuleResponse, AlertHistoryResponse

router = APIRouter()


def get_user_workspace(workspace_id: int, db: Session, current_user: User) -> Workspace:
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    return workspace


@router.get("/workspace/{workspace_id}", response_model=List[AlertRuleResponse])
def list_alerts(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workspace = get_user_workspace(workspace_id, db, current_user)
    alerts = db.query(AlertRule).filter(
        AlertRule.workspace_id == workspace.id
    ).all()
    return alerts


@router.post("/workspace/{workspace_id}", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    workspace_id: int,
    alert_data: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workspace = get_user_workspace(workspace_id, db, current_user)

    # Check alert limit
    current_count = db.query(AlertRule).filter(
        AlertRule.workspace_id == workspace.id
    ).count()

    if current_count >= workspace.max_alerts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum number of alerts ({workspace.max_alerts}) reached"
        )

    # Validate condition
    valid_conditions = ["gt", "lt", "eq", "gte", "lte"]
    if alert_data.condition not in valid_conditions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid condition. Must be one of: {valid_conditions}"
        )

    alert = AlertRule(
        workspace_id=workspace.id,
        name=alert_data.name,
        description=alert_data.description,
        metric_name=alert_data.metric_name,
        condition=alert_data.condition,
        threshold=alert_data.threshold,
        duration=alert_data.duration,
        severity=alert_data.severity,
        notification_channels=alert_data.notification_channels
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return alert


@router.get("/{alert_id}", response_model=AlertRuleResponse)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alert = db.query(AlertRule).join(Workspace).filter(
        AlertRule.id == alert_id,
        Workspace.owner_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alert = db.query(AlertRule).join(Workspace).filter(
        AlertRule.id == alert_id,
        Workspace.owner_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    db.delete(alert)
    db.commit()

    return None


@router.post("/{alert_id}/mute", response_model=AlertRuleResponse)
def mute_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alert = db.query(AlertRule).join(Workspace).filter(
        AlertRule.id == alert_id,
        Workspace.owner_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    alert.is_muted = True
    db.commit()
    db.refresh(alert)

    return alert


@router.post("/{alert_id}/unmute", response_model=AlertRuleResponse)
def unmute_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alert = db.query(AlertRule).join(Workspace).filter(
        AlertRule.id == alert_id,
        Workspace.owner_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    alert.is_muted = False
    db.commit()
    db.refresh(alert)

    return alert


@router.get("/{alert_id}/history", response_model=List[AlertHistoryResponse])
def get_alert_history(
    alert_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alert = db.query(AlertRule).join(Workspace).filter(
        AlertRule.id == alert_id,
        Workspace.owner_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    history = db.query(AlertHistory).filter(
        AlertHistory.alert_id == alert_id
    ).order_by(AlertHistory.triggered_at.desc()).limit(limit).all()

    return history
