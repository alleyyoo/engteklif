import { createUseStyles } from 'react-jss';

export const DefaultLayoutStyles = createUseStyles({
  container: {
    margin: '1rem',
    position: 'relative',

    '@media (max-width: 768px)': {
      margin: '0.5rem'
    },

    '@media (max-width: 480px)': {
      margin: '0'
    }
  },

  layout: {
    width: '100%',
    display: 'flex',
    gap: '1rem',
    position: 'relative',

    '@media (max-width: 768px)': {
      gap: '0.75rem'
    },

    '@media (max-width: 480px)': {
      gap: '0'
    }
  },

  sidebarWrapper: {
    flex: '0 0 100px',
    transition: 'transform 0.3s ease-in-out',

    '@media (max-width: 768px)': {
      position: 'fixed',
      top: 0,
      left: 0,
      height: '100vh',
      width: '250px',
      backgroundColor: 'white',
      boxShadow: '2px 0 10px rgba(0, 0, 0, 0.1)',
      zIndex: 1000,
      transform: 'translateX(-100%)'
    },

    '@media (max-width: 480px)': {
      width: '80%',
      maxWidth: '300px'
    }
  },

  sidebarOpen: {
    '@media (max-width: 768px)': {
      transform: 'translateX(0) !important'
    }
  },

  content: {
    border: '1px solid oklch(92% .004 286.32)',
    backgroundColor: 'oklch(100% 0 0)',
    borderRadius: '1rem',
    flex: 1,
    height: '95vh',
    padding: '2rem',
    overflowY: 'auto',
    transition: 'margin-left 0.3s ease-in-out',

    '@media (max-width: 768px)': {
      width: '100%',
      padding: '1.5rem',
      height: '93vh'
    },

    '@media (max-width: 480px)': {
      padding: '1rem',
      borderRadius: '0.5rem',
      height: '100vh',
      border: 'none'
    }
  },

  hamburgerButton: {
    display: 'none',
    position: 'fixed',
    top: '1.5rem',
    left: '1.5rem',
    zIndex: 1001,
    backgroundColor: 'white',
    border: '1px solid oklch(92% .004 286.32)',
    borderRadius: '0.5rem',
    padding: '0.75rem',
    cursor: 'pointer',
    boxShadow: '0 2px 5px rgba(0, 0, 0, 0.1)',
    transition: 'all 0.3s ease',
    width: '44px',
    height: '44px',

    '&:hover': {
      backgroundColor: 'oklch(98% .002 286.32)'
    },

    '@media (max-width: 768px)': {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '4px'
    },

    '@media (max-width: 480px)': {
      top: '1rem',
      left: '1rem',
      width: '40px',
      height: '40px',
      padding: '0.5rem'
    }
  },

  hamburgerActive: {
    '& $hamburgerLine': {
      '&:nth-child(1)': {
        transform: 'rotate(45deg) translate(0, 6px)'
      },
      '&:nth-child(2)': {
        opacity: 0,
        transform: 'scale(0)'
      },
      '&:nth-child(3)': {
        transform: 'rotate(-45deg) translate(0, -6px)'
      }
    }
  },

  hamburgerLine: {
    display: 'block',
    width: '20px',
    height: '1px',
    backgroundColor: 'oklch(30% .02 286.32)',
    transition: 'all 0.3s ease',
    transformOrigin: 'center',
    position: 'relative'
  },

  overlay: {
    display: 'none',

    '@media (max-width: 768px)': {
      display: 'block',
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      zIndex: 999,
      animation: '$fadeIn 0.3s ease'
    }
  },

  '@keyframes fadeIn': {
    from: {
      opacity: 0
    },
    to: {
      opacity: 1
    }
  }
});
