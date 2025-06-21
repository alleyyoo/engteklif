import { createUseStyles } from "react-jss";
import { px2rem } from "../../utils/px2rem";

export const NavbarStyles = createUseStyles({
  navbarContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: px2rem(32),
    height: "60px",
  }
})