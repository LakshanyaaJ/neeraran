import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';

interface AuthGuardProps {
  children: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { role } = useAuthStore();
  const location = useLocation();

  if (!role) {
    const fromPath = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?from=${fromPath}`} replace />;
  }

  return <>{children}</>;
};
