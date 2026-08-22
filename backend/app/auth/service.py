from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.constants import (
    NORMAL_PERMISSION,
    PERMISSION_SET_REGISTRY,
    RESOURCE_REGISTRY,
    SESSION_COOKIE_NAME,
)
from app.auth.models import (
    PermissionRequest,
    PermissionSet,
    ProtectedResource,
    ResourcePermissionSet,
    User,
    UserPermissionGrant,
    UserSession,
)
from app.auth.schemas import CurrentUserResponse, PermissionRequestResponse
from app.common.config import get_settings
from app.common.database import get_db


PBKDF2_ITERATIONS = 600_000


@dataclass(frozen=True)
class AuthenticatedUser:
    user: User
    session: UserSession

    def __getattr__(self, name: str):
        return getattr(self.user, name)

    @property
    def is_admin_mode(self) -> bool:
        return self.user.role == "admin" and self.session.auth_mode == "admin"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def validate_admin_password(password: str) -> None:
    if len(password) < 8 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise HTTPException(status_code=400, detail="管理员密码至少 8 位，且必须同时包含字母和数字")


def sync_permission_registry(db: Session) -> None:
    """Register code-owned identifiers without overwriting administrator policy edits."""
    for code, item in PERMISSION_SET_REGISTRY.items():
        if db.get(PermissionSet, code) is None:
            db.add(PermissionSet(code=code, **item))

    db.flush()
    for code, item in RESOURCE_REGISTRY.items():
        resource = db.get(ProtectedResource, code)
        if resource is not None:
            continue
        resource = ProtectedResource(
            code=code,
            name=str(item["name"]),
            description=str(item["description"]),
            access_mode=str(item["access_mode"]),
            system_managed=True,
        )
        db.add(resource)
        db.flush()
        for permission_code in item["permissions"]:
            db.add(ResourcePermissionSet(
                resource_code=code,
                permission_code=str(permission_code),
            ))
    db.commit()


def ensure_bootstrap_admin(db: Session) -> None:
    settings = get_settings()
    employee_id = settings.platform_bootstrap_admin_id.strip()
    password = settings.platform_bootstrap_admin_password
    if not employee_id:
        return

    user = db.scalar(select(User).where(User.employee_id == employee_id))
    changed = False
    if user is None:
        user = User(employee_id=employee_id, display_name=employee_id, role="admin")
        db.add(user)
        changed = True
    elif user.role != "admin":
        user.role = "admin"
        changed = True

    if password and not user.password_hash:
        validate_admin_password(password)
        user.password_hash = hash_password(password)
        user.password_changed_at = _utcnow()
        changed = True
    if changed:
        db.commit()


def initialize_auth_data(db: Session) -> None:
    sync_permission_registry(db)
    ensure_bootstrap_admin(db)


def _get_or_create_normal_user(db: Session, employee_id: str) -> User:
    user = db.scalar(select(User).where(User.employee_id == employee_id))
    if user is None:
        user = User(employee_id=employee_id, display_name=employee_id, role="normal")
        db.add(user)
        db.flush()
    if not user.active:
        raise HTTPException(status_code=403, detail="账号已停用")
    return user


def login_user(db: Session, employee_id: str, auth_mode: str, password: str) -> tuple[AuthenticatedUser, str]:
    initialize_auth_data(db)
    normalized = employee_id.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="请输入工号")

    if auth_mode == "admin":
        user = db.scalar(select(User).where(User.employee_id == normalized))
        if user is None or not user.active or user.role != "admin" or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="管理员账号或密码错误")
    else:
        user = _get_or_create_normal_user(db, normalized)

    now = _utcnow()
    raw_token = secrets.token_urlsafe(48)
    session = UserSession(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        auth_mode=auth_mode,
        last_seen_at=now,
        expires_at=now + timedelta(hours=get_settings().platform_session_hours),
    )
    user.last_login_at = now
    db.add(session)
    db.commit()
    db.refresh(session)
    return AuthenticatedUser(user=user, session=session), raw_token


def logout_user(db: Session, current: AuthenticatedUser) -> None:
    current.session.revoked_at = _utcnow()
    db.commit()


def get_user_permissions(db: Session, current: AuthenticatedUser | User) -> set[str]:
    user = current.user if isinstance(current, AuthenticatedUser) else current
    if isinstance(current, AuthenticatedUser) and current.is_admin_mode:
        return set(db.scalars(select(PermissionSet.code).where(PermissionSet.active.is_(True))).all())

    active_codes = select(PermissionSet.code).where(PermissionSet.active.is_(True))
    grants = db.scalars(
        select(UserPermissionGrant.permission_code).where(
            UserPermissionGrant.user_id == user.id,
            UserPermissionGrant.active.is_(True),
            UserPermissionGrant.permission_code.in_(active_codes),
        )
    ).all()
    return {NORMAL_PERMISSION, *grants}


def get_user_requests(db: Session, user: User) -> list[PermissionRequest]:
    return list(db.scalars(
        select(PermissionRequest)
        .where(PermissionRequest.user_id == user.id)
        .order_by(PermissionRequest.created_at.desc())
    ).all())


def request_response(item: PermissionRequest, user: User) -> PermissionRequestResponse:
    return PermissionRequestResponse(
        request_id=item.id,
        user_id=user.employee_id,
        display_name=user.display_name,
        permission_code=item.permission_code,
        status=item.status,
        reason=item.reason,
        review_comment=item.review_comment,
        created_at=item.created_at,
        reviewed_at=item.reviewed_at,
    )


def current_user_response(db: Session, current: AuthenticatedUser) -> CurrentUserResponse:
    active_role = "admin" if current.is_admin_mode else "normal"
    permissions = get_user_permissions(db, current)
    resource_permissions: dict[str, list[str]] = {}
    accessible_resources: list[str] = []
    resources = db.scalars(select(ProtectedResource).order_by(ProtectedResource.code)).all()
    for resource in resources:
        required = sorted(db.scalars(select(ResourcePermissionSet.permission_code).where(
            ResourcePermissionSet.resource_code == resource.code
        )).all())
        resource_permissions[resource.code] = required
        allowed = resource.access_mode != "disabled" and (current.is_admin_mode or resource.access_mode == "normal")
        if resource.access_mode == "permission":
            allowed = bool(required) and set(required).issubset(permissions)
        elif resource.access_mode == "admin":
            allowed = current.is_admin_mode
        elif resource.access_mode == "disabled":
            allowed = False
        if allowed:
            accessible_resources.append(resource.code)
    return CurrentUserResponse(
        user_id=current.user.employee_id,
        display_name=current.user.display_name,
        role=active_role,
        account_role="admin" if current.user.role == "admin" else "normal",
        auth_mode="admin" if current.is_admin_mode else "normal",
        permissions=sorted(permissions),
        resources=accessible_resources,
        resource_permissions=resource_permissions,
        permission_requests=[
            request_response(item, current.user) for item in get_user_requests(db, current.user)
        ],
    )


def get_current_user(
    platform_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    if not platform_session:
        raise HTTPException(status_code=401, detail="请先登录")
    token_hash = hashlib.sha256(platform_session.encode()).hexdigest()
    session = db.scalar(select(UserSession).where(
        UserSession.token_hash == token_hash,
        UserSession.revoked_at.is_(None),
    ))
    now = _utcnow()
    if session is None or _as_utc(session.expires_at) <= now:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = db.get(User, session.user_id)
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="登录身份无效，请重新登录")
    session.last_seen_at = now
    db.commit()
    return AuthenticatedUser(user=user, session=session)


def require_permission(permission_code: str):
    def dependency(
        current: AuthenticatedUser = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> AuthenticatedUser:
        if permission_code not in get_user_permissions(db, current):
            raise HTTPException(status_code=403, detail={
                "code": "permission_required",
                "permission": permission_code,
                "message": f"需要权限：{permission_code}",
            })
        return current
    return dependency


def require_resource(resource_code: str):
    def dependency(
        current: AuthenticatedUser = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> AuthenticatedUser:
        resource = db.get(ProtectedResource, resource_code)
        if resource is None:
            raise HTTPException(status_code=403, detail="资源尚未配置，默认拒绝访问")
        if resource.access_mode == "disabled":
            raise HTTPException(status_code=403, detail="该模块当前未开放")
        if current.is_admin_mode:
            return current
        if resource.access_mode == "normal":
            return current
        if resource.access_mode == "admin":
            raise HTTPException(status_code=403, detail="需要管理员模式")
        required = set(db.scalars(select(ResourcePermissionSet.permission_code).where(
            ResourcePermissionSet.resource_code == resource_code
        )).all())
        owned = get_user_permissions(db, current)
        if required and required.issubset(owned):
            return current
        raise HTTPException(status_code=403, detail={
            "code": "permission_required",
            "permission": sorted(required)[0] if required else None,
            "message": f"没有访问 {resource.name} 的权限",
        })
    return dependency


def require_admin(current: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if not current.is_admin_mode:
        raise HTTPException(status_code=403, detail="请使用管理员登录")
    return current


def create_permission_request(db: Session, current: AuthenticatedUser, permission_code: str, reason: str) -> PermissionRequest:
    permission = db.get(PermissionSet, permission_code)
    if permission is None or not permission.active or not permission.requestable:
        raise HTTPException(status_code=400, detail="该权限不可申请")
    if permission_code in get_user_permissions(db, current):
        raise HTTPException(status_code=409, detail="已经拥有该权限")
    existing = db.scalar(select(PermissionRequest).where(
        PermissionRequest.user_id == current.user.id,
        PermissionRequest.permission_code == permission_code,
        PermissionRequest.status == "pending",
    ))
    if existing is not None:
        return existing
    item = PermissionRequest(user_id=current.user.id, permission_code=permission_code, reason=reason.strip())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def review_permission_request(db: Session, reviewer: AuthenticatedUser, request_id: str, decision: str, comment: str) -> PermissionRequest:
    item = db.get(PermissionRequest, request_id)
    if item is None:
        raise HTTPException(status_code=404, detail="权限申请不存在")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="该申请已经处理")

    item.status = decision
    item.reviewer_user_id = reviewer.user.id
    item.review_comment = comment.strip() or None
    item.reviewed_at = _utcnow()
    if decision == "approved":
        grant = db.scalar(select(UserPermissionGrant).where(
            UserPermissionGrant.user_id == item.user_id,
            UserPermissionGrant.permission_code == item.permission_code,
        ))
        if grant is None:
            grant = UserPermissionGrant(user_id=item.user_id, permission_code=item.permission_code)
            db.add(grant)
        grant.active = True
        grant.granted_by_user_id = reviewer.user.id
        grant.granted_at = item.reviewed_at
        grant.revoked_at = None
    db.commit()
    db.refresh(item)
    return item


def update_resource_policy(db: Session, resource: ProtectedResource, access_mode: str, permission_codes: list[str]) -> None:
    codes = list(dict.fromkeys(permission_codes))
    if access_mode == "permission" and not codes:
        raise HTTPException(status_code=400, detail="权限访问模式至少需要一个 Permission Set")
    existing = set(db.scalars(select(PermissionSet.code).where(
        PermissionSet.code.in_(codes), PermissionSet.active.is_(True)
    )).all()) if codes else set()
    if existing != set(codes):
        raise HTTPException(status_code=400, detail="包含不存在或已停用的 Permission Set")
    db.execute(delete(ResourcePermissionSet).where(ResourcePermissionSet.resource_code == resource.code))
    if access_mode == "permission":
        for code in codes:
            db.add(ResourcePermissionSet(resource_code=resource.code, permission_code=code))
    resource.access_mode = access_mode
    db.commit()


def update_admin_user(db: Session, employee_id: str, role: str, display_name: str | None, password: str | None, active: bool) -> User:
    normalized = employee_id.strip()
    bootstrap_id = get_settings().platform_bootstrap_admin_id.strip()
    if normalized == bootstrap_id and (role != "admin" or not active):
        raise HTTPException(status_code=409, detail="启动恢复管理员不能被降级或停用")
    user = db.scalar(select(User).where(User.employee_id == normalized))
    if user is None:
        user = User(employee_id=normalized, display_name=display_name or normalized)
        db.add(user)
    if role == "admin" and not (password or user.password_hash):
        raise HTTPException(status_code=400, detail="管理员必须配置密码")
    if password:
        validate_admin_password(password)
        user.password_hash = hash_password(password)
        user.password_changed_at = _utcnow()
    if user.role == "admin" and (role != "admin" or not active):
        admin_count = db.scalar(select(func.count()).select_from(User).where(
            User.role == "admin", User.active.is_(True)
        )) or 0
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="不能停用或移除最后一个管理员")
    user.role = role
    user.active = active
    if display_name:
        user.display_name = display_name.strip()
    db.commit()
    db.refresh(user)
    return user


def change_admin_password(db: Session, current: AuthenticatedUser, old_password: str, new_password: str) -> None:
    if not current.is_admin_mode or not verify_password(old_password, current.user.password_hash):
        raise HTTPException(status_code=401, detail="当前密码错误")
    validate_admin_password(new_password)
    current.user.password_hash = hash_password(new_password)
    current.user.password_changed_at = _utcnow()
    db.commit()
