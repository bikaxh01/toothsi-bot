"use client";

import { useState, useEffect } from 'react';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
}

export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true
  });

  useEffect(() => {
    // Check localStorage for existing authentication
    const checkAuth = () => {
      try {
        const authData = localStorage.getItem('toothsi_auth');
        if (authData) {
          const parsed = JSON.parse(authData);
          if (parsed.authenticated && parsed.timestamp) {
            // Check if authentication is still valid (optional: add expiration)
            setAuthState({
              isAuthenticated: true,
              isLoading: false
            });
            return;
          }
        }
      } catch (error) {
        console.error('Error checking authentication:', error);
      }
      
      setAuthState({
        isAuthenticated: false,
        isLoading: false
      });
    };

    checkAuth();
  }, []);

  const authenticate = () => {
    setAuthState({
      isAuthenticated: true,
      isLoading: false
    });
  };

  const logout = () => {
    localStorage.removeItem('toothsi_auth');
    setAuthState({
      isAuthenticated: false,
      isLoading: false
    });
  };

  return {
    ...authState,
    authenticate,
    logout
  };
}
