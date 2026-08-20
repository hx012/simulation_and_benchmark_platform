import { createContext, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

export interface PlatformUser {
  userId: string;
  displayName: string;
  role: 'normal' | 'admin';
}

interface AuthContextValue {
  user: PlatformUser | null;
  authenticated: boolean;
  login: (employeeId: string) => Promise<PlatformUser>;
  logout: () => void;
}

const STORAGE_KEY = 'ai-chip-platform.auth.v1';

function readStoredUser(): PlatformUser | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<PlatformUser>;
    if (!value.userId || !value.displayName) return null;
    return {
      userId: value.userId,
      displayName: value.displayName,
      role: value.role === 'admin' ? 'admin' : 'normal',
    };
  } catch {
    return null;
  }
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PlatformUser | null>(() => readStoredUser());

  async function login(employeeId: string): Promise<PlatformUser> {
    const normalizedId = employeeId.trim();
    if (!normalizedId) {
      throw new Error('请输入工号');
    }

    // 临时开发态身份方案：仅记录工号，不承担真实身份认证。
    // 正式接入 W3 OAuth2 SSO 后，由 Auth Provider 从 /userinfo 获取 uid，
    // PlatformUser / owner_id 等业务接口保持不变。
    const nextUser: PlatformUser = {
      userId: normalizedId,
      displayName: normalizedId,
      role: 'normal',
    };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextUser));
    setUser(nextUser);
    return nextUser;
  }

  function logout() {
    window.localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  }

  const value = useMemo<AuthContextValue>(() => ({
    user,
    authenticated: Boolean(user),
    login,
    logout,
  }), [user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return value;
}
