import { createUseStyles } from "react-jss";

export const NavbarStyles = createUseStyles({
  navbarContainer: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "1rem 2rem",
    backgroundColor: "#fff",
    boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
  },

  navbarMenu: {
    display: "flex",
    alignItems: "center",
    gap: "2rem",
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

    "&:hover": {
      backgroundColor: "#f0f4ff",
      color: "#195cd7",
    },
  },

  navbarItemActive: {
    color: "#195cd7",
    "&:hover": {
      backgroundColor: "#1547b8",
      color: "white !important",
    },
  },

  logoutButton: {
    // Özel logout button stilleri buraya
  },
});
