import { NavbarStyles } from "./Navbar.styles"

export const Navbar = () => {
  const classes = NavbarStyles()
  return (
    <div className={classes.navbarContainer}>
      <img src="/logo.svg" alt="" width="300" />
      <div>
        <p>deneme</p>
      </div>
    </div>
  )
}