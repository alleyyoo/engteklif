import { NavbarStyles } from "./Navbar.styles";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "primereact/button";
import { authService } from "../../services/authService";
import { verifyToken } from "../../utils/jwt";

export const Navbar = () => {
  const classes = NavbarStyles();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    authService.logout();
    navigate("/auth");
  };

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  // Current user bilgilerini al - multiple sources
  const getCurrentUser = () => {
    // 1. localStorage'dan user bilgisi
    const storedUser = authService.getCurrentUserFromStorage();
    if (storedUser) {
      return storedUser;
    }

    // 2. Token'dan decode et
    const token = localStorage.getItem('accessToken');
    if (token && verifyToken(token)) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return {
          id: payload.user_id || payload.sub,
          username: payload.username || 'User',
          role: payload.role || 'user'
        };
      } catch (error) {
        console.error('Token decode error:', error);
      }
    }

    return null;
  };

  const currentUser = getCurrentUser();
  const isAdmin = currentUser?.role === 'admin';

  return (
    <div className={classes.navbarContainer}>
      <img src="/logo.svg" alt="" width="300" />
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <Button
          label="Ana Sayfa"
          icon="pi pi-home"
          text={!isActive('/')}
          onClick={() => navigate('/')}
          style={{ 
            backgroundColor: isActive('/') ? '#195cd7' : 'transparent',
            color: isActive('/') ? 'white' : '#195cd7'
          }}
        />
        
        {/* Sadece admin'lere Material Management butonu göster */}
        {isAdmin && (
          <Button
            label="Malzeme Yönetimi"
            icon="pi pi-cog"
            text={!isActive('/materials')}
            onClick={() => navigate('/materials')}
            style={{ 
              backgroundColor: isActive('/materials') ? '#195cd7' : 'transparent',
              color: isActive('/materials') ? 'white' : '#195cd7'
            }}
          />
        )}
        
        <Button
          label="Çıkış"
          icon="pi pi-sign-out"
          severity="danger"
          outlined
          onClick={handleLogout}
        />
      </div>
    </div>
  );
};