'use client';

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { createContext, createElement, useContext, useEffect, type ReactNode } from 'react';
import { apiClient } from '@/lib/api-client';

export interface AuthUser {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  avatar?: string;
  roles: string[];
  permissions: string[];
  schoolId?: string;
  school?: {
    id: string;
    name: string;
    slug: string;
    logo?: string;
    currency: string;
    currencySymbol: string;
  };
  mfaEnabled: boolean;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setUser: (user: AuthUser) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      setUser: (user) => set({ user, isAuthenticated: true }),

      setTokens: (accessToken, refreshToken) => {
        set({ accessToken, refreshToken });
        // Set in axios defaults
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
      },

      clearAuth: () => {
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
        delete apiClient.defaults.headers.common['Authorization'];
        if (typeof window !== 'undefined') {
          window.location.href = '/auth/login';
        }
      },

      hasPermission: (permission) => {
        const { user } = get();
        if (!user) return false;
        if (user.roles?.includes('super-admin')) return true;
        return user.permissions?.includes(permission) ?? false;
      },

      hasRole: (role) => {
        const { user } = get();
        if (!user) return false;
        return user.roles?.includes(role) ?? false;
      },

      hasAnyRole: (roles) => {
        const { user } = get();
        if (!user) return false;
        return roles.some((r) => user.roles?.includes(r) ?? false);
      },
    }),
    {
      name: 'educore-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);

// Context provider to initialize auth on mount
const AuthContext = createContext<null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { accessToken, setTokens, clearAuth, setUser } = useAuthStore();

  useEffect(() => {
    if (accessToken) {
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
      // Validate token by fetching user
      apiClient
        .get('/v1/auth/me')
        .then((res) => setUser(res.data.data))
        .catch(() => clearAuth());
    }
  }, []);

  return createElement(AuthContext.Provider, { value: null }, children);
}

export const useAuth = () => useAuthStore();
export const useUser = () => useAuthStore((s) => s.user);
export const usePermission = (perm: string) => useAuthStore((s) => s.hasPermission(perm));
