import React, { useState, useEffect, useRef } from "react";
import { NavbarStyles } from "./Navbar.styles";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "primereact/button";
import { authService } from "../../services/authService";
import { verifyToken } from "../../utils/jwt";

export const Navbar = () => {
  const classes = NavbarStyles();
  const navigate = useNavigate();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const mobileMenuRef = useRef<HTMLDivElement>(null);

  const handleLogout = () => {
    authService.logout();
    navigate("/auth");
    setIsMobileMenuOpen(false); // Mobil menu'yu kapat
  };

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  // Current user bilgilerini al
  const getCurrentUser = () => {
    const storedUser = authService.getCurrentUserFromStorage();
    if (storedUser) {
      return storedUser;
    }

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

  // Mobil menu toggle
  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  // Mobil menu dışına tıklama ile kapatma
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        mobileMenuRef.current && 
        !mobileMenuRef.current.contains(event.target as Node) &&
        isMobileMenuOpen
      ) {
        setIsMobileMenuOpen(false);
      }
    };

    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isMobileMenuOpen) {
        setIsMobileMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscapeKey);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscapeKey);
    };
  }, [isMobileMenuOpen]);

  // Sayfa değiştiğinde mobil menu'yu kapat
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  // Navigation fonksiyonları
  const navigateToHome = () => {
    navigate('/');
    setIsMobileMenuOpen(false);
  };

  const navigateToMaterials = () => {
    navigate('/materials');
    setIsMobileMenuOpen(false);
  };

  return (
    <div className={classes.navbarContainer} ref={mobileMenuRef}>
      {/* Desktop Layout */}
      <img 
        src="/logo.svg" 
        alt="Logo" 
        className={classes.navbarLogo}
      />
      
      <div className={classes.desktopMenu}>
        <Button
          label="Ana Sayfa"
          icon="pi pi-home"
          text={!isActive('/')}
          onClick={navigateToHome}
          className={classes.navbarMenuItem}
          style={{ 
            backgroundColor: isActive('/') ? '#195cd7' : 'transparent',
            color: isActive('/') ? 'white' : '#195cd7'
          }}
        />
        
        {isAdmin && (
          <Button
            label="Malzeme Yönetimi"
            icon="pi pi-cog"
            text={!isActive('/materials')}
            onClick={navigateToMaterials}
            className={classes.navbarMenuItem}
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
          className={`${classes.navbarMenuItem} ${classes.logoutButton}`}
        />
      </div>

      {/* Mobile Layout */}
      <div className={classes.mobileHeader}>
        <img 
          src="/logo.svg" 
          alt="Logo" 
          className={classes.navbarLogo}
        />
        
        <button 
          className={classes.hamburgerButton}
          onClick={toggleMobileMenu}
          aria-label="Menu"
          aria-expanded={isMobileMenuOpen}
        >
          <i className={`pi ${isMobileMenuOpen ? 'pi-times' : 'pi-bars'} ${classes.hamburgerIcon}`}></i>
        </button>
      </div>

      {/* Mobile Menu Overlay */}
      <div 
        className={`${classes.mobileMenuOverlay} ${isMobileMenuOpen ? 'overlay-open' : ''}`}
        onClick={() => setIsMobileMenuOpen(false)}
      ></div>

      {/* Mobile Menu */}
      <div className={`${classes.navbarMenu} ${isMobileMenuOpen ? 'mobile-menu-open' : ''}`}>
        {/* Kullanıcı Bilgisi (Mobilde) */}
        {currentUser && (
          <div className={classes.mobileUserInfo}>
            👤 {currentUser.username} ({currentUser.role})
          </div>
        )}
        
        <Button
          label="Ana Sayfa"
          icon="pi pi-home"
          text={!isActive('/')}
          onClick={navigateToHome}
          className={classes.navbarMenuItem}
          style={{ 
            backgroundColor: isActive('/') ? '#195cd7' : 'transparent',
            color: isActive('/') ? 'white' : '#195cd7',
            width: '100%'
          }}
        />
        
        {isAdmin && (
          <Button
            label="Malzeme Yönetimi"
            icon="pi pi-cog"
            text={!isActive('/materials')}
            onClick={navigateToMaterials}
            className={classes.navbarMenuItem}
            style={{ 
              backgroundColor: isActive('/materials') ? '#195cd7' : 'transparent',
              color: isActive('/materials') ? 'white' : '#195cd7',
              width: '100%'
            }}
          />
        )}
        
        <div className={classes.menuDivider}></div>
        
        <Button
          label="Çıkış Yap"
          icon="pi pi-sign-out"
          severity="danger"
          outlined
          onClick={handleLogout}
          className={`${classes.navbarMenuItem} ${classes.logoutButton}`}
        />
      </div>
    </div>
  );
};