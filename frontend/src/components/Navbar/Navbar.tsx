import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "primereact/button";
import { authService } from "../../services/authService";
import { verifyToken } from "../../utils/jwt";
import { NavbarStyles } from "./Navbar.styles";

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
      
      <div className={classes.navbarMenu}>
        <a 
          href="#"
          className={`${classes.navbarItem} ${isActive('/') ? classes.navbarItemActive : ''}`}
          onClick={(e) => {
            e.preventDefault();
            navigate('/');
          }}
        >
          <i className="pi pi-home"></i>
          Ana Sayfa
        </a>
        
        {/* Sadece admin'lere Material Management menüsü göster */}
        {isAdmin && (
          <a 
            href="#"
            className={`${classes.navbarItem} ${isActive('/materials') ? classes.navbarItemActive : ''}`}
            onClick={(e) => {
              e.preventDefault();
              navigate('/materials');
            }}
          >
            <i className="pi pi-cog"></i>
            Malzeme Yönetimi
          </a>
        )}
        
        <Button
          label="Çıkış"
          icon="pi pi-sign-out"
          severity="danger"
          outlined
          onClick={handleLogout}
          className={classes.logoutButton}
        />
      </div>
    </div>
  );
};