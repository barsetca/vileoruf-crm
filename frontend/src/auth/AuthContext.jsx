import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { AuthApiError, login as loginRequest, logout as logoutRequest, refresh } from "../services/auth.js";


const AuthContext = createContext(null);


export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(null);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;

    refresh()
      .then((session) => {
        if (active) {
          setAccessToken(session.access_token);
          setUser(session.user);
        }
      })
      .catch(() => {
        if (active) {
          setAccessToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    try {
      const session = await loginRequest(email, password);
      setAccessToken(session.access_token);
      setUser(session.user);
      return { ok: true };
    } catch (error) {
      return {
        ok: false,
        reason: error instanceof AuthApiError && error.status === 401
          ? "invalidCredentials"
          : "unavailable",
      };
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      // Local logout must succeed even when the backend is unavailable.
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, []);

  const value = useMemo(() => ({
    accessToken,
    user,
    isAuthenticated: Boolean(accessToken && user),
    isLoading,
    login,
    logout,
  }), [accessToken, user, isLoading, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}


export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
