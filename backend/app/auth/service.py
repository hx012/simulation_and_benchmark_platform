from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import secrets

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import delete, func, select, update
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
    OAuthLoginTransaction,
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


def create_w3_login_transaction(db: Session, next_path: str) -> tuple[str, str, str]:
    """Create one short-lived state/PKCE pair; only its hash is exposed in storage."""
    settings = get_settings()
    now = _utcnow()
    db.execute(delete(OAuthLoginTransaction).where(OAuthLoginTransaction.expires_at <= now))
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    item = OAuthLoginTransaction(
        state_hash=hashlib.sha256(state.encode()).hexdigest(),
        code_verifier=code_verifier,
        next_path=next_path,
        expires_at=now + timedelta(seconds=settings.platform_w3_state_ttl_seconds),
    )
    db.add(item)
    db.commit()
    code_challenge = base64url_sha256(code_verifier)
    return state, code_verifier, code_challenge


def consume_w3_login_transaction(db: Session, state: str) -> tuple[str, str]:
    """Consume a state exactly once and return its PKCE verifier and target path."""
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    item = db.scalar(select(OAuthLoginTransaction).where(
        OAuthLoginTransaction.state_hash == state_hash,
    ).with_for_update())
    now = _utcnow()
    if item is None or item.consumed_at is not None or _as_utc(item.expires_at) <= now:
        raise HTTPException(status_code=400, detail="W3 登录状态已失效，请重新登录")
    item.consumed_at = now
    db.commit()
    return item.code_verifier, item.next_path


def base64url_sha256(value: str) -> str:
    digest = hashlib.sha256(value.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def parse_w3_display_name(value: str | None, fallback: str) -> str:
    """Prefer W3's Chinese display name, then English, then the employee ID."""
    if not value:
        return fallback
    names: dict[str, str] = {}
    for item in value.split(","):
        key, separator, text = item.partition("=")
        if separator and key.strip().lower() in {"cn", "en"} and text.strip():
            names[key.strip().lower()] = text.strip()
    return names.get("cn") or names.get("en") or fallback


def login_w3_user(
    db: Session,
    global_user_id: str,
    employee_id: str,
    display_name: str | None,
) -> tuple[AuthenticatedUser, str]:
    """Bind a W3 identity to a local user and establish an ordinary local session."""
    initialize_auth_data(db)
    global_id = global_user_id.strip()
    employee = employee_id.strip()
    if not global_id or not employee:
        raise HTTPException(status_code=502, detail="W3 用户信息缺少 globalUserID 或 uid")

    user = db.scalar(select(User).where(User.w3_global_user_id == global_id))
    employee_owner = db.scalar(select(User).where(User.employee_id == employee))
    if user is not None:
        if employee_owner is not None and employee_owner.id != user.id:
            raise HTTPException(status_code=409, detail="W3 工号已绑定到其他平台账号，请联系管理员")
        user.employee_id = employee
    elif employee_owner is not None:
        if employee_owner.w3_global_user_id and employee_owner.w3_global_user_id != global_id:
            raise HTTPException(status_code=409, detail="该工号已绑定其他 W3 账号，请联系管理员")
        user = employee_owner
        user.w3_global_user_id = global_id
    else:
        user = User(
            employee_id=employee,
            w3_global_user_id=global_id,
            display_name=parse_w3_display_name(display_name, employee),
            role="normal",
        )
        db.add(user)
        db.flush()

    if not user.active:
        raise HTTPException(status_code=403, detail="账号已停用")
    user.display_name = parse_w3_display_name(display_name, employee)
    return _create_user_session(db, user, "normal")


def _create_user_session(db: Session, user: User, auth_mode: str) -> tuple[AuthenticatedUser, str]:
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
        if get_settings().platform_w3_oauth_enabled:
            raise HTTPException(status_code=403, detail="普通用户请使用 W3 登录")
        user = _get_or_create_normal_user(db, normalized)
    return _create_user_session(db, user, auth_mode)


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
    permissions = {NORMAL_PERMISSION, *grants}
    if user.is_team_member:
        permissions.update(db.scalars(
            select(ResourcePermissionSet.permission_code)
            .join(
                ProtectedResource,
                ProtectedResource.code == ResourcePermissionSet.resource_code,
            )
            .where(
                ProtectedResource.access_mode.in_(("normal", "permission")),
                ResourcePermissionSet.permission_code.in_(active_codes),
            )
        ).all())
    return permissions


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
        team_business_access = (
            current.user.is_team_member
            and resource.access_mode in {"normal", "permission"}
        )
        allowed = resource.access_mode != "disabled" and (
            current.is_admin_mode or team_business_access or resource.access_mode == "normal"
        )
        if resource.access_mode == "permission" and not team_business_access:
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
        is_team_member=current.user.is_team_member,
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
        if current.user.is_team_member and resource.access_mode in {"normal", "permission"}:
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


def require_team_member_or_admin(
    current: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if current.is_admin_mode or current.user.is_team_member:
        return current
    raise HTTPException(status_code=403, detail="只有团队成员或管理员可以查看使用概览")


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
        codes = list(db.scalars(select(ResourcePermissionSet.permission_code).where(
            ResourcePermissionSet.resource_code == resource.code
        )).all())
    if access_mode == "permission" and not codes:
        generated_code = f"resource_{hashlib.sha1(resource.code.encode()).hexdigest()[:16]}"
        permission = db.get(PermissionSet, generated_code)
        if permission is None:
            permission = PermissionSet(
                code=generated_code,
                name=f"{resource.name}访问权限",
                description=resource.description,
                requestable=True,
                active=True,
                system_managed=False,
            )
            db.add(permission)
            db.flush()
        codes = [generated_code]
    existing = set(db.scalars(select(PermissionSet.code).where(
        PermissionSet.code.in_(codes), PermissionSet.active.is_(True)
    )).all()) if codes else set()
    if existing != set(codes):
        raise HTTPException(status_code=400, detail="包含不存在或已停用的 Permission Set")
    if access_mode == "permission":
        db.execute(delete(ResourcePermissionSet).where(ResourcePermissionSet.resource_code == resource.code))
        for code in codes:
            db.add(ResourcePermissionSet(resource_code=resource.code, permission_code=code))
        permissions = db.scalars(select(PermissionSet).where(PermissionSet.code.in_(codes))).all()
        for permission in permissions:
            permission.requestable = True
            permission.active = True
            permission.name = f"{resource.name}访问权限"
            permission.description = resource.description
    else:
        retained_codes = db.scalars(select(ResourcePermissionSet.permission_code).where(
            ResourcePermissionSet.resource_code == resource.code
        )).all()
        for code in retained_codes:
            used_elsewhere = db.scalar(select(func.count()).select_from(ResourcePermissionSet).join(
                ProtectedResource,
                ProtectedResource.code == ResourcePermissionSet.resource_code,
            ).where(
                ResourcePermissionSet.permission_code == code,
                ResourcePermissionSet.resource_code != resource.code,
                ProtectedResource.access_mode == "permission",
            )) or 0
            permission = db.get(PermissionSet, code)
            if permission is not None and used_elsewhere == 0 and code != NORMAL_PERMISSION:
                permission.requestable = False
    resource.access_mode = access_mode
    db.commit()


def update_admin_user(
    db: Session,
    current: AuthenticatedUser,
    employee_id: str,
    role: str,
    display_name: str | None,
    password: str | None,
    active: bool,
    is_team_member: bool | None = None,
) -> User:
    normalized = employee_id.strip()
    bootstrap_id = get_settings().platform_bootstrap_admin_id.strip()
    if normalized == bootstrap_id and (role != "admin" or not active):
        raise HTTPException(status_code=409, detail="启动恢复管理员不能被降级或停用")
    if normalized == current.user.employee_id and not active:
        raise HTTPException(status_code=409, detail="不能屏蔽当前登录账号")
    if normalized == current.user.employee_id and role != "admin":
        raise HTTPException(status_code=409, detail="不能移除当前登录账号的管理员身份")
    user = db.scalar(select(User).where(User.employee_id == normalized))
    if user is None:
        user = User(employee_id=normalized, display_name=display_name or normalized)
        db.add(user)
        db.flush()
    if role == "admin" and not (password or user.password_hash):
        raise HTTPException(status_code=400, detail="管理员必须配置密码")
    if password:
        validate_admin_password(password)
        user.password_hash = hash_password(password)
        user.password_changed_at = _utcnow()
    if user.role == "admin" and user.active and (role != "admin" or not active):
        admin_count = db.scalar(select(func.count()).select_from(User).where(
            User.role == "admin", User.active.is_(True)
        )) or 0
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="不能停用或移除最后一个管理员")
    user.role = role
    user.active = active
    if is_team_member is not None:
        user.is_team_member = is_team_member
    if display_name:
        user.display_name = display_name.strip()
    if not active:
        db.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .values(revoked_at=_utcnow())
        )
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
