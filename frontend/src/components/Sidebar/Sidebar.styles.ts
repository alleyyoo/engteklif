import { createUseStyles } from 'react-jss';

export const SidebarStyles = createUseStyles({
  sidebar: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    width: '100%',
    height: '100%',
    padding: '1rem',
    boxSizing: 'border-box',

    // Tablet ve altı
    '@media (max-width: 768px)': {
      padding: '1.5rem',
      height: '100vh'
    },

    // Mobil
    '@media (max-width: 480px)': {
      padding: '1rem',
      flexDirection: 'column',
      height: '100vh'
    }
  },

  logo: {
    // Mobil
    '@media (max-width: 480px)': {
      flex: '0 0 auto'
    }
  },

  sidebarMenus: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',

    // Tablet
    '@media (max-width: 768px)': {
      gap: '0.75rem'
    },

    // Mobil - dikey düzen koru
    '@media (max-width: 480px)': {
      flexDirection: 'column',
      gap: '0.5rem',
      padding: '1rem',
      marginTop: '2rem'
    }
  },

  menu: {
    padding: '.5rem',
    borderRadius: '.5rem',
    backgroundColor: 'white',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    border: '1px solid white',
    filter: 'drop-shadow(0px 0px 2px rgba(0, 0, 0, 0.1))',
    transition: 'border 0.3s ease',
    textDecoration: 'none',
    minWidth: 'fit-content',

    '&:hover': {
      border: '1px solid black'
    },

    // Tablet
    '@media (max-width: 768px)': {
      padding: '.75rem 1rem',
      flexDirection: 'row',
      justifyContent: 'flex-start',
      gap: '1rem'
    },

    // Mobil
    '@media (max-width: 480px)': {
      padding: '.75rem 1rem',
      flexDirection: 'row',
      justifyContent: 'flex-start',
      gap: '0.75rem',
      width: '100%'
    }
  },

  menuIcon: {
    // Icon boyutları için yeni class
    width: '24px',
    height: '24px',

    '@media (max-width: 768px)': {
      width: '20px',
      height: '20px'
    },

    '@media (max-width: 480px)': {
      width: '18px',
      height: '18px'
    }
  },

  menutitle: {
    fontSize: '.7rem',
    color: 'oklch(44.6% .03 256.802)',
    whiteSpace: 'nowrap',

    // Tablet
    '@media (max-width: 768px)': {
      fontSize: '.65rem'
    },

    // Mobil - metni göster
    '@media (max-width: 480px)': {
      fontSize: '.6rem',
      display: 'block'
    }
  },

  // Mobil için metin gösterme seçeneği
  menuTitleVisible: {
    '@media (max-width: 480px)': {
      display: 'block !important',
      fontSize: '.6rem'
    }
  },

  activeMenu: {
    border: '1px solid black',

    // Mobil için daha belirgin active state
    '@media (max-width: 480px)': {
      backgroundColor: 'oklch(96% .01 256.802)',
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
    }
  },

  // Mobil için hamburger menü container (opsiyonel)
  mobileMenuToggle: {
    display: 'none',

    '@media (max-width: 480px)': {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0.5rem',
      cursor: 'pointer',
      backgroundColor: 'white',
      border: '1px solid rgba(0, 0, 0, 0.1)',
      borderRadius: '0.25rem',
      marginLeft: 'auto'
    }
  }
});
