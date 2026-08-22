import { apiRequest } from './client';
import type {
  CurrentUserApiResponse,
  AdminUserRecord,
  AuthMode,
  PermissionCode,
  PermissionCatalogItem,
  PermissionRequestRecord,
  ProtectedResourceRecord,
} from '../auth/types';

export const authApi = {
  login(employeeId: string, authMode: AuthMode, password = '') {
    return apiRequest<CurrentUserApiResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ employee_id: employeeId, auth_mode: authMode, password }),
    });
  },

  logout() {
    return apiRequest<void>('/api/auth/logout', { method: 'POST' });
  },

  getMe() {
    return apiRequest<CurrentUserApiResponse>('/api/auth/me');
  },

  getPermissionCatalog() {
    return apiRequest<{ items: PermissionCatalogItem[] }>('/api/permissions/catalog');
  },

  changePassword(currentPassword: string, newPassword: string) {
    return apiRequest<void>('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  },

  requestPermission(permissionCode: PermissionCode, reason: string) {
    return apiRequest<PermissionRequestRecord>('/api/permissions/requests', {
      method: 'POST',
      body: JSON.stringify({ permission_code: permissionCode, reason }),
    });
  },

  listPendingRequests() {
    return apiRequest<PermissionRequestRecord[]>('/api/admin/permission-requests');
  },

  reviewRequest(requestId: string, decision: 'approved' | 'rejected', comment = '') {
    return apiRequest<PermissionRequestRecord>(
      `/api/admin/permission-requests/${encodeURIComponent(requestId)}/review`,
      {
        method: 'POST',
        body: JSON.stringify({ decision, comment }),
      },
    );
  },

  updatePermissionSet(item: PermissionCatalogItem) {
    return apiRequest<PermissionCatalogItem>(`/api/admin/permission-sets/${encodeURIComponent(item.code)}`, {
      method: 'PUT',
      body: JSON.stringify({
        name: item.name,
        description: item.description,
        requestable: item.requestable,
        active: item.active,
      }),
    });
  },

  listResources() {
    return apiRequest<ProtectedResourceRecord[]>('/api/admin/resources');
  },

  updateResource(item: ProtectedResourceRecord) {
    return apiRequest<ProtectedResourceRecord>(`/api/admin/resources/${encodeURIComponent(item.code)}`, {
      method: 'PUT',
      body: JSON.stringify({
        name: item.name,
        description: item.description,
        access_mode: item.access_mode,
        permission_codes: item.permission_codes,
      }),
    });
  },

  listUsers() {
    return apiRequest<AdminUserRecord[]>('/api/admin/users');
  },

  updateUser(employeeId: string, values: {
    role: 'normal' | 'admin';
    display_name?: string;
    password?: string;
    active: boolean;
  }) {
    return apiRequest<AdminUserRecord>(`/api/admin/users/${encodeURIComponent(employeeId)}`, {
      method: 'PUT',
      body: JSON.stringify(values),
    });
  },
};
