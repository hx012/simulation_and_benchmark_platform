export type PlatformRole = 'normal' | 'admin';
export type AuthMode = 'normal' | 'admin';
export type PermissionCode = string;
export type PermissionRequestStatus = 'pending' | 'approved' | 'rejected';

export interface PermissionCatalogItem {
  code: PermissionCode;
  name: string;
  description: string;
  requestable: boolean;
  active: boolean;
  system_managed: boolean;
}

export interface ProtectedResourceRecord {
  code: string;
  name: string;
  description: string;
  access_mode: 'normal' | 'permission' | 'admin' | 'disabled';
  permission_codes: PermissionCode[];
  system_managed: boolean;
}

export interface AdminUserRecord {
  user_id: string;
  display_name: string;
  role: PlatformRole;
  active: boolean;
  password_configured: boolean;
  last_login_at: string | null;
}

export interface PermissionRequestRecord {
  request_id: string;
  user_id: string;
  display_name: string;
  permission_code: PermissionCode;
  status: PermissionRequestStatus;
  reason: string;
  review_comment: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface PlatformUser {
  userId: string;
  displayName: string;
  role: PlatformRole;
  accountRole: PlatformRole;
  authMode: AuthMode;
  permissions: PermissionCode[];
  resources: string[];
  resourcePermissions: Record<string, PermissionCode[]>;
  permissionRequests: PermissionRequestRecord[];
}

export interface CurrentUserApiResponse {
  user_id: string;
  display_name: string;
  role: PlatformRole;
  account_role: PlatformRole;
  auth_mode: AuthMode;
  permissions: PermissionCode[];
  resources: string[];
  resource_permissions: Record<string, PermissionCode[]>;
  permission_requests: PermissionRequestRecord[];
}

export function mapCurrentUser(value: CurrentUserApiResponse): PlatformUser {
  return {
    userId: value.user_id,
    displayName: value.display_name,
    role: value.role,
    accountRole: value.account_role,
    authMode: value.auth_mode,
    permissions: value.permissions,
    resources: value.resources,
    resourcePermissions: value.resource_permissions,
    permissionRequests: value.permission_requests,
  };
}
