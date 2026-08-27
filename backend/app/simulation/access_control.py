from app.auth.service import AuthenticatedUser
from app.simulation.exceptions import TaskNotFoundError
from app.simulation.models import SimulationTask


def visible_task_owner(
    current: AuthenticatedUser,
    requested_owner_id: str | None = None,
) -> str | None:
    """Return the owner filter allowed for the current task-list request."""
    if current.is_admin_mode:
        return requested_owner_id
    return current.user.employee_id


def require_task_read_access(
    current: AuthenticatedUser,
    task: SimulationTask,
) -> SimulationTask:
    if current.is_admin_mode or task.owner_id == current.user.employee_id:
        return task
    # Hide task existence from users who do not own it.
    raise TaskNotFoundError(f"Simulation task not found: {task.task_id}")


def require_task_owner(
    current: AuthenticatedUser,
    task: SimulationTask,
) -> SimulationTask:
    """Keep task mutations owner-only, including for administrators."""
    if task.owner_id == current.user.employee_id:
        return task
    raise TaskNotFoundError(f"Simulation task not found: {task.task_id}")
