from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.constants import CORE_ADMIN_RESOURCES, NORMAL_PERMISSION, SESSION_COOKIE_NAME
from app.auth.models import (
    PermissionRequest,
    PermissionSet,
    ProtectedResource,
    ResourcePermissionSet,
    User,
    UserPermissionGrant,
)
from app.auth.schemas import (
    AdminUserResponse,
    AdminUserUpdate,
    AuthConfigResponse,
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
    ResourceAuthorizedUserResponse,
)
from app.auth.service import (
    AuthenticatedUser,
    change_admin_password,
    create_permission_request,
    current_user_response,
    consume_w3_login_transaction,
    create_w3_login_transaction,
    get_current_user,
    login_user,
    login_w3_user,
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


def _safe_next_path(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/home"


def _w3_error_redirect(message: str) -> RedirectResponse:
    return RedirectResponse(
        url=f"/login?{urlencode({'oauth_error': message})}",
        status_code=status.HTTP_303_SEE_OTHER,
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
    bootstrap_id = get_settings().platform_bootstrap_admin_id.strip()
    return AdminUserResponse(
        user_id=user.employee_id,
        display_name=user.display_name,
        role="admin" if user.role == "admin" else "normal",
        active=user.active,
        password_configured=bool(user.password_hash),
        bootstrap_admin=user.employee_id == bootstrap_id,
        last_login_at=user.last_login_at,
    )


def _resource_response(db: Session, item: ProtectedResource) -> ProtectedResourceResponse:
    permission_codes = list(db.scalars(
        select(ResourcePermissionSet.permission_code)
        .where(ResourcePermissionSet.resource_code == item.code)
        .order_by(ResourcePermissionSet.permission_code)
    ).all())
    authorized_users: list[ResourceAuthorizedUserResponse] = []
    if permission_codes:
        users = db.scalars(
            select(User)
            .join(UserPermissionGrant, UserPermissionGrant.user_id == User.id)
            .where(
                UserPermissionGrant.permission_code.in_(permission_codes),
                UserPermissionGrant.active.is_(True),
                User.active.is_(True),
            )
            .distinct()
            .order_by(User.employee_id)
        ).all()
        authorized_users = [
            ResourceAuthorizedUserResponse(user_id=user.employee_id, display_name=user.display_name)
            for user in users
        ]
    return ProtectedResourceResponse(
        code=item.code,
        name=item.name,
        description=item.description,
        access_mode=item.access_mode,
        permission_codes=permission_codes,
        authorized_users=authorized_users,
        system_managed=item.system_managed,
    )


@router.post("/auth/login", response_model=CurrentUserResponse)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)) -> CurrentUserResponse:
    current, token = login_user(db, request.employee_id, request.auth_mode, request.password)
    _set_session_cookie(response, token)
    return current_user_response(db, current)


@router.get("/auth/config", response_model=AuthConfigResponse)
def auth_config() -> AuthConfigResponse:
    return AuthConfigResponse(w3_oauth_enabled=get_settings().platform_w3_oauth_enabled)


@router.get("/auth/w3/login")
def w3_login(
    next_path: str = Query(default="/home", alias="next"),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    if not settings.platform_w3_oauth_enabled:
        raise HTTPException(status_code=404, detail="W3 OAuth2 登录未启用")

    state, _, code_challenge = create_w3_login_transaction(db, _safe_next_path(next_path))
    params = {
        "response_type": "code",
        "client_id": settings.platform_w3_client_id,
        "redirect_uri": settings.platform_w3_redirect_uri,
        "scope": settings.platform_w3_scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    separator = "&" if "?" in settings.platform_w3_authorize_url else "?"
    return RedirectResponse(
        url=f"{settings.platform_w3_authorize_url}{separator}{urlencode(params)}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/auth/w3/callback")
def w3_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    if not settings.platform_w3_oauth_enabled:
        raise HTTPException(status_code=404, detail="W3 OAuth2 登录未启用")
    if error:
        return _w3_error_redirect(error_description or error)
    if not code or not state:
        return _w3_error_redirect("W3 回调缺少授权码或登录状态")

    try:
        code_verifier, next_path = consume_w3_login_transaction(db, state)
    except HTTPException as exc:
        return _w3_error_redirect(str(exc.detail))

    try:
        with httpx.Client(timeout=settings.platform_w3_http_timeout_seconds) as client:
            token_response = client.post(settings.platform_w3_token_url, json={
                "client_id": settings.platform_w3_client_id,
                "client_secret": settings.platform_w3_client_secret,
                "redirect_uri": settings.platform_w3_redirect_uri,
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
            })
            token_response.raise_for_status()
            token_payload = token_response.json()
            access_token = token_payload.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                return _w3_error_redirect("W3 Token 响应缺少 access_token")
            userinfo_response = client.post(settings.platform_w3_userinfo_url, json={
                "client_id": settings.platform_w3_client_id,
                "access_token": access_token,
                "scope": settings.platform_w3_scope,
            })
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()
    except (httpx.HTTPError, ValueError):
        return _w3_error_redirect("W3 认证服务请求失败，请稍后重试")

    global_user_id = userinfo.get("globalUserID") if isinstance(userinfo, dict) else None
    employee_id = userinfo.get("uid") if isinstance(userinfo, dict) else None
    display_name = userinfo.get("displayName") if isinstance(userinfo, dict) else None
    if not isinstance(global_user_id, str) or not global_user_id.strip():
        return _w3_error_redirect("W3 用户信息缺少 globalUserID")
    if not isinstance(employee_id, str) or not employee_id.strip():
        return _w3_error_redirect("W3 用户信息缺少 uid 工号")
    if not isinstance(display_name, str) or not display_name.strip():
        return _w3_error_redirect("W3 用户信息缺少 displayName 姓名")

    try:
        current, session_token = login_w3_user(db, global_user_id, employee_id, display_name)
    except HTTPException as exc:
        return _w3_error_redirect(str(exc.detail))
    response = RedirectResponse(url=_safe_next_path(next_path), status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, session_token)
    return response


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
