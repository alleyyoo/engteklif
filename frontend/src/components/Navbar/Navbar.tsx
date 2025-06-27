import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "primereact/button";
import { authService } from "../../services/authService";
import { verifyToken } from "../../utils/jwt";
import { NavbarStyles } from "./Navbar.styles";
import { useEffect, useRef, useState } from "react";

export const Navbar = () => {
  const classes = NavbarStyles();
  const navigate = useNavigate();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const mobileMenuRef = useRef<HTMLDivElement>(null);

  const handleLogout = () => {
    authService.logout();
    navigate("/auth");
    setIsMobileMenuOpen(false);
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

    const token = localStorage.getItem("accessToken");
    if (token && verifyToken(token)) {
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        return {
          id: payload.user_id || payload.sub,
          username: payload.username || "User",
          role: payload.role || "user",
        };
      } catch (error) {
        console.error("Token decode error:", error);
      }
    }

    return null;
  };

  const currentUser = getCurrentUser();
  const isAdmin = currentUser?.role === "admin";

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
      if (event.key === "Escape" && isMobileMenuOpen) {
        setIsMobileMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscapeKey);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscapeKey);
    };
  }, [isMobileMenuOpen]);

  // Sayfa değiştiğinde mobil menu'yu kapat
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  // Navigation fonksiyonları
  const navigateToHome = () => {
    navigate("/");
    setIsMobileMenuOpen(false);
  };

  const navigateToMaterials = () => {
    navigate("/materials");
    setIsMobileMenuOpen(false);
  };

  return (
    <>
      <div className={classes.navbarContainer} ref={mobileMenuRef}>
        {/* Logo */}
        <div className={classes.navbarBrand}>
          <img src="/logo.svg" alt="Logo" />
        </div>

        {/* Mobil Menu Toggle Button */}
        <button
          className={classes.mobileMenuToggle}
          onClick={toggleMobileMenu}
          aria-label="Menu"
          aria-expanded={isMobileMenuOpen}
        >
          <i className={isMobileMenuOpen ? "pi pi-times" : "pi pi-bars"}></i>
        </button>

        {/* Navigation Menu */}
        <div
          className={`${classes.navbarMenu} ${
            isMobileMenuOpen ? "active" : ""
          }`}
          role="navigation"
        >
          <a
            href="#"
            className={`${classes.navbarItem} ${
              isActive("/") ? classes.navbarItemActive : ""
            }`}
            onClick={(e) => {
              e.preventDefault();
              navigateToHome();
            }}
          >
            <i className="pi pi-home"></i>
            Ana Sayfa
          </a>

          {/* Sadece admin'lere Material Management menüsü göster */}
          {isAdmin && (
            <a
              href="#"
              className={`${classes.navbarItem} ${
                isActive("/materials") ? classes.navbarItemActive : ""
              }`}
              onClick={(e) => {
                e.preventDefault();
                navigateToMaterials();
              }}
            >
              <i className="pi pi-cog"></i>
              Malzeme Yönetimi
            </a>
          )}

          {/* User Info (Mobilde göster) */}

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

      {/* Mobil Menu Overlay */}
      <div
        className={`${classes.mobileMenuOverlay} ${
          isMobileMenuOpen ? "active" : ""
        }`}
        onClick={() => setIsMobileMenuOpen(false)}
        aria-hidden="true"
      />
    </>
  );
};
