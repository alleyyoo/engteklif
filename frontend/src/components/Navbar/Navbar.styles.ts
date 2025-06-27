import { createUseStyles } from "react-jss";

export const NavbarStyles = createUseStyles({
  navbarContainer: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "1rem 2rem",
    backgroundColor: "#fff",
    boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
    position: "relative",

    // Tablet için
    "@media (max-width: 1024px)": {
      padding: "1rem 1.5rem",
    },

    // Mobil için
    "@media (max-width: 768px)": {
      padding: "0.75rem 1rem",
      flexWrap: "wrap",
    },
  },

  navbarBrand: {
    // Logo/marka alanı için
    "@media (max-width: 768px)": {
      order: 1,
      flex: "1",
    },
  },

  mobileMenuToggle: {
    display: "none",
    background: "none",
    border: "none",
    fontSize: "1.5rem",
    cursor: "pointer",
    padding: "0.5rem",
    borderRadius: "4px",
    transition: "background-color 0.3s ease",

    "&:hover": {
      backgroundColor: "#f0f4ff",
    },

    // Sadece mobilde görünür
    "@media (max-width: 768px)": {
      display: "block",
      order: 2,
    },
  },

  navbarMenu: {
    display: "flex",
    alignItems: "center",
    gap: "2rem",

    // Tablet için
    "@media (max-width: 1024px)": {
      gap: "1.5rem",
    },

    // Mobil için
    "@media (max-width: 768px)": {
      display: "none",
      position: "absolute",
      top: "100%",
      left: "0",
      right: "0",
      backgroundColor: "#fff",
      boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
      flexDirection: "column",
      gap: "0",
      padding: "1rem 0",
      zIndex: 1000,
      order: 3,
      width: "100%",

      "&.active": {
        display: "flex",
      },
    },
  },

  navbarItem: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.5rem 1rem",
    textDecoration: "none",
    color: "black",
    borderRadius: "4px",
    transition: "all 0.3s ease",
    cursor: "pointer",
    whiteSpace: "nowrap",

    "&:hover": {
      backgroundColor: "#f0f4ff",
      color: "#195cd7",
    },

    // Tablet için
    "@media (max-width: 1024px)": {
      padding: "0.4rem 0.8rem",
      fontSize: "0.9rem",
      gap: "0.4rem",
    },

    // Mobil için
    "@media (max-width: 768px)": {
      width: "100%",
      justifyContent: "flex-start",
      padding: "0.75rem 1.5rem",
      borderRadius: "0",
      fontSize: "1rem",

      "&:hover": {
        backgroundColor: "#f8f9fa",
      },
    },
  },

  navbarItemActive: {
    color: "#195cd7",

    "&:hover": {
      backgroundColor: "#1547b8",
      color: "white !important",
    },

    // Mobil için aktif durumda farklı stil
    "@media (max-width: 768px)": {
      backgroundColor: "#f0f4ff",

      "&:hover": {
        backgroundColor: "#1547b8",
        color: "white !important",
      },
    },
  },

  logoutButton: {
    backgroundColor: "#dc3545",
    color: "white",
    border: "none",
    borderRadius: "4px",
    padding: "0.5rem 1rem",
    cursor: "pointer",
    transition: "all 0.3s ease",

    "&:hover": {
      backgroundColor: "#c82333",
      color: "white !important",
    },

    // Tablet için
    "@media (max-width: 1024px)": {
      padding: "0.4rem 0.8rem",
      fontSize: "0.9rem",
    },

    // Mobil için
    "@media (max-width: 768px)": {
      width: "calc(100% - 3rem)",
      margin: "0.5rem 1.5rem",
      padding: "0.75rem",
      textAlign: "center",

      "&:hover": {
        backgroundColor: "#c82333",
      },
    },
  },

  // Mobil menü açık olduğunda overlay
  mobileMenuOverlay: {
    display: "none",

    "@media (max-width: 768px)": {
      position: "fixed",
      top: "0",
      left: "0",
      right: "0",
      bottom: "0",
      backgroundColor: "rgba(0,0,0,0.5)",
      zIndex: 999,

      "&.active": {
        display: "block",
      },
    },
  },

  // Küçük ekranlar için ek optimizasyonlar
  "@media (max-width: 480px)": {
    navbarContainer: {
      padding: "0.5rem 0.75rem",
    },

    navbarItem: {
      padding: "0.875rem 1rem",
      fontSize: "1.1rem",
    },

    logoutButton: {
      margin: "0.75rem 1rem",
      padding: "0.875rem",
    },
  },
});
