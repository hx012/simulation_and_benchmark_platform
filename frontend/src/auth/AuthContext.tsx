import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { authApi } from '../api/auth';
import { clearStoredUser, readStoredUser, storeUser } from './storage';
import { mapCurrentUser } from './types';
import type { AuthMode, PermissionCatalogItem, PermissionCode, PlatformUser } from './types';

interface AuthContextValue {
  user: PlatformUser | null;
  authenticated: boolean;
  login: (employeeId: string, authMode: AuthMode, password?: string) => Promise<PlatformUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<PlatformUser | null>;
  hasPermission: (permission: PermissionCode) => boolean;
  hasResource: (resource: string) => boolean;
  permissionCatalog: Record<string, PermissionCatalogItem>;
  refreshPermissionCatalog: () => Promise<Record<string, PermissionCatalogItem>>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PlatformUser | null>(() => readStoredUser());
  const [permissionCatalog, setPermissionCatalog] = useState<Record<string, PermissionCatalogItem>>({});

  async function refreshPermissionCatalog() {
    const response = await authApi.getPermissionCatalog();
    const next = Object.fromEntries(response.items.map((item) => [item.code, item]));
    setPermissionCatalog(next);
    return next;
  }

  async function refreshUser(): Promise<PlatformUser | null> {
    try {
      const current = mapCurrentUser(await authApi.getMe());
      storeUser(current);
      setUser(current);
      await refreshPermissionCatalog();
      return current;
    } catch {
      clearStoredUser();
      setUser(null);
      return null;
    }
  }

  useEffect(() => {
    void refreshUser();
    // Reconcile the server-side session once on startup.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function login(employeeId: string, authMode: AuthMode, password = ''): Promise<PlatformUser> {
    const normalizedId = employeeId.trim();
    if (!normalizedId) {
      throw new Error('请输入工号');
    }

    const nextUser = mapCurrentUser(await authApi.login(normalizedId, authMode, password));
    storeUser(nextUser);
    setUser(nextUser);
    await refreshPermissionCatalog();
    return nextUser;
  }

  async function logout() {
    try {
      await authApi.logout();
    } catch {
      // Local logout still clears stale UI state if the session already expired.
    }
    clearStoredUser();
    setUser(null);
    setPermissionCatalog({});
  }

  function hasPermission(permission: PermissionCode) {
    return Boolean(user?.permissions.includes(permission));
  }

  function hasResource(resource: string) {
    return Boolean(user?.resources.includes(resource));
  }

  const value = useMemo<AuthContextValue>(() => ({
    user,
    authenticated: Boolean(user),
    login,
    logout,
    refreshUser,
    hasPermission,
    hasResource,
    permissionCatalog,
    refreshPermissionCatalog,
  }), [user, permissionCatalog]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return value;
}
