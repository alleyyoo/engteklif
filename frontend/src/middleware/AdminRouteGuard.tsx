// src/components/guards/AdminRouteGuard.tsx
import React from 'react';
import { Navigate } from 'react-router-dom';
import { authService } from '../services/authService';

interface AdminRouteGuardProps {
  children: React.ReactNode;
}

export const AdminRouteGuard: React.FC<AdminRouteGuardProps> = ({ children }) => {
  // Token'dan user bilgilerini al
  const user = authService.getCurrentUserFromStorage();
  
  // User yoksa veya admin değilse 404'e yönlendir
  if (!user || user.role !== 'admin') {
    console.log('🚫 Admin access denied:', user?.role || 'no user');
    return <Navigate to="/404" replace />;
  }

  // Admin ise sayfayı göster
  console.log('✅ Admin access granted:', user.username);
  return <>{children}</>;
};