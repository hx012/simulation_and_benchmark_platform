import type { PlatformUser } from './types';

export const AUTH_STORAGE_KEY = 'ai-chip-platform.auth.v1';

export function readStoredUser(): PlatformUser | null {
  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<PlatformUser>;
    if (!value.userId || !value.displayName) return null;
    return {
      userId: value.userId,
      displayName: value.displayName,
      role: value.role === 'admin' ? 'admin' : 'normal',
      accountRole: value.accountRole === 'admin' ? 'admin' : 'normal',
      authMode: value.authMode === 'admin' ? 'admin' : 'normal',
      permissions: Array.isArray(value.permissions) ? value.permissions : ['normal'],
      resources: Array.isArray(value.resources) ? value.resources : [],
      resourcePermissions: value.resourcePermissions && typeof value.resourcePermissions === 'object' ? value.resourcePermissions : {},
      permissionRequests: Array.isArray(value.permissionRequests) ? value.permissionRequests : [],
    };
  } catch {
    return null;
  }
}

export function storeUser(user: PlatformUser) {
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
}

export function clearStoredUser() {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}
