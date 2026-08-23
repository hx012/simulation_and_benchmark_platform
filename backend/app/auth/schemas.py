from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PermissionRequestStatus = Literal["pending", "approved", "rejected"]


class LoginRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=128)
    auth_mode: Literal["normal", "admin"] = "normal"
    password: str = Field(default="", max_length=256)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class PermissionRequestCreate(BaseModel):
    permission_code: str = Field(min_length=1, max_length=64)
    reason: str = Field(default="", max_length=1000)


class PermissionReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str = Field(default="", max_length=1000)


class PermissionRequestResponse(BaseModel):
    request_id: str
    user_id: str
    display_name: str
    permission_code: str
    status: PermissionRequestStatus
    reason: str
    review_comment: str | None
    created_at: datetime
    reviewed_at: datetime | None


class CurrentUserResponse(BaseModel):
    user_id: str
    display_name: str
    role: Literal["normal", "admin"]
    account_role: Literal["normal", "admin"]
    auth_mode: Literal["normal", "admin"]
    permissions: list[str]
    resources: list[str]
    resource_permissions: dict[str, list[str]]
    permission_requests: list[PermissionRequestResponse]


class PermissionCatalogItem(BaseModel):
    code: str
    name: str
    description: str
    requestable: bool
    active: bool
    system_managed: bool


class PermissionCatalogResponse(BaseModel):
    items: list[PermissionCatalogItem]


class PermissionSetUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    requestable: bool
    active: bool


class ProtectedResourceResponse(BaseModel):
    code: str
    name: str
    description: str
    access_mode: Literal["normal", "permission", "admin", "disabled"]
    permission_codes: list[str]
    system_managed: bool


class ProtectedResourceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    access_mode: Literal["normal", "permission", "admin", "disabled"]
    permission_codes: list[str] = Field(default_factory=list)


class AdminUserResponse(BaseModel):
    user_id: str
    display_name: str
    role: Literal["normal", "admin"]
    active: bool
    password_configured: bool
    last_login_at: datetime | None


class AdminUserUpdate(BaseModel):
    role: Literal["normal", "admin"]
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=256)
    active: bool = True
