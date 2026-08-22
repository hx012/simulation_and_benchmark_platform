from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.constants import CORE_ADMIN_RESOURCES, NORMAL_PERMISSION, SESSION_COOKIE_NAME
from app.auth.models import (
    PermissionRequest,
    PermissionSet,
    ProtectedResource,
    ResourcePermissionSet,
    User,
)
from app.auth.schemas import (
    AdminUserResponse,
    AdminUserUpdate,
    CurrentUserResponse,
    LoginRequest,
    PasswordChangeRequest,
    PermissionCatalogItem,
    PermissionCatalogResponse,
    PermissionRequestCreate,
    PermissionRequestResponse,
    PermissionReviewRequest,
    PermissionSetUpdate,
    ProtectedResourceResponse,
    ProtectedResourceUpdate,
)
from app.auth.service import (
    AuthenticatedUser,
    change_admin_password,
    create_permission_request,
    current_user_response,
    get_current_user,
    login_user,
    logout_user,
    request_response,
    require_admin,
    review_permission_request,
    update_admin_user,
    update_resource_policy,
)
from app.common.config import get_settings
from app.common.database import get_db


router = APIRouter(prefix="/api", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=int(settings.platform_session_hours * 3600),
        httponly=True,
        secure=settings.platform_session_cookie_secure,
        samesite="lax",
        path="/",
    )


def _catalog_item(item: PermissionSet) -> PermissionCatalogItem:
    return PermissionCatalogItem(
        code=item.code,
        name=item.name,
        description=item.description,
        requestable=item.requestable,
        active=item.active,
        system_managed=item.system_managed,
    )


def _admin_user_response(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        user_id=user.employee_id,
        display_name=user.display_name,
        role="admin" if user.role == "admin" else "normal",
        active=user.active,
        password_configured=bool(user.password_hash),
        last_login_at=user.last_login_at,
    )


def _resource_response(db: Session, item: ProtectedResource) -> ProtectedResourceResponse:
    permission_codes = list(db.scalars(
        select(ResourcePermissionSet.permission_code)
        .where(ResourcePermissionSet.resource_code == item.code)
        .order_by(ResourcePermissionSet.permission_code)
    ).all())
    return ProtectedResourceResponse(
        code=item.code,
        name=item.name,
        description=item.description,
        access_mode=item.access_mode,
        permission_codes=permission_codes,
        system_managed=item.system_managed,
    )


@router.post("/auth/login", response_model=CurrentUserResponse)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)) -> CurrentUserResponse:
    current, token = login_user(db, request.employee_id, request.auth_mode, request.password)
    _set_session_cookie(response, token)
    return current_user_response(db, current)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    logout_user(db, current)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@router.get("/auth/me", response_model=CurrentUserResponse)
def me(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    return current_user_response(db, current)


@router.post("/auth/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    request: PasswordChangeRequest,
    current: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    change_admin_password(db, current, request.current_password, request.new_password)


@router.get("/permissions/catalog", response_model=PermissionCatalogResponse)
def permission_catalog(
    _: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PermissionCatalogResponse:
    items = db.scalars(select(PermissionSet).order_by(PermissionSet.code)).all()
    return PermissionCatalogResponse(items=[_catalog_item(item) for item in items])


@router.post("/permissions/requests", response_model=PermissionRequestResponse)
def submit_permission_request(
    request: PermissionRequestCreate,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PermissionRequestResponse:
    item = create_permission_request(db, current, request.permission_code, request.reason)
    return request_response(item, current.user)


@router.get("/admin/permission-requests", response_model=list[PermissionRequestResponse])
def list_pending_permission_requests(
    _: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[PermissionRequestResponse]:
    rows = db.execute(
        select(PermissionRequest, User)
        .join(User, PermissionRequest.user_id == User.id)
        .where(PermissionRequest.status == "pending")
        .order_by(PermissionRequest.created_at.asc())
    ).all()
    return [request_response(item, user) for item, user in rows]


@router.post("/admin/permission-requests/{request_id}/review", response_model=PermissionRequestResponse)
def review_request(
    request_id: str,
    request: PermissionReviewRequest,
    reviewer: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PermissionRequestResponse:
    item = review_permission_request(db, reviewer, request_id, request.decision, request.comment)
    applicant = db.get(User, item.user_id)
    assert applicant is not None
    return request_response(item, applicant)


@router.put("/admin/permission-sets/{permission_code}", response_model=PermissionCatalogItem)
def configure_permission_set(
    permission_code: str,
    request: PermissionSetUpdate,
    _: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PermissionCatalogItem:
    item = db.get(PermissionSet, permission_code)
    if item is None:
        raise HTTPException(status_code=404, detail="Permission Set 不存在")
    if item.system_managed and not request.active:
        raise HTTPException(status_code=400, detail="系统基础 Permission Set 不能停用")
    if item.code == NORMAL_PERMISSION and request.requestable:
        raise HTTPException(status_code=400, detail="平台基础权限不能设置为可申请")
    item.name = request.name.strip()
    item.description = request.description.strip()
    item.requestable = request.requestable
    item.active = request.active
    db.commit()
    db.refresh(item)
    return _catalog_item(item)


@router.get("/admin/resources", response_model=list[ProtectedResourceResponse])
def list_resources(
    _: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ProtectedResourceResponse]:
    items = db.scalars(select(ProtectedResource).order_by(ProtectedResource.code)).all()
    return [_resource_response(db, item) for item in items]


@router.put("/admin/resources/{resource_code}", response_model=ProtectedResourceResponse)
def configure_resource(
    resource_code: str,
    request: ProtectedResourceUpdate,
    _: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProtectedResourceResponse:
    item = db.get(ProtectedResource, resource_code)
    if item is None:
        raise HTTPException(status_code=404, detail="受保护资源不存在")
    if item.code in CORE_ADMIN_RESOURCES and request.access_mode != "admin":
        raise HTTPException(status_code=400, detail="核心管理资源必须保持为仅管理员访问")
    item.name = request.name.strip()
    item.description = request.description.strip()
    update_resource_policy(db, item, request.access_mode, request.permission_codes)
    db.refresh(item)
    return _resource_response(db, item)


@router.get("/admin/users", response_model=list[AdminUserResponse])
def list_users(
    _: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminUserResponse]:
    users = db.scalars(select(User).order_by(User.employee_id)).all()
    return [_admin_user_response(user) for user in users]


@router.put("/admin/users/{employee_id}", response_model=AdminUserResponse)
def configure_user(
    employee_id: str,
    request: AdminUserUpdate,
    _: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    user = update_admin_user(
        db, employee_id, request.role, request.display_name, request.password, request.active
    )
    return _admin_user_response(user)
