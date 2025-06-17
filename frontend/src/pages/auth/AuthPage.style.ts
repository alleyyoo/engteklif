import { createUseStyles } from "react-jss";
import { px2rem } from "../../utils/px2rem";

export const AuthPageStyle = createUseStyles({
  authContainer: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    columnGap: px2rem(48),
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
    height: "100vh",
    boxSizing: "border-box",
    padding: `0 ${px2rem(100)}`,
  },
  authImage: {
    width: "100%",
    height: "80vh",
    objectFit: "cover",
    borderRadius: px2rem(40),
  },
  authDiv: {
    display: "flex",
    flexDirection: "column",
    rowGap: px2rem(24),
    width: "100%",
    padding: px2rem(32),
    boxSizing: "border-box",
    borderRadius: px2rem(16),
  },
  authLogo: {
    height: px2rem(48),
    width: "auto",
  },
  authTitle: {
    fontSize: px2rem(48),
    fontWeight: 400,
    textAlign: "center",
    margin: 0,
  },
  inputContainer: {
    width: "100%",
  },
});
