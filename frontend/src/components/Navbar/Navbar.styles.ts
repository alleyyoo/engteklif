import { createUseStyles } from "react-jss";
import { px2rem } from "../../utils/px2rem";

export const NavbarStyles = createUseStyles({
  navbarContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: px2rem(32),
    height: "60px",
    position: "relative",
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      padding: px2rem(24),
      height: "55px",
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      padding: px2rem(16),
      height: "50px",
      flexWrap: "wrap",
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      padding: px2rem(12),
      height: "auto",
      minHeight: "50px",
    },
  },
  
  // Logo styling
  navbarLogo: {
    height: "auto",
    maxHeight: "40px",
    width: "auto",
    maxWidth: "300px",
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      maxWidth: "250px",
      maxHeight: "35px",
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      maxWidth: "200px",
      maxHeight: "30px",
      display: "none",
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      maxWidth: "150px",
      maxHeight: "25px",
      display: "none",
    },
  },
  
  // Menu container
  navbarMenu: {
    display: "flex",
    alignItems: "center",
    gap: px2rem(16),
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      gap: px2rem(12),
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      display: "none", // Mobilde gizle, hamburger menu ile göster
      position: "absolute",
      top: "100%",
      left: 0,
      right: 0,
      backgroundColor: "white",
      boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
      borderRadius: `0 0 ${px2rem(8)} ${px2rem(8)}`,
      padding: px2rem(16),
      flexDirection: "column",
      alignItems: "stretch",
      gap: px2rem(8),
      zIndex: 1000,
      
      "&.mobile-menu-open": {
        display: "flex",
      },
    },
  },
  
  // Menu item styling
  navbarMenuItem: {
    // Desktop default styles handled by PrimeReact Button
    
    // Mobil responsive - menu item'lar tam genişlik
    "@media (max-width: 768px)": {
      width: "100%",
      justifyContent: "flex-start",
      padding: `${px2rem(12)} ${px2rem(16)}`,
      fontSize: px2rem(14),
      
      "& .p-button-label": {
        flex: 1,
        textAlign: "left",
      },
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      padding: `${px2rem(10)} ${px2rem(12)}`,
      fontSize: px2rem(12),
    },
  },
  
  // Hamburger menu button
  hamburgerButton: {
    display: "none",
    backgroundColor: "transparent",
    border: "none",
    cursor: "pointer",
    padding: px2rem(8),
    borderRadius: px2rem(4),
    transition: "background-color 0.2s ease",
    
    "&:hover": {
      backgroundColor: "rgba(25, 92, 215, 0.1)",
    },
    
    // Mobil responsive - hamburger menu'yu göster
    "@media (max-width: 768px)": {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    },
  },
  
  // Hamburger icon
  hamburgerIcon: {
    fontSize: px2rem(18),
    color: "#195cd7",
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      fontSize: px2rem(16),
    },
  },
  
  // Desktop menu container (mobilde gizlenmeyecek kısım)
  desktopMenu: {
    display: "flex",
    alignItems: "center",
    gap: px2rem(16),
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      gap: px2rem(12),
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      display: "none",
    },
  },
  
  // Mobil header (logo + hamburger)
  mobileHeader: {
    display: "none",
    width: "100%",
    justifyContent: "space-between",
    alignItems: "center",
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      display: "flex",
    },
  },
  
  // Overlay for mobile menu
  mobileMenuOverlay: {
    display: "none",
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0, 0, 0, 0.3)",
    zIndex: 999,
    
    "&.overlay-open": {
      display: "block",
    },
    
    // Sadece mobilde
    "@media (max-width: 768px)": {
      // Overlay styles
    },
  },
  
  // Çıkış butonu özel stilleri
  logoutButton: {
    // Desktop default styles
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      width: "100%",
      justifyContent: "center",
      marginTop: px2rem(8),
      padding: `${px2rem(12)} ${px2rem(16)}`,
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      padding: `${px2rem(10)} ${px2rem(12)}`,
      fontSize: px2rem(12),
    },
  },
  
  // Kullanıcı bilgisi (mobilde gösterilecek)
  mobileUserInfo: {
    display: "none",
    padding: px2rem(12),
    backgroundColor: "#f8f9fa",
    borderRadius: px2rem(8),
    marginBottom: px2rem(8),
    fontSize: px2rem(14),
    color: "#6c757d",
    textAlign: "center",
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      display: "block",
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      fontSize: px2rem(12),
      padding: px2rem(8),
    },
  },
  
  // Menu divider (mobilde)
  menuDivider: {
    display: "none",
    height: "1px",
    backgroundColor: "#e9ecef",
    margin: `${px2rem(8)} 0`,
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      display: "block",
    },
  },
});