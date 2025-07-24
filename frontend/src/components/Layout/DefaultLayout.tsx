import { JSX, useState } from 'react';
import { Content } from 'antd/es/layout/layout';
import { Sidebar } from '../Sidebar/Sidebar';
import { DefaultLayoutStyles } from './DefaultLayout.styles';
import { Navbar } from '../Navbar/Navbar';

export const DefaultLayout = ({ children }: { children: JSX.Element }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const classes = DefaultLayoutStyles();

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className={classes.container}>
      {/* Hamburger Menu Button */}
      <button
        className={`${classes.hamburgerButton} ${
          sidebarOpen ? classes.hamburgerActive : ''
        }`}
        onClick={toggleSidebar}
        aria-label='Toggle menu'>
        <span className={classes.hamburgerLine}></span>
        <span className={classes.hamburgerLine}></span>
        <span className={classes.hamburgerLine}></span>
      </button>

      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div
          className={classes.overlay}
          onClick={toggleSidebar}
        />
      )}

      <Content className={classes.layout}>
        <div
          className={`${classes.sidebarWrapper} ${
            sidebarOpen ? classes.sidebarOpen : ''
          }`}>
          <Sidebar onItemClick={() => setSidebarOpen(false)} />
        </div>
        <div className={classes.content}>{children}</div>
      </Content>
    </div>
  );
};
