from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import re

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.workspace import Workspace
from ..schemas.workspace import WorkspaceCreate, WorkspaceResponse

router = APIRouter()


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text


@router.get("/", response_model=List[WorkspaceResponse])
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workspaces = db.query(Workspace).filter(
        Workspace.owner_id == current_user.id
    ).all()
    return workspaces


@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    workspace_data: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Generate unique slug and tenant_id
    base_slug = slugify(workspace_data.name)
    slug = base_slug
    counter = 1

    while db.query(Workspace).filter(Workspace.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    tenant_id = str(uuid.uuid4())

    workspace = Workspace(
        name=workspace_data.name,
        slug=slug,
        description=workspace_data.description,
        owner_id=current_user.id,
        tenant_id=tenant_id,
        max_systems=workspace_data.max_systems,
        max_alerts=workspace_data.max_alerts,
        retention_days=workspace_data.retention_days
    )

    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
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

    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
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

    db.delete(workspace)
    db.commit()

    return None
