import { SidebarStyles } from './Sidebar.styles';
import { useLocation, useNavigate } from 'react-router-dom';

interface SidebarProps {
  onItemClick?: () => void;
}

export const Sidebar = ({ onItemClick }: SidebarProps) => {
  const classes = SidebarStyles();
  const location = useLocation();
  const navigate = useNavigate();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  const handleNavigation = (
    e: React.MouseEvent<HTMLAnchorElement>,
    path: string
  ) => {
    e.preventDefault();
    navigate(path);
    onItemClick?.(); // Mobilde sidebar'ı kapat
  };

  const handleLogout = () => {
    // Logout işlemleri
    console.log('Logging out...');
    // localStorage.clear(); // veya auth token temizleme
    onItemClick?.(); // Mobilde sidebar'ı kapat
    navigate('/login'); // veya logout sonrası yönlendirme
  };

  return (
    <div className={classes.sidebar}>
      <div className={classes.sidebarMenus}>
        <a
          href='/'
          onClick={(e) => handleNavigation(e, '/')}
          className={`${classes.menu} ${
            isActive('/') ? classes.activeMenu : ''
          }`}>
          <img
            src='/HomeIcon.svg'
            alt='Dashboard'
            className={classes.menuIcon}
          />
          <span className={classes.menutitle}>Dashboard</span>
        </a>
        <a
          href='/cmm'
          onClick={(e) => handleNavigation(e, '/cmm')}
          className={`${classes.menu} ${
            isActive('/cmm') ? classes.activeMenu : ''
          }`}>
          <img
            src='/Gears.svg'
            alt='CMM'
            className={classes.menuIcon}
          />
          <span className={classes.menutitle}>CMM</span>
        </a>
        <a
          href='/materials'
          onClick={(e) => handleNavigation(e, '/materials')}
          className={`${classes.menu} ${
            isActive('/materials') ? classes.activeMenu : ''
          }`}>
          <img
            src='/Boxes.svg'
            alt='Materials'
            className={classes.menuIcon}
          />
          <span className={classes.menutitle}>Materials</span>
        </a>
      </div>
      <div>
        <div
          className={classes.menu}
          onClick={handleLogout}
          style={{ cursor: 'pointer' }}>
          <img
            src='/Logout.svg'
            alt='Logout'
            className={classes.menuIcon}
          />
          <span className={classes.menutitle}>Logout</span>
        </div>
      </div>
    </div>
  );
};
