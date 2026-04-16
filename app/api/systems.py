from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

from ..core.database import get_database_session
from ..core.security import get_authenticated_current_user
from ..models.user import User
from ..models.workspace import Workspace
from ..models.system import MonitoredSystem
from ..models.collector import CollectorJob
from ..schemas.system import SystemCreate, SystemResponse, SystemUpdate

logger = logging.getLogger(__name__)

systems_router = APIRouter()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def retrieve_workspace_owned_by_current_user_or_raise_401(
    workspace_id_requested: int,
    current_user_owner: User,
    database_session: Session
) -> Workspace:
    """
    Retrieve a workspace by ID, verifying it's owned by the current user.
    This is a security check — users can only access their own workspaces.

    Raises HTTPException 404 if workspace doesn't exist or isn't owned by the user.
    """
    if workspace_id_requested is None or workspace_id_requested <= 0:
        raise ValueError("retrieve_workspace_owned_by_current_user_or_raise_401: workspace_id must be positive")
    if current_user_owner is None:
        raise ValueError("retrieve_workspace_owned_by_current_user_or_raise_401: current_user cannot be None")

    workspace_found_in_database = database_session.query(Workspace).filter(
        Workspace.id == workspace_id_requested,
        Workspace.owner_id == current_user_owner.id
    ).first()

    if workspace_found_in_database is None:
        logger.warning(
            f"Unauthorized workspace access attempt. "
            f"User: {current_user_owner.id}, Workspace: {workspace_id_requested}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found. Either it doesn't exist or you don't have access to it.",
        )

    return workspace_found_in_database


def retrieve_monitored_system_by_id_or_raise_401(
    system_id_requested: int,
    current_user_owner: User,
    database_session: Session
) -> MonitoredSystem:
    """
    Retrieve a monitored system by ID, verifying it belongs to a workspace owned by the current user.
    This ensures users can only access systems they own.

    Raises HTTPException 404 if system doesn't exist or isn't owned by the user.
    """
    if system_id_requested is None or system_id_requested <= 0:
        raise ValueError("retrieve_monitored_system_by_id_or_raise_401: system_id must be positive")
    if current_user_owner is None:
        raise ValueError("retrieve_monitored_system_by_id_or_raise_401: current_user cannot be None")

    monitored_system_found = database_session.query(MonitoredSystem).join(Workspace).filter(
        MonitoredSystem.id == system_id_requested,
        Workspace.owner_id == current_user_owner.id
    ).first()

    if monitored_system_found is None:
        logger.warning(
            f"Unauthorized system access attempt. "
            f"User: {current_user_owner.id}, System: {system_id_requested}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System not found. Either it doesn't exist or you don't have access to it.",
        )

    return monitored_system_found


def verify_system_count_is_below_workspace_limit(
    workspace_with_limit_check: Workspace,
    database_session: Session
) -> None:
    """
    Check if the workspace has room for another system.
    Different plans have different limits (e.g., free=5, pro=100, enterprise=unlimited).

    Raises HTTPException 400 if the limit is already reached.
    """
    if workspace_with_limit_check is None:
        raise ValueError("verify_system_count_is_below_workspace_limit: workspace cannot be None")

    # Count existing systems in this workspace.
    current_system_count_in_workspace = database_session.query(MonitoredSystem).filter(
        MonitoredSystem.workspace_id == workspace_with_limit_check.id
    ).count()

    systems_remaining_quota = workspace_with_limit_check.max_systems - current_system_count_in_workspace

    if systems_remaining_quota <= 0:
        logger.warning(
            f"System creation rejected: workspace {workspace_with_limit_check.id} reached limit "
            f"({workspace_with_limit_check.max_systems} systems)."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot add more systems. Your workspace has reached the limit of "
                f"{workspace_with_limit_check.max_systems} systems. "
                f"Upgrade your plan to add more."
            ),
        )


def create_initial_collector_job_for_new_system(
    newly_created_system: MonitoredSystem,
    database_session: Session
) -> CollectorJob:
    """
    When a system is registered, we create an initial collector job to start telemetry collection.
    This is why metrics appear "instantly" in the UI after registration.

    The job will be picked up by the collector agents (Go) from the Redis queue.
    """
    if newly_created_system is None:
        raise ValueError("create_initial_collector_job_for_new_system: system cannot be None")

    initial_collector_job = CollectorJob(
        system_id=newly_created_system.id,
        job_type="metrics",  # Could also be "logs" or "traces"
        status="pending",  # Will be picked up by collector agents
        priority=10,  # Higher priority for initial collection
        scheduled_at=datetime.utcnow(),
    )

    database_session.add(initial_collector_job)
    database_session.commit()

    logger.info(f"Initial collector job created for system {newly_created_system.id}")
    return initial_collector_job


# ============================================================================
# ENDPOINT: GET /workspace/{workspace_id}
# ============================================================================

@systems_router.get(
    "/workspace/{workspace_id}",
    response_model=List[SystemResponse],
    summary="List all systems in a workspace",
    description="Returns all monitored systems registered in the specified workspace."
)
def list_all_systems_in_workspace(
    workspace_id: int,
    database_session: Session = Depends(get_database_session),
    current_user: User = Depends(get_authenticated_current_user)
) -> List[SystemResponse]:
    """
    List all systems (monitored endpoints) in a workspace.

    Only returns systems in workspaces owned by the current user.
    """
    # Guard: Workspace must exist and be owned by user
    workspace_found = retrieve_workspace_owned_by_current_user_or_raise_401(
        workspace_id,
        current_user,
        database_session
    )

    # Query all systems in the workspace.
    all_systems_in_workspace = database_session.query(MonitoredSystem).filter(
        MonitoredSystem.workspace_id == workspace_found.id
    ).all()

    logger.debug(f"Listed {len(all_systems_in_workspace)} systems in workspace {workspace_id}")
    return all_systems_in_workspace


# ============================================================================
# ENDPOINT: POST /workspace/{workspace_id}
# ============================================================================

@systems_router.post(
    "/workspace/{workspace_id}",
    response_model=SystemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new monitored system",
    description="Add a system/service to be monitored. Triggers initial telemetry collection."
)
def register_new_monitored_system_in_workspace(
    workspace_id: int,
    system_registration_data: SystemCreate,
    database_session: Session = Depends(get_database_session),
    current_user: User = Depends(get_authenticated_current_user)
) -> SystemResponse:
    """
    Register a new system to be monitored.

    Steps:
    1. Verify workspace exists and is owned by user
    2. Check system count is below limit
    3. Create the system record
    4. Queue initial collector job
    5. Return system info

    The collector agents will automatically start polling this system's endpoints
    within seconds.
    """
    # Guard: Input data must be valid
    if system_registration_data is None:
        raise ValueError("register_new_monitored_system_in_workspace: system_registration_data cannot be None")
    if system_registration_data.name is None or system_registration_data.name == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System name is required."
        )
    if system_registration_data.metrics_url is None or system_registration_data.metrics_url == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metrics endpoint URL is required."
        )

    # Guard: Workspace must exist and be owned by user
    workspace_found = retrieve_workspace_owned_by_current_user_or_raise_401(
        workspace_id,
        current_user,
        database_session
    )

    # Guard: System count must be below limit
    verify_system_count_is_below_workspace_limit(workspace_found, database_session)

    # Create the system record.
    newly_created_monitored_system = MonitoredSystem(
        workspace_id=workspace_found.id,
        name=system_registration_data.name,
        description=system_registration_data.description,
        metrics_url=system_registration_data.metrics_url,
        logs_url=system_registration_data.logs_url,
        traces_url=system_registration_data.traces_url,
        health_url=system_registration_data.health_url,
        check_interval=system_registration_data.check_interval,
        timeout=system_registration_data.timeout,
        headers=system_registration_data.headers,
        region=system_registration_data.region,
        environment=system_registration_data.environment,
        tags=system_registration_data.tags,
    )

    database_session.add(newly_created_monitored_system)
    database_session.commit()
    database_session.refresh(newly_created_monitored_system)

    # Queue initial collection job so data starts flowing immediately.
    create_initial_collector_job_for_new_system(newly_created_monitored_system, database_session)

    logger.info(
        f"New system registered: {newly_created_monitored_system.name} "
        f"(ID: {newly_created_monitored_system.id}) in workspace {workspace_id}"
    )
    return newly_created_monitored_system


# ============================================================================
# ENDPOINT: GET /{system_id}
# ============================================================================

@systems_router.get(
    "/{system_id}",
    response_model=SystemResponse,
    summary="Get a specific system",
    description="Returns details of a specific monitored system."
)
def retrieve_specific_monitored_system(
    system_id: int,
    database_session: Session = Depends(get_database_session),
    current_user: User = Depends(get_authenticated_current_user)
) -> SystemResponse:
    """
    Retrieve a specific system by ID.

    Only returns the system if it belongs to a workspace owned by the current user.
    """
    # Guard: System must exist and be owned by user (via workspace)
    monitored_system_found = retrieve_monitored_system_by_id_or_raise_401(
        system_id,
        current_user,
        database_session
    )

    return monitored_system_found


# ============================================================================
# ENDPOINT: PATCH /{system_id}
# ============================================================================

@systems_router.patch(
    "/{system_id}",
    response_model=SystemResponse,
    summary="Update system configuration",
    description="Update a system's monitoring settings (URL, interval, tags, etc)."
)
def update_monitored_system_configuration(
    system_id: int,
    system_update_data: SystemUpdate,
    database_session: Session = Depends(get_database_session),
    current_user: User = Depends(get_authenticated_current_user)
) -> SystemResponse:
    """
    Update a system's configuration.

    Only certain fields can be updated: name, description, URLs, interval, etc.
    We don't allow changing the system ID or creation timestamp.
    """
    # Guard: System must exist and be owned by user
    monitored_system_to_update = retrieve_monitored_system_by_id_or_raise_401(
        system_id,
        current_user,
        database_session
    )

    # Extract the fields to update (only include fields explicitly set).
    fields_provided_for_update = system_update_data.model_dump(exclude_unset=True)

    # Guard: Don't allow empty updates
    if len(fields_provided_for_update) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update.",
        )

    # Apply the updates.
    for field_name, new_field_value in fields_provided_for_update.items():
        setattr(monitored_system_to_update, field_name, new_field_value)

    database_session.commit()
    database_session.refresh(monitored_system_to_update)

    logger.info(f"System {system_id} updated with {len(fields_provided_for_update)} fields")
    return monitored_system_to_update


# ============================================================================
# ENDPOINT: DELETE /{system_id}
# ============================================================================

@systems_router.delete(
    "/{system_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a monitored system",
    description="Remove a system from monitoring. This is a soft delete — data is preserved."
)
def delete_monitored_system(
    system_id: int,
    database_session: Session = Depends(get_database_session),
    current_user: User = Depends(get_authenticated_current_user)
) -> None:
    """
    Delete (remove) a monitored system.

    This is a permanent delete. The system record and its collector jobs are removed.
    Historical metrics are preserved in Prometheus/storage for audit purposes.

    TODO(kweku, 2025-04-16): Implement soft deletes instead of hard deletes.
    Hard deletes make it hard to audit "what happened to this system?"
    We should add an is_deleted flag and query accordingly.
    """
    # Guard: System must exist and be owned by user
    monitored_system_to_delete = retrieve_monitored_system_by_id_or_raise_401(
        system_id,
        current_user,
        database_session
    )

    database_session.delete(monitored_system_to_delete)
    database_session.commit()

    logger.info(f"System {system_id} deleted (hard delete)")


# ============================================================================
# ENDPOINT: POST /{system_id}/pause
# ============================================================================

@systems_router.post(
    "/{system_id}/pause",
    response_model=SystemResponse,
    summary="Pause monitoring of a system",
    description="Temporarily stop collecting telemetry from a system."
)
def pause_monitored_system_collection(
    system_id: int,
    database_session: Session = Depends(get_database_session),
    current_user: User = Depends(get_authenticated_current_user)
) -> SystemResponse:
    """
    Pause collection for a system.

    Useful when you're doing maintenance and don't want to pollute the metrics with spurious errors.
    The system's historical data is preserved.
    """
    # Guard: System must exist and be owned by user
    monitored_system_to_pause = retrieve_monitored_system_by_id_or_raise_401(
        system_id,
        current_user,
        database_session
    )

    # Guard: System should not already be paused
    if not monitored_system_to_pause.user_is_active_and_can_login:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System is already paused.",
        )

    monitored_system_to_pause.status = "paused"
    monitored_system_to_pause.user_is_active_and_can_login = False
    database_session.commit()
    database_session.refresh(monitored_system_to_pause)

    logger.info(f"System {system_id} paused")
    return monitored_system_to_pause


# ============================================================================
# ENDPOINT: POST /{system_id}/resume
# ============================================================================

@systems_router.post(
    "/{system_id}/resume",
    response_model=SystemResponse,
    summary="Resume monitoring of a system",
    description="Resume telemetry collection for a previously paused system."
)
def resume_monitored_system_collection(
    system_id: int,
    database_session: Session = Depends(get_database_session),
    current_user: User = Depends(get_authenticated_current_user)
) -> SystemResponse:
    """
    Resume collection for a paused system.

    Collection will resume according to the configured check_interval.
    """
    # Guard: System must exist and be owned by user
    monitored_system_to_resume = retrieve_monitored_system_by_id_or_raise_401(
        system_id,
        current_user,
        database_session
    )

    # Guard: System must be paused to resume
    if monitored_system_to_resume.user_is_active_and_can_login:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System is already active. Nothing to resume.",
        )

    monitored_system_to_resume.status = "active"
    monitored_system_to_resume.user_is_active_and_can_login = True
    database_session.commit()
    database_session.refresh(monitored_system_to_resume)

    logger.info(f"System {system_id} resumed")
    return monitored_system_to_resume


# Export router for inclusion in main API.
router = systems_router

